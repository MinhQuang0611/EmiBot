# Dựng Emi lên host OpenClaw (Hostinger)

Dành cho dev dựng Emi. Quyết định 2026-10-09: Emi là **agent thứ hai** trên OpenClaw đang chạy ở VPS Hostinger `srv2000138` (201.18.208.83). Phần n8n/FastAPI trong `emi/` và `Dockerfile` không dùng cho cách này.

## Host thực tế (kiểm tra 2026-10-09, chỉ đọc)
| Mục | Giá trị |
|---|---|
| VPS | Ubuntu 24.04, giờ hệ thống UTC, có git, rsync, flock, Docker |
| OpenClaw | Container `openclaw-lk3h-openclaw-1`, image `ghcr.io/hostinger/hvps-openclaw`, **2026.9.4**, compose ở `/docker/openclaw-lk3h` |
| Ổ bền | Host `/docker/openclaw-lk3h/data` = `/data` trong container (`HOME=/data`, nên `~/.openclaw` = `/data/.openclaw`) |
| Trong container | Debian 13, Python 3.13 của hệ thống (không có ensurepip, có pip), flock, linuxbrew (chỉ có `brew`). **Không có git, rsync** |
| Agent hiện có | `main` (mặc định, WhatsApp). `plugins.allow` có `telegram` |
| Cũng chạy trên VPS | n8n, traefik |

## Bố cục của Emi
| Host | Trong container | Là gì |
|---|---|---|
| `/docker/openclaw-lk3h/data/emi` | `/data/emi` | git clone repo `EmiBot` |
| `…/data/emi/.venv` | `/data/emi/.venv` | venv tạo **trong container** (Python 3.13). Nếu image đổi bản Python thì tạo lại venv |
| `…/data/emi/.env` | `/data/emi/.env` | secret + cấu hình, chmod 600; `tools/config.py` tự đọc |
| `…/data/emi/secrets/google-service-account.json` | `/data/emi/secrets/…` | key Google, chmod 600 |
| `…/data/.openclaw/workspace-emi` | `/data/.openclaw/workspace-emi` | workspace agent `emi` (persona, skills, rate-knowledge) |
| `…/data/emi-logs` | `/data/emi-logs` | log từng job |

Phân việc: **host** làm git pull, sync workspace, status, cron. **Container** chạy Python và `openclaw`.
Trên máy dev, alias SSH là `haya-openclaw` (key `~/.ssh/emi_vps_ssh_key`, nạp vào ssh-agent).

Viết tắt dùng bên dưới: `D=/docker/openclaw-lk3h/data`, `C=openclaw-lk3h-openclaw-1`.

## Bước 1 — Lấy code về host
Repo private → deploy key **chỉ đọc** trên host:
```bash
ssh-keygen -t ed25519 -f ~/.ssh/emibot_deploy -N "" -C "srv2000138 deploy"
cat ~/.ssh/emibot_deploy.pub
```
GitHub → `EmiBot` → **Settings → Deploy keys → Add** → dán, **không** tick "Allow write access". Rồi:
```bash
cat >> ~/.ssh/config <<'EOF'
Host github-emibot
  HostName github.com
  IdentityFile ~/.ssh/emibot_deploy
EOF
D=/docker/openclaw-lk3h/data; C=openclaw-lk3h-openclaw-1
git clone -b deploy-openclaw git@github-emibot:MinhQuang0611/EmiBot.git $D/emi
chown -R 1000:1000 $D/emi
git config --global --add safe.directory $D/emi   # repo thuộc uid 1000, git chạy bằng root
# Python Debian trong container không có ensurepip: tạo venv không kèm pip, cài bằng pip hệ thống
docker exec $C sh -c 'cd /data/emi && python3 -m venv --without-pip .venv && python3 -m pip --python .venv/bin/python install -q -r requirements.txt'
docker exec $C sh -c 'cd /data/emi && .venv/bin/python -m unittest discover -s tools/tests -t . && .venv/bin/python -m tools.acceptance send-blocked'
```
Đạt: unit test OK, `PASS: every send endpoint is refused`.

