"""No test reaches the real Telegram group, whatever .env holds on the machine running them. config.telegram() gives
None without a chat id; a test that needs notices passes its own fake. (05/11: running the suite on the host put a
false "Stop sell hôm nay chưa làm được" in the group.) Blank, not removed: config's .env loader only fills unset names."""
import os

os.environ["EMI_TELEGRAM_CHAT_ID"] = ""
