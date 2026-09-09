# Verification record

Date: 2026-09-09. Dedicated test account, fictional business inquiries.

| Test | Evidence | Outcome |
|---|---|---|
| Manual end-to-end | n8n execution 6, manual, success | Sales / High; real Gmail draft receipt stored |
| Automatic end-to-end | n8n execution 7, trigger, success | Support / High; real Gmail draft receipt stored |
| Automatic timing | 07:38:09.839–07:38:26.315 UTC | 16.476 seconds after detection |
| Local reliability | Four backend test cases | Passed |
| Frontend | Vite production build | Passed |

Neither workflow contains a send-email operation. Approval stores a local review decision. A stored Gmail draft ID is returned by Gmail's create-draft operation, then recorded by the final n8n node. No Google credentials, mailbox databases or execution payloads belong in the public repository.

Automatic tests require both local services to remain running and an authorized Google credential. This is a local portfolio demonstration, not an always-on hosted service.
