---
name: task-monitor
description: Use when tracking clipping tasks and verified delivery.
---
# Portable clipping progress
Use `python scripts/fingerprint_progress.py start TITLE --stages Source,Select,Render,QA,Deliver` from CLIP_ROOT. Save the returned ID, then `stage ID STAGE STATUS --detail TEXT`, `note ID TEXT`, `show ID`, and `finish ID --success --summary TEXT` (or `--fail`). One task, one record, including retries. State is local in outputs/task-monitors. No default bot, account or chat is included. Host UI can relay progress. Do not claim a local JSON record is a Telegram live card. Completion means verified delivery, not render queued. Never expose credentials or signaled source URLs in status records.
