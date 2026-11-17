"""Karen's answers, kept for next time (dev, 2026-11-17: "với các case mà cần Karen hỏi đáp hay gì đó, nếu mà Karen
trả lời trên tele thì lưu nó vào memory cho các lần sau luôn").

Every answer recorded with karen-answer is kept twice:
  - in the run state (questions E-nnn, never pruned), which is what the lookup reads;
  - in karen-answers.md next to the state file, every answered question with its date, booking and answer, for a
    person or the agent to read (rewritten whole from the state on each answer, so it never drifts).

ask-karen looks here first: a question Karen has already answered is not asked again (SOUL: "I never make Karen
explain the same thing twice"); her old answer is printed instead. A different case that only looks alike → --again.
"""
import os
import re
import unicodedata

FILE = "karen-answers.md"
SAME = 0.6   # this close → the same question: refused, her answer is shown
NEAR = 0.35  # this close → shown as a hint, the question still goes

STOP = set("""
the and for are was were this that with from have has had not but you your our can could would should will what which
when where who how why does did any all its into about than then them they there their been being also only just more
please confirm check whether still same other such each per via
cho cua cac nhung mot hai voi khong chua duoc hay hoac nay kia thi sau truoc trong ngoai den tren duoi theo neu
khi roi con can xin vui long xac nhan hoi chi emi karen nhe the nao bao nhieu
""".split())


def path_for(st):
    return os.path.join(os.path.dirname(os.path.abspath(st.path)), FILE)


def _plain(text):
    text = unicodedata.normalize("NFD", text or "").replace("đ", "d").replace("Đ", "D")
    return "".join(c for c in text if unicodedata.category(c) != "Mn").lower()


def words(text):
    return {w for w in re.findall(r"[a-z0-9]+", _plain(text)) if len(w) >= 3 and w not in STOP}


def score(a, b):
    a, b = words(a), words(b)
    return 2 * len(a & b) / (len(a) + len(b)) if a and b else 0.0


def answered(st):
    return {k: v for k, v in st.data.get("questions", {}).items() if v.get("answer") is not None}


def similar(st, question, ref="", least=NEAR):
    """Answered questions like this one, closest first: [(score, qid, q)]. The same booking adds to the score."""
    out = []
    for qid, q in answered(st).items():
        s = score(question, q["ask"])
        if ref and q.get("booking_ref") and _plain(ref) == _plain(q["booking_ref"]):
            s += 0.15
        if s >= least:
            out.append((round(min(s, 1.0), 2), qid, q))
    return sorted(out, key=lambda x: (-x[0], x[1]))


def line(qid, q):
    when = (q.get("answered_at") or "")[:10]
    ref = f" · {q['booking_ref']}" if q.get("booking_ref") else ""
    return f"{qid}{ref} ({when}) — Q: {q['ask']} — Karen: {q['answer']}"


def write(st):
    """karen-answers.md from the state, newest first."""
    rows = sorted(answered(st).items(), key=lambda kv: (kv[1].get("answered_at") or "", kv[0]), reverse=True)
    text = ["# Karen's answers", "",
            "Every question Emi asked Karen (ask-karen) and her answer (karen-answer), newest first. Written by "
            "tools/karen_memory.py from the run state; don't edit by hand. ask-karen reads these before asking. "
            "A rule meant for every later case also goes to MEMORY.md.", ""]
    text += [f"- {line(qid, q)}" for qid, q in rows]
    p = path_for(st)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    tmp = p + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write("\n".join(text) + "\n")
    os.replace(tmp, p)
    return p
