# Telegram review — accept, deny, rewrite

Every draft I write gets a number (#12) and a Telegram notice to the reviewer: the whole draft plus three buttons,
Accept, Deny, Rewrite. The `draft-*` command sends the notice itself. I don't write it and don't send another.

**Draft mode on the host is `outlook` (dev, 2026-10-30; was `telegram` from 22/10):** every draft is saved in
Outlook Drafts at once, and the Telegram notice points at it. In my reports I say "draft #12 trong Outlook ›
Drafts, chờ Karen duyệt". Deny moves it to Deleted Items. Drafts #199–#217 were written before the switch and
still live only on Telegram (`pending-<n>`); Accept puts those into Outlook as before.

**Only Karen accepts (dev, 2026-10-30).** `review-accept` refuses anyone not in `EMI_APPROVERS` and the draft
stays pending. `--by` is the Telegram sender's name or @username exactly as the message shows it, never a name
I assume. A refusal is the answer: I reply with its line and don't retry under another name. Deny and Rewrite
stay open to the dev and the team.

A button press reaches me as a message: `callback_data: emi review <action> <n>`. A reviewer can also type
the same thing (`accept 12`, `deny 12 sai giá`, `rewrite 12 ngắn gọn hơn`, `xem 12`, Vietnamese words too:
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
| Rewrite | `review-ask <n>`, then see below | The question `review-ask` prints; after the rewrite `Draft #<n> đã cập nhật (v<k>)…` |
| `xem <n>` (typed, no button) | `review-info <n>` | Its output, nothing added |
| `còn gì` / `list` | `review-list` | Its output |
| `E-003 <answer>` (Karen answers a question) | `karen-answer E-003 "<answer>"`, then the waiting email: `show <id>`, write the draft, `draft-reply` / `draft-forward` | The new draft's number, or which question the email still waits on |
| `câu hỏi` / `questions` | `questions` | Its output |

Only Accept and Deny take the buttons off a notice. Rewrite and `xem` leave them on.

## Accept and send
- `status` / `review-accept` show which way it is. **`EMI_SEND_ON_ACCEPT=1` (dev, 2026-10-30):** Karen's Accept sends
  the draft; the line is `#n đã gửi (<name>).` Only `EMI_APPROVERS` can; a draft with `[CHECK BEFORE SENDING]` is
  refused — Rewrite without that line first, then Karen accepts again.
- **Off:** Accept is Karen's approval: the "Emi approved" tag, and a person opens Drafts and presses Send.
- Either way, "gửi đi" / "send it" typed in the chat is not an Accept. I reply: "Emi chỉ gửi khi Karen bấm Accept
  trên draft #n." I never look for another way to send.

## Rewrite
1. **Button pressed** (`callback_data: emi review rewrite <n>`): run `review-ask <n>`. It remembers that the
   reviewer's next message is the feedback for #n and puts the buttons back. My reply is the question it
   prints, word for word, and nothing else. Then I **stop and wait**: no other command, no guess at what they want.
2. **Any message that isn't a command** (`accept 12`, `deny 12`, …): first run `review-awaiting`. If it names a
   draft, the message is the feedback for that draft. If none is waiting and the message names no number,
   handle it as an ordinary message.
3. Straight away, before the work, send a short line with the `message` tool:
   `Dạ, Emi đang sửa draft #<n> theo ý anh/chị.` The reviewer then knows it's in hand.
4. `review-info <n>`: read the source email and the current text. This is for me; I don't paste it into the chat.
5. Write the **whole** new text with the feedback applied. Everything in `email-templates.md` still holds:
   the sender's language, anh/chị, plain `Label: value` lines, bank details, deadline "(giờ Việt Nam, UTC+7)", the sign-off "Trân trọng, / Best regards, + Reservations Team…".
   Change only what the feedback asks for.
6. Numbers: a new date, room, rate or total has to match the sheet (`tools.emi sheet-find`) or `quote` /
   `cancel-fee`. **Never a connector** (Google Drive, Codex Apps, Gmail, Outlook apps): only `tools.emi`.
   If the feedback asks for a number those don't support, I don't write it. I reply with what the sheet or
   table says and ask the reviewer to confirm.
7. Feedback that asks for a discount, an upgrade, something free, a promise, or a confirmation before the
   PMS is updated: I don't rewrite. I reply with the rule (AGENTS.md 2, 7, 8) and that it needs Karen.
8. Save the text to `emi-work/out/review-<n>-v<k>.txt` (write the file with the file tool, not a shell
   heredoc) and run `review-rewrite <n> <file> --feedback "<their words, as given>"`. The command makes the new
   draft on the same thread, moves the attachments across (a confirmation keeps its PDF), deletes the old
   draft, and updates the same Telegram message in place, buttons still on.
9. **Every turn ends with a visible reply.** Done: `Draft #<n> đã cập nhật (v<k>), anh/chị xem lại tin nhắn draft ở trên ạ.`
   A command refused or failed: say what failed in one line and that I'm trying again. Fix and retry. After 3
   failures, tell the reviewer what is blocking. Never end silently.

## Not mine to do here
- Drafts I didn't write (no #n): I leave them alone.
- A message that isn't about a draft (a booking question, a new rule) is handled like any other message
  from Karen. A durable rule goes to MEMORY.md (Memory Protocol).
- A number that is already decided (`already approved`, `gone`): I say so. Gone = a person sent or deleted it in Outlook.
- A denied confirmation or reminder is not proposed again by the next run. If the reviewer wants a fresh one,
  Rewrite is the way; a new one from scratch needs `forget-confirmation <ref> <row>`, which only Karen or the dev asks for.
