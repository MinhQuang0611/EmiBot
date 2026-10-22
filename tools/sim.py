"""Scenarios for testing Emi end to end without real email (tools/sim_mail.py).

test/sim/<scenario>/inbox/*.eml   the emails, as an agency would send them
test/sim/<scenario>/scenario.json what to clean before, what the sheet and drafts must show after

sim-reset copies the inbox to <work dir>/sim/<scenario>/ (fresh state, no drafts) and deletes the
scenario's TEST- rows from the sandbox sheet; sim-check grades the sheet and the drafts.

scenario.json "drafts" rules: max_confirmations, must_not_contain [text], must_include_forward_to [address],
kinds {kind: n} (n >= 1 = at least n drafts of that --kind, 0 = none), reply_to [address] (a reply goes to it),
no_reply_to_domain [domain] (no reply's To is at that domain: a mail forwarded in by our staff is answered to
the original sender), no_forward_to [address] (nothing is forwarded there, e.g. back to the colleague who
forwarded it in). Drafts are read from drafts/ and from
the reviews in state.json, so Telegram-mode drafts (not in Outlook until Accept) are graded too.
"""
import glob
import json
import os
import re
import shutil

SCENARIOS = os.path.join(os.path.dirname(__file__), "..", "test", "sim")


def _digits(text):
    """Drop thousands separators so an amount matches however it was written."""
    return re.sub(r"(?<=\d)[.,](?=\d{3})", "", text)


def scenario_dir(name):
    d = os.path.join(SCENARIOS, name)
    if not os.path.isfile(os.path.join(d, "scenario.json")):
        raise FileNotFoundError(f"no scenario {name!r}; have {sorted(os.listdir(SCENARIOS))}")
    return d


def load(name):
    with open(os.path.join(scenario_dir(name), "scenario.json"), encoding="utf-8") as f:
        return json.load(f)


def run_dir(work_dir, name):
    return os.path.abspath(os.path.join(work_dir, "sim", name))


def reset(sheet, name, work_dir, out=print):
    sc = load(name)
    target = run_dir(work_dir, name)
    shutil.rmtree(target, ignore_errors=True)
    shutil.copytree(os.path.join(scenario_dir(name), "inbox"), os.path.join(target, "inbox"))
    doomed = []
    for rule in sc.get("cleanup", []):
        for r in sheet.find_by_ref(rule["ref"]):
            if "actions" not in rule or r.get("action") in rule["actions"]:
                doomed.append(r["_row"])
    for row in sorted(set(doomed), reverse=True):  # bottom up, so row numbers above stay put
        sheet.delete_test_row(row)
    out(f"sim {name}: {len(glob.glob(os.path.join(target, 'inbox', '*.eml')))} email(s) ready, "
        f"{len(doomed)} old TEST row(s) removed from the sheet")
    out(f"run every command with: EMI_SIM_DIR={target}")
    return target


def collect_drafts(target):
    """Every draft the run wrote, in either draft mode. Telegram mode: a draft waiting for review exists only
    in state.json's reviews (draft id 'pending-<n>'), not in drafts/. Outlook mode (and after Accept): a file
    in drafts/ plus its review. Denied reviews and deleted files don't count.
    Returns ([{id, kind, how, status, to, subject, text, attachments}], state dict)."""
    st = {}
    state_path = os.path.join(target, "state.json")
    if os.path.exists(state_path):
        with open(state_path, encoding="utf-8") as f:
            st = json.load(f)
    files = {}
    for p in sorted(glob.glob(os.path.join(target, "drafts", "*.json"))):
        with open(p, encoding="utf-8") as f:
            d = json.load(f)
        if not d.get("deleted"):
            files[d["id"]] = d
    drafts, seen = [], set()
    for n, r in sorted(st.get("reviews", {}).items(), key=lambda kv: int(kv[0])):
        if r.get("status") == "denied":
            continue
        did = r.get("draft_id") or ""
        if not did.startswith("pending-") and did not in files:
            continue  # sent or deleted in Outlook
        seen.add(did)
        drafts.append({"id": f"#{n}", "kind": r.get("kind", ""), "how": r.get("how", ""),
                       "status": r.get("status", ""), "to": list(r.get("to", [])), "cc": list(r.get("cc", [])),
                       "subject": r.get("subject", ""), "text": r.get("text", ""),
                       "attachments": list(r.get("attachments", []))})
    for did, d in files.items():  # a draft written without a review record
        if did in seen:
            continue
        drafts.append({"id": did, "kind": st.get("drafts", {}).get(did, {}).get("kind", d["kind"]),
                       "how": d["kind"], "status": "outlook", "to": d["to"], "cc": d.get("cc", []),
                       "subject": d["subject"],
                       "text": d["text"], "attachments": [a["name"] for a in d["attachments"]]})
    return drafts, st


