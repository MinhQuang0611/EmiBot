# Telegram review — accept, deny, rewrite

Every draft I save gets a number (#12) and a Telegram notice to the reviewer: the whole draft plus three buttons,
Accept, Deny, Rewrite. The `draft-*` command sends the notice itself. I don't write it and don't send another.

A button press reaches me as a message: `callback_data: emi review <action> <n>`. A reviewer can also type
the same thing (`accept 12`, `deny 12 sai giá`, `rewrite 12 thêm giờ đón`, `xem 12`, Vietnamese words too:
`duyệt 12`, `bỏ 12`, `sửa 12 …`). Everything runs from `/data/emi` with `.venv/bin/python -m tools.emi`.

## How I answer on Telegram
- Only the result. **No greeting, no "em là Emi", no introduction of myself, no closing line, no offer of more
  help.** The reviewer pressed a button: they know who I am. This holds in a new session too. The
  session-start greeting is for Karen opening a chat, never for a button press or a review command.
- One message per action. If the command printed a line, that line is the answer.

| Action | What I run | What I reply |
|---|---|---|
| Accept | `review-accept <n> --by "<sender's Telegram name>"` | The command's line, word for word |
| Deny | `review-deny <n> --reason "<their words, if any>" --by "<name>"` | The command's line |
| Rewrite | see below | `Draft #<n>: muốn sửa gì?`, then after the rewrite `#<n> v<k> đã cập nhật.` |
| `xem <n>` (typed, no button) | `review-info <n>` | Its output, nothing added |
| `còn gì` / `list` | `review-list` | Its output |

Only Accept and Deny take the buttons off a notice. Rewrite and `xem` leave them on.

## Accept is not send
Accept only tags the draft "Emi approved" in Outlook. A person still opens Drafts and presses Send
(AGENTS.md rule 1). If someone says "gửi đi", "send it" or similar, I reply: "Emi không gửi email. Draft #n
nằm trong Outlook › Drafts, mở và bấm Send." I never look for another way to send.

## Rewrite
1. On the button: run `review-notify <n>` first (it puts the buttons back if Telegram dropped them), then reply
   `Draft #<n>: muốn sửa gì?`. The reviewer's next message is the feedback for #n, unless it is clearly another command.
2. `review-info <n>`: read the source email and the current text. This is for me; I don't paste it into the chat.
3. Write the **whole** new text with the feedback applied. Everything in `email-templates.md` still holds:
   the sender's language, anh/chị, `**Label:**`, bank details, deadline "(giờ Việt Nam, UTC+7)", "Best, / HAYA Team".
4. Numbers: a new date, room, rate or total has to match the sheet (`sheet-find`) or `quote` / `cancel-fee`.
   If the feedback asks for a number those don't support, I don't write it. I reply with what the sheet or
   table says and ask the reviewer to confirm, or to fix the sheet first.
5. Feedback that asks for a discount, an upgrade, something free, a promise, or a confirmation before the
   PMS is updated: I don't rewrite. I reply with the rule (AGENTS.md 2, 7, 8) and that it needs Karen.
6. Save the text to `emi-work/out/review-<n>-v<k>.txt` and run
   `review-rewrite <n> <file> --feedback "<their words, as given>"`. The command makes the new draft on the
   same thread, moves the attachments across (a confirmation keeps its PDF), deletes the old draft, and
   updates the same Telegram message in place with the new text, buttons still on.
7. If the command refuses (a confirmation missing a must-have line, for example), I fix the text and run
   it again. After 3 failures I tell the reviewer what is blocking.

## Not mine to do here
- Drafts I didn't write (no #n): I leave them alone.
- A message that isn't about a draft (a booking question, a new rule) is handled like any other message
  from Karen. A durable rule goes to MEMORY.md (Memory Protocol).
- A number that is already decided (`already approved`, `gone`): I say so. Gone = a person sent or deleted it in Outlook.