## Bước 2 — Secret
Trên host:
```bash
D=/docker/openclaw-lk3h/data
mkdir -p $D/emi/secrets && chmod 700 $D/emi/secrets
cp $D/emi/.env.example $D/emi/.env && chmod 600 $D/emi/.env
```
Chép key Google từ **máy Windows**:
```powershell
scp "C:\Code\Emi - HAYA Emails\tools\ascendant-nova-478100-q0-51467066def5.json" haya-openclaw:/docker/openclaw-lk3h/data/emi/secrets/google-service-account.json
```
Trên host: `chmod 600 $D/emi/secrets/google-service-account.json && chown -R 1000:1000 $D/emi/secrets $D/emi/.env`, rồi `nano $D/emi/.env`:
```
EMI_GOOGLE_KEYFILE=/data/emi/secrets/google-service-account.json
EMI_SHEET_ID=1VgGWbqslgXCOJ5DWiS95cWSmGkGpqtT03LaETkhLJFQ
EMI_SHEET_TAB=Intake
EMI_STATE_PATH=/data/emi/emi-state.json
# EMI_TENANT_ID / EMI_CLIENT_ID / EMI_CLIENT_SECRET: để trống tới khi admin M365 cấp app cho sales@
```
Đường dẫn trong `.env` là đường dẫn **trong container** (`/data/...`). Sheet = SANDBOX cho tới khi Karen cho dùng sheet thật. Kiểm tra:
```bash
docker exec $C sh -c 'cd /data/emi && .venv/bin/python -m tools.acceptance sheet-header && .venv/bin/python -m tools.acceptance sheet-roundtrip'
```

## Bước 2b — Chọn model AI (OpenAI hoặc Anthropic)
Emi dùng model riêng, không đổi model mặc định của `main`. Hai chỗ cần điền:

| File trên host | Biến | Ghi chú |
|---|---|---|
| `/docker/openclaw-lk3h/data/emi/.env` | `EMI_LLM_PROVIDER=anthropic` hoặc `openai` | Bắt buộc |
| | `EMI_LLM_MODEL=` | Để trống = mặc định: `anthropic/claude-sonnet-5-5` / `openai/gpt-5.6-sol`. Nếu điền phải bắt đầu bằng tên provider |
| `/docker/openclaw-lk3h/.env` (env của container OpenClaw) | `ANTHROPIC_API_KEY=...` hoặc `OPENAI_API_KEY=...` | Key thật. Chỉ nhập trên host, không dán vào chat/git |

Sau khi thêm key: `cd /docker/openclaw-lk3h && docker compose up -d` (tạo lại container, `main` khởi động lại theo; dữ liệu `/data` giữ nguyên). Rồi:
```bash
/docker/openclaw-lk3h/data/emi/deploy/set-model.sh --dry-run   # kiểm tra, không ghi gì
/docker/openclaw-lk3h/data/emi/deploy/set-model.sh             # áp model cho agent emi
```
Script báo key có/thiếu (không in giá trị), key đã vào container chưa, và nếu `emi` chưa được tạo thì in sẵn lệnh `agents add` với đúng model. Đổi provider sau này: sửa `EMI_LLM_PROVIDER`, thêm key tương ứng, chạy lại script.

## Bước 3 — Agent `emi`
**Không** chạy lại onboarding, **không** bấm Restart trên trang Hostinger, **không** sửa tay `openclaw.json` (OpenClaw tự giữ `.bak` và `.last-good`, nhưng đừng thử).
```bash
D=/docker/openclaw-lk3h/data; C=openclaw-lk3h-openclaw-1
$D/emi/deploy/set-model.sh   # lần đầu: in ra lệnh agents add với model theo EMI_LLM_PROVIDER, chạy lệnh đó
# docker exec $C openclaw agents add emi --workspace /data/.openclaw/workspace-emi --model <model> --non-interactive
/docker/openclaw-lk3h/data/emi/deploy/sync-workspace.sh
docker exec $C openclaw agents list --bindings
```
Đạt: có `main` và `emi`; workspace có `SOUL.md`, `AGENTS.md`, `skills/`, `docs/rate-knowledge/`, `DEPLOYED_VERSION`. `main` không đổi.