def check(sheet, name, work_dir, out=print):
    sc = load(name)
    fails = []

    def verdict(ok, what):
        out(("PASS " if ok else "FAIL ") + what)
        if not ok:
            fails.append(what)

    for e in sc.get("expect", []):
        rows = [r for r in sheet.find_by_ref(e["ref"]) if r.get("action") == e["action"]]
        label = f"{e['ref']} {e['action']}"
        if "rows" in e:
            verdict(len(rows) == e["rows"], f"{label}: {len(rows)} row(s), want {e['rows']}")
        if "rows_min" in e:
            verdict(len(rows) >= e["rows_min"], f"{label}: {len(rows)} row(s), want at least {e['rows_min']}")
        for col, want in e.get("fields", {}).items():
            got = sorted({r.get(col, "") for r in rows})
            verdict(rows and got == [want], f"{label}: {col} = {got}, want {want!r}")
        if "room_codes" in e:
            got = sorted(r.get("room_code", "") for r in rows)
            verdict(got == sorted(e["room_codes"]), f"{label}: room codes {got}, want {sorted(e['room_codes'])}")
        for col in e.get("nonblank", []):
            verdict(rows and all(r.get(col, "").strip() for r in rows), f"{label}: {col} filled on every row")
        for text in e.get("notes_contains", []):  # 2.100.000 = 2,100,000 = 2100000
            verdict(any(_digits(text) in _digits(r.get("notes", "")) for r in rows), f"{label}: notes mention {text!r}")
        for r in rows:
            out(f"     row {r['_row']}: " + json.dumps({k: v for k, v in r.items() if v and k != '_row'},
                                                     ensure_ascii=False))

    target = run_dir(work_dir, name)
    drafts, st = collect_drafts(target)
    rules = sc.get("drafts", {})
    confirmations = len(st.get("confirmations", {}))
    if "max_confirmations" in rules:
        verdict(confirmations <= rules["max_confirmations"],
                f"confirmation drafts: {confirmations}, at most {rules['max_confirmations']}")
    for text in rules.get("must_not_contain", []):
        bad = [d["id"] for d in drafts if text.lower() in d["text"].lower()]
        verdict(not bad, f"no draft says {text!r}" + (f" (found in {bad})" if bad else ""))
    for address in rules.get("must_include_forward_to", []):
        hits = [d["id"] for d in drafts if d["how"] == "forward" and address.lower() in [a.lower() for a in d["to"]]]
        verdict(bool(hits), f"a forward to {address}" + (f" ({hits})" if hits else ": none"))
    replies = [d for d in drafts if d["how"] == "reply"]
    for address in rules.get("reply_to", []):
        hits = [d["id"] for d in replies if address.lower() in [a.lower() for a in d["to"]]]
        verdict(bool(hits), f"a reply to {address}" + (f" ({hits})" if hits else ": none"))
    for domain in rules.get("no_reply_to_domain", []):
        bad = [f"{d['id']} to {a}" for d in replies for a in d["to"] if a.lower().endswith("@" + domain.lower())]
        verdict(not bad, f"no reply to @{domain}" + (f" (found {bad})" if bad else ""))
    for address in rules.get("no_forward_to", []):
        bad = [d["id"] for d in drafts if d["how"] == "forward" and address.lower() in [a.lower() for a in d["to"]]]
        verdict(not bad, f"no forward to {address}" + (f" (found {bad})" if bad else ""))
    for kind, want in rules.get("kinds", {}).items():  # {"request": 1} = at least one; {"inquiry": 0} = none
        got = sum(1 for d in drafts if d["kind"] == kind)
        verdict(got == 0 if want == 0 else got >= want,
                f"drafts of kind {kind!r}: {got}, want " + ("none" if want == 0 else f"at least {want}"))
    if "min_questions" in rules:  # a missing fact goes to Karen as a question, not into a draft as a gap
        asked = st.get("questions", {})
        verdict(len(asked) >= rules["min_questions"], f"questions to Karen: {len(asked)}, want at least "
                f"{rules['min_questions']}" + "".join(f"\n       {k}: {q['ask']}" for k, q in asked.items()))
    out(f"drafts written: {len(drafts)}")
    for d in drafts:
        out(f"--- {d['id']} {d['kind']} ({d['how']}, {d['status']}) to {', '.join(d['to'])}"
            + (f" cc {', '.join(d['cc'])}" if d.get("cc") else "") + f" | {d['subject']}"
            + (f" | attachments {d['attachments']}" if d["attachments"] else ""))
        out(d["text"])
    out(f"\nRESULT: {'PASS' if not fails else 'FAIL'} ({len(fails)} failed check(s))")
    return not fails
