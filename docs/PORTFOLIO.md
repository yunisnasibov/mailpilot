# MailPilot — AI Email Triage & Reply Assistant

## Role
Python Developer | AI Workflow Automation & API Integration

## Description
MailPilot organizes incoming business emails and prepares replies for human review. A live n8n Gmail trigger passes each test email to a Python backend. Gemini classifies its category, priority and sentiment, summarizes the request and drafts a response. SQLite preserves the record and Gmail receives a real draft. The dashboard supports editing, approval and completion. Verified with a dedicated test account; no emails are sent automatically. Personal portfolio project, not a client deployment.

## Skills
Python · n8n · API Integration · Generative AI · Workflow Automation

## Case study
**Problem:** Small teams manually sort incoming requests and repeatedly write similar replies.

**Solution:** Turn incoming email into an organized queue with clear priorities, concise summaries and editable drafts.

**Workflow:** Gmail → n8n → FastAPI → Gemini → SQLite → Gmail Draft → Human Review.

**Hero demo:** “MailPilot-Test — Login problem”: a team cannot access its customer portal and requests help today. Result: **Support / High → Gmail draft**.

**Verified result:** On September 9, 2026, a test support inquiry automatically triggered n8n, received Support / High classification and created a Gmail draft. Execution took approximately 16.5 seconds after detection; Gmail is polled once per minute. This is one test observation, not a service-level guarantee or measured client time saving.

**Boundaries:** The local demo watches only subjects containing MailPilot-Test. Google Sheets and notifications are optional future integrations. Dashboard approval does not send mail. Edits in the dashboard are local and must be copied to an existing Gmail draft when needed.

## Short demo storyboard (28 seconds)
1. 0–5 seconds: Original test inquiry, subject and problem readable.
2. 5–11 seconds: Actual successful n8n trigger execution, showing the connected nodes.
3. 11–19 seconds: Dashboard analysis — Support, High, summary and reply draft.
4. 19–28 seconds: Actual Gmail draft, with “Human review before sending”.

The [28-second demo GIF](images/mailpilot-demo.gif) uses captured results from this same test: the Gmail inquiry, successful n8n execution, Support / High analysis and real Gmail draft. It is an edited screenshot walkthrough, not a continuous live screen recording. Personal addresses and unrelated inbox content are excluded from the captures. Use [the dashboard screenshot](images/support-high-demo.png) as the main portfolio image.