Thêm skill `anti-ai-slop` vào `$D/.openclaw/workspace-emi/skills/` (bản của Karen: `/Users/karennguyen/Desktop/anti-ai-slop-SKILL.md`).
Trong `$D/.openclaw/workspace-emi/MEMORY.md` (bản trên host), sửa mục "Infrastructure": code mail/sheet ở `/data/emi/tools`, gọi bằng `cd /data/emi && .venv/bin/python -m tools.<module>`.

Thử một lượt không có cron:
```bash
docker exec $C openclaw agent --agent emi -m "Đọc DEPLOYED_VERSION và cho biết em là ai, đang chạy bản nào."
```

## Bước 4 — Telegram (bot riêng cho Emi)
1. BotFather → bot mới (Karen đặt tên). Không dùng lại token bot của agent khác — hai process poll một token sẽ conflict.
2. Thêm token làm một Telegram account riêng rồi bind vào `emi` (`openclaw channels --help`; `openclaw agents add` có cờ `--bind telegram:<accountId>` nếu làm lại từ đầu).
3. Chỉ cho phép Telegram user ID của Karen (và của dev khi test).
4. `docker exec $C openclaw channels status --probe` → Telegram **works**; nhắn bot → Emi trả lời; `main` vẫn chạy như cũ.

## Bước 5 — Cron (CHƯA BẬT)
Bật khi đủ: quyền Graph cho sales@ đã test (`mail-read` → `attach-pdf`), Karen xác nhận agent khác không còn đụng email sales@, Karen OK giai đoạn 1.
Host chạy UTC. `crontab -e` trên host:
```
0 23,0-15 * * *  docker exec openclaw-lk3h-openclaw-1 /data/emi/deploy/run-job.sh inbox
30 23,0-15 * * * docker exec openclaw-lk3h-openclaw-1 /data/emi/deploy/run-job.sh confirmations
0 1,8 * * *      docker exec openclaw-lk3h-openclaw-1 /data/emi/deploy/run-job.sh payments
30 14 * * *      docker exec openclaw-lk3h-openclaw-1 /data/emi/deploy/run-job.sh report
```
`run-job.sh` chạy trong container: precheck trước (không có việc thì không đánh thức agent), khóa chống chạy chồng, log vào `/data/emi-logs/<job>.log`.

## Cập nhật (mỗi lần có commit mới)
Từ máy dev:
```bash
ssh haya-openclaw 'D=/docker/openclaw-lk3h/data; git -C $D/emi pull --ff-only && chown -R 1000:1000 $D/emi && docker exec openclaw-lk3h-openclaw-1 sh -c "cd /data/emi && python3 -m pip --python .venv/bin/python install -q -r requirements.txt" && $D/emi/deploy/sync-workspace.sh && $D/emi/deploy/status.sh'
```
`MEMORY.md` và `memory/` trong workspace không bị ghi đè — đó là phần Emi tự học.

## Theo dõi
```bash
ssh haya-openclaw /docker/openclaw-lk3h/data/emi/deploy/status.sh
ssh haya-openclaw tail -f /docker/openclaw-lk3h/data/emi-logs/inbox.log
```
Nháp của Emi trong Outlook có category **Emi**.

## Gỡ Emi
Xóa các dòng `run-job.sh` khỏi crontab → `docker exec $C openclaw agents delete emi` (xem `--help`) → gỡ binding Telegram. Agent `main` không bị ảnh hưởng.
