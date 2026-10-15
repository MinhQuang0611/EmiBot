"""Scenarios for testing Emi end to end without real email (tools/sim_mail.py).

test/sim/<scenario>/inbox/*.eml   the emails, as an agency would send them
test/sim/<scenario>/scenario.json what to clean before, what the sheet and drafts must show after

sim-reset copies the inbox to <work dir>/sim/<scenario>/ (fresh state, no drafts) and deletes the
scenario's TEST- rows from the sandbox sheet; sim-check grades the sheet and the drafts.
"""
import glob
import json
import os
import shutil

SCENARIOS = os.path.join(os.path.dirname(__file__), "..", "test", "sim")


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
        for text in e.get("notes_contains", []):
            verdict(any(text in r.get("notes", "") for r in rows), f"{label}: notes mention {text!r}")
        for r in rows:
            out(f"     row {r['_row']}: " + json.dumps({k: v for k, v in r.items() if v and k != '_row'},
                                                     ensure_ascii=False))

    target = run_dir(work_dir, name)
    drafts = []
    for p in sorted(glob.glob(os.path.join(target, "drafts", "*.json"))):
        with open(p, encoding="utf-8") as f:
            drafts.append(json.load(f))
    rules = sc.get("drafts", {})
    state_path = os.path.join(target, "state.json")
    confirmations = 0
    if os.path.exists(state_path):
        with open(state_path, encoding="utf-8") as f:
            confirmations = len(json.load(f).get("confirmations", {}))
    if "max_confirmations" in rules:
        verdict(confirmations <= rules["max_confirmations"],
                f"confirmation drafts: {confirmations}, at most {rules['max_confirmations']}")
    for text in rules.get("must_not_contain", []):
        bad = [d["id"] for d in drafts if text.lower() in d["text"].lower()]
        verdict(not bad, f"no draft says {text!r}" + (f" (found in {bad})" if bad else ""))
    out(f"drafts written: {len(drafts)}")
    for d in drafts:
        out(f"--- {d['id']} {d['kind']} to {', '.join(d['to'])} | {d['subject']}"
            + (f" | attachments {[a['name'] for a in d['attachments']]}" if d["attachments"] else ""))
        out(d["text"])
    out(f"\nRESULT: {'PASS' if not fails else 'FAIL'} ({len(fails)} failed check(s))")
    return not fails
