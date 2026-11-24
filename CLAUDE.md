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

## Directive of 2026-11-24 (integrated execution order; supersedes nothing above)
- Goal: a multi-AI system that runs the business 24/7 with minimal human intervention and produces lasting profit (first target 1,000,000 JPY/month; build deadline 2026-12-20; budget about 30,000 JPY/month). Not limited to YouTube: any monetisation channel (SNS, web, EC, ads, digital products, AI services). Revenue and net profit are tracked separately. Work that does not contribute to profit is stopped.
- Learn from others' trial and error: study success AND failure cases over time (start point, turning points, strategy changes, acquisition, revenue structure), extract reusable principles, never copy surface content. Observed facts and AI interpretation are always separated; correlation is not causation; look for counter-examples.
- Use the best AI/tool per job (compare by official spec, measured quality, cost, speed, compatibility); prefer existing services/public code over new development. Do not rebuild existing assets; back up before changing. Status vocabulary for every capability: 未実装 / 実装済み / 模擬テスト済み / 実動作確認済み / 実運用確認済み / 市場成果確認済み. Never report completion percentages from code volume, commits or test counts.
- Real video understanding is the core capability (video + audio, not titles/subtitles). A video is "analysed" only if the API reports VIDEO (and AUDIO) input tokens; the analysis capability itself must be verified against ground truth (own videos, injected defects, FFmpeg/transcript cross-checks) before any large-scale use. Technical verification budget cap: 1,000 JPY.
- Producer and evaluator are separate; AI-to-AI agreement is internal evaluation, not market proof. Evaluation AIs are themselves tested (seeded defects, hidden-outcome comparison against real results).
- Learned knowledge lives in SQLite (knowledge id, content, evidence, source URL, timestamp, date, audience, market, conditions, success/failure factors, counter-evidence, confidence, verification status, applications, history), is searched automatically for planning/production, and is promoted/demoted by measured market results.
- Autonomy: act within existing permissions and budget without waiting for instructions; when blocked, find alternatives. Owner approval is still required for: external publishing, new contracts, budget increases, starting payments, outreach, important account changes, secrets, destructive changes.
- Scraping must respect terms; no circumvention of access limits; unavailable data is reported as unavailable.
