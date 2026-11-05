"""Emi's memory between runs: one JSON file on the host (openclaw-setup-brief.md step 5).

Not on the intake sheet: the sheet's columns belong to the EZFOLIO build tool.
"""
import json
import os
import tempfile
import time
from datetime import datetime, timedelta, timezone

try:
    import fcntl
except ImportError:  # the dev's Windows machine; Emi runs on Linux
    fcntl = None

EMPTY = {
    "last_scan": None,       # ISO UTC of the last inbox scan
    "processed": {},         # Graph message id -> {at, outcome}; a crashed scan doesn't redo these
    "next_question": 1,      # E-001, E-002, ...
    "questions": {},         # "E-001" -> {booking_ref, message_id, ask, asked_at, answer, answered_at}
    "drafts": {},            # Graph draft id -> {booking_ref, row, kind, drafted_at}
    "confirmations": {},     # "booking_ref|row" -> {draft_id, sent_at, cod_deadline, balance_deadline}
    "reminders": {},         # "booking_ref|deposit" / "booking_ref|balance" -> {draft_id, drafted_at}
    "confirmation_holds": {},  # booking_ref -> {pdf_link, reason}: left out of confirmations-due until a new PDF
    "stop_sales_nights": {},  # room code -> [ISO nights already in a stop-sales draft]: no second draft for them
    "next_review": 1,        # draft #1, #2, ... as shown on Telegram
    "reviews": {},           # "12" -> {draft_id, status, how, source, to, kind, ref, row, text, version, ...}
    "awaiting_feedback": None,  # "12" after Rewrite is pressed, until the rewrite is saved
}

REVIEW_OPEN = "pending"
_held = {}  # path -> the lock's open file, kept until the process ends, which releases it


def hold_lock(path, wait=120):
    """One command at a time from reading the state to saving it, held until this process ends. Each command loads
    the whole file and saves it whole: on 04/11 a Telegram Deny loaded it, a new draft took #415, and the Deny's save
    wiped that draft's record, so the next draft took #415 again. Raises TimeoutError after `wait` seconds rather than risk that."""
    if fcntl is None or path in _held:  # flock is per open file: a second open in this process would wait on itself
        return
    f = open(path + ".lock", "a")
    deadline = time.time() + wait
    while True:
        try:
            fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
            _held[path] = f
            return
        except OSError:
            if time.time() >= deadline:
                f.close()
                raise TimeoutError(f"another command has held {path}.lock for {wait} s; run this one again") from None
            time.sleep(0.1)


def now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class State:
    def __init__(self, path):
        self.path = path
        if os.path.exists(path):
            with open(path, encoding="utf-8") as f:
                self.data = {**json.loads(json.dumps(EMPTY)), **json.load(f)}
        else:
            self.data = json.loads(json.dumps(EMPTY))

    def save(self):
        """Write to a temp file then rename, so a crash mid-write can't corrupt the state."""
        d = os.path.dirname(os.path.abspath(self.path))
        fd, tmp = tempfile.mkstemp(dir=d, prefix=".state-", suffix=".json")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)
        os.replace(tmp, self.path)

    # --- scan clock ---
    def mark_scanned(self, at=None):
        """Move the scan clock and forget processed ids older than a week before it."""
        self.data["last_scan"] = at = at or now_iso()
        cutoff = (datetime.strptime(at, "%Y-%m-%dT%H:%M:%SZ") - timedelta(days=7)).strftime("%Y-%m-%dT%H:%M:%SZ")
        self.data["processed"] = {k: v for k, v in self.data["processed"].items() if v["at"] >= cutoff}

    def mark_processed(self, message_id, outcome):
        self.data["processed"][message_id] = {"at": now_iso(), "outcome": outcome}

    def is_processed(self, message_id):
        return message_id in self.data["processed"]

    # --- questions to Karen ---
    def ask(self, booking_ref, ask, message_id=""):
        """message_id: the email that waits for this answer before its draft is written."""
        qid = f"E-{self.data['next_question']:03d}"
        self.data["next_question"] += 1
        self.data["questions"][qid] = {"booking_ref": booking_ref, "message_id": message_id, "ask": ask,
                                       "asked_at": now_iso(), "answer": None, "answered_at": None}
        return qid

    def open_questions(self):
        return {k: v for k, v in self.data["questions"].items() if v["answer"] is None}

    def answer(self, text):
        """Match Karen's reply to a question. 'E-014 yes' -> E-014. A bare 'yes' only when exactly one is open.
        Returns the question id, or None when it's ambiguous and Emi must ask which one."""
        first, _, rest = text.strip().partition(" ")
        qid = first.upper()
        if qid in self.data["questions"]:
            body = rest.strip()
        else:
            opened = list(self.open_questions())
            if len(opened) != 1:
                return None
            qid, body = opened[0], text.strip()
        self.data["questions"][qid].update(answer=body, answered_at=now_iso())
        return qid

    # --- drafts, confirmations, reminders ---
    def record_draft(self, draft_id, booking_ref, row, kind):
        self.data["drafts"][draft_id] = {"booking_ref": booking_ref, "row": row, "kind": kind,
                                         "drafted_at": now_iso()}
        if kind == "confirmation":
            self.data["confirmations"][f"{booking_ref}|{row}"] = {"draft_id": draft_id, "sent_at": None}
        elif kind in ("deposit_reminder", "balance_reminder"):
            self.data["reminders"][f"{booking_ref}|{kind.split('_')[0]}"] = {"draft_id": draft_id,
                                                                            "drafted_at": now_iso()}

    # --- person's review of each draft (Telegram: accept / deny / rewrite / info) ---
    def open_review(self, draft_id, **fields):
        n = str(self.data["next_review"])
        self.data["next_review"] += 1
        self.data["reviews"][n] = {"draft_id": draft_id, "status": REVIEW_OPEN, "version": 1,
                                   "opened_at": now_iso(), "history": [], **fields}
        return n

    def review(self, n):
        n = str(n).lstrip("#")
        if n not in self.data["reviews"]:
            raise KeyError(f"no draft #{n}")
        return n, self.data["reviews"][n]

    def review_by_draft(self, draft_id):
        return next((n for n, r in self.data["reviews"].items() if r["draft_id"] == draft_id), None)

    def close_review(self, n, status, note=""):
        r = self.data["reviews"][n]
        r["history"].append({"at": now_iso(), "status": status, "note": note})
        r["status"] = status

    def forget_confirmation(self, booking_ref, row):
        """A person deleted the confirmation draft (wrong, or a test): allow a new one for this row."""
        key = f"{booking_ref}|{row}"
        entry = self.data["confirmations"].pop(key, None)
        if entry:
            self.data["drafts"].pop(entry.get("draft_id"), None)
            for n, r in self.data["reviews"].items():
                if r.get("draft_id") == entry.get("draft_id") and r.get("status") in (REVIEW_OPEN, "approved"):
                    self.close_review(n, "gone", "forget-confirmation: a person deleted it")
        return entry is not None

    def confirmation_drafted(self):
        """(booking_ref, row) pairs that already have a confirmation draft."""
        out = set()
        for key in self.data["confirmations"]:
            ref, _, row = key.rpartition("|")
            out.add((ref, int(row)))
        return out

    def reminder_drafted(self, booking_ref, which):
        return f"{booking_ref}|{which}" in self.data["reminders"]
