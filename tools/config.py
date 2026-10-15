"""Settings from environment variables. Secrets live on the host, never in these files.

A `.env` file at the project root is loaded first if present (see `.env.example`).
Variables already set in the environment win, and blank values in `.env` are ignored.
"""
import os

ENV_FILE = os.path.join(os.path.dirname(__file__), "..", ".env")


def load_env(path=ENV_FILE):
    if not os.path.exists(path):
        return
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            k, v = k.strip(), v.strip().strip('"').strip("'")
            if v:
                os.environ.setdefault(k, v)


load_env()

MAILBOX = os.environ.get("EMI_MAILBOX", "sales@haya-hotels.com")
SHEET_ID = os.environ.get("EMI_SHEET_ID", "16pFhmPB6sQB7Bu8S61qq094cvq8Ie1OcRGCeC-CR440")
SHEET_TAB = os.environ.get("EMI_SHEET_TAB", "Intake")
STATE_PATH = os.environ.get("EMI_STATE_PATH", "emi-state.json")


def _need(name):
    v = os.environ.get(name)
    if not v:
        raise RuntimeError(f"{name} is not set")
    return v


SIM_DIR = os.environ.get("EMI_SIM_DIR")  # test emails from files, drafts to files (tools/sim_mail.py)


def mail():
    if SIM_DIR:
        from .sim_mail import SimMail
        return SimMail(SIM_DIR)
    from .graph_mail import ClientCredentialsToken, DeviceCodeToken, GraphMail
    if os.environ.get("EMI_AUTH") == "device":
        # Personal Outlook.com test mailbox: sign in once with a code, then the cached refresh token.
        token = DeviceCodeToken(_need("EMI_CLIENT_ID"), os.environ.get("EMI_TOKEN_CACHE", ".emi-token.json"))
        return GraphMail("me", token)
    if os.environ.get("EMI_AUTH") == "delegated":
        # HAYA tenant, no client secret: sign in once as sales@ with a code, then the cached refresh token.
        token = DeviceCodeToken(_need("EMI_CLIENT_ID"), os.environ.get("EMI_TOKEN_CACHE", ".emi-token.json"),
                                tenant=_need("EMI_TENANT_ID"))
        return GraphMail(MAILBOX, token)
    token = ClientCredentialsToken(_need("EMI_TENANT_ID"), _need("EMI_CLIENT_ID"), _need("EMI_CLIENT_SECRET"))
    return GraphMail(MAILBOX, token)


def sheet():
    from .intake_sheet import IntakeSheet, google_service_account_transport
    return IntakeSheet(SHEET_ID, google_service_account_transport(_need("EMI_GOOGLE_KEYFILE")), tab=SHEET_TAB)


def state():
    from .state import State
    # A simulation never moves the real scan clock or the real processed/draft records.
    return State(os.path.join(SIM_DIR, "state.json") if SIM_DIR else STATE_PATH)
