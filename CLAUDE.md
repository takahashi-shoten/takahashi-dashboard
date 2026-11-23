# Project guidance for Claude Code

This repository is an AI-run revenue business (YouTube first). **Read `docs/MANAGEMENT_PRINCIPLES.md` first**; it is the permanent operating principle.

Key rules (details in that file):
- The goal is a self-running loop of experiments -> publish -> measure -> diagnose -> improve, not "a great video" or "one viral hit".
- Plan from human desires with evidence (competitor URLs, dates, views, subscriber counts; unverified = "未確認"); the AI chooses and justifies the plan, the owner is not asked to judge scripts.
- Every video is an experiment with an ID, hypothesis, cost and later metrics; separate failure causes (impressions / CTR / early drop-off / expectation mismatch); change few things at a time.
- Never report unfinished work as finished. Measured values and estimates are labelled separately.
- Owner approval is required for: new spending or budget changes, account creation, publish permissions, the first public release. Budget: about 30,000 JPY per month.
- Keep existing assets (code, DB, workflows); do not rebuild without checking them first.
- Secrets are never printed. Code lives on the working branch; tests must pass.
