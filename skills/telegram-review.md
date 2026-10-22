# Telegram review — accept, deny, rewrite, info

Every draft I save gets a number (#12) and a Telegram notice to the reviewer, with four buttons. The
notice is sent by the `draft-*` command itself. I don't write it, and I don't send another one.

A button press reaches me as a message: `callback_data: emi review <action> <n>`. A reviewer can also type
the same thing (`accept 12`, `deny 12 sai giá`, `rewrite 12 thêm giờ đón`, `info 12`, Vietnamese words too:
`duyệt 12`, `bỏ 12`, `sửa 12 …`, `xem 12`). Everything runs from `/data/emi` with `.venv/bin/python -m tools.emi`.

| Action | What I run | What I reply |
|---|---|---|
| accept | `review-accept <n> --by "<sender's Telegram name>"` | The command's line, word for word |
| deny | `review-deny <n> --reason "<their words, if any>" --by "<name>"` | The command's line |
| info | `review-info <n>` | Its output. Keep the draft text whole; shorten the source email if it's too long |
| rewrite | see below | One line: `#<n> v<k> đã lưu — xem tin mới ở trên.` |
| list (`còn gì`, `list`) | `review-list` | Its output |

## Accept is not send
Accept only tags the draft "Emi approved" in Outlook. A person still opens Drafts and presses Send
(AGENTS.md rule 1). If someone says "gửi đi", "send it" or similar, I reply: "Emi không gửi email. Draft #n
nằm trong Outlook › Drafts, anh/chị mở và bấm Send." I never look for another way to send.

## Rewrite
1. The button gives no text. I reply `Draft #<n>: anh/chị muốn sửa gì?` and the reviewer's next
   message is the feedback for #n, unless it is clearly another command.
2. `review-info <n>`: read the source email and the current text.
3. Write the **whole** new text with the feedback applied. Everything in `email-templates.md` still holds:
   the sender's language, anh/chị, `**Label:**`, bank details, deadline "(giờ Việt Nam, UTC+7)", "Best, / HAYA Team".
4. Numbers: a new date, room, rate or total has to match the sheet (`sheet-find`) or `quote` / `cancel-fee`.
   If the feedback asks for a number those don't support, I don't write it. I reply with what the sheet or
   table says and ask the reviewer to confirm, or to fix the sheet first.
5. Feedback that asks for a discount, an upgrade, something free, a promise, or a confirmation before the
   PMS is updated: I don't rewrite. I reply with the rule (AGENTS.md 2, 7, 8) and that it needs Karen. If Karen
   herself asked, I list it as her decision in my report and still don't promise anything in the email.
6. Save the text to `emi-work/out/review-<n>-v<k>.txt` and run
   `review-rewrite <n> <file> --feedback "<their words, as given>"`. The command makes the new draft on the
   same thread, moves the attachments across (a confirmation keeps its PDF), deletes the old draft, and sends
   the new notice.
7. If the command refuses (a confirmation missing a must-have line, for example), I fix the text and run
   it again. After 3 failures I tell the reviewer what is blocking.

## Not mine to do here
- Drafts I didn't write (no #n): I leave them alone.
- A message that isn't about a draft (a booking question, a new rule) is handled like any other message
  from Karen. A durable rule goes to MEMORY.md (Memory Protocol).
- A number that is already decided (`already approved`, `gone`): I say so. Gone = a person sent or deleted it in Outlook.
