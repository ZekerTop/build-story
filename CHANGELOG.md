# Changelog

## Unreleased

## 0.4.0 - 2026-08-31

- Added communication review from ordered `user → assistant → user correction` evidence chains, capped at three cards.
- Added neutral attribution for information clarified later, AI misses of explicit requirements, term-meaning mismatches, requirement evolution, and insufficient evidence.
- Added evidence-gated request rewrites, reusable communication patterns, and local `communication_confirmations` without prompt scoring or judgments of user ability.
- Clarified that repeated prompts do not prove unclear wording and that nearby Git commits do not prove causation.
- Kept communication analysis local and limited reports to short supporting excerpts rather than complete transcripts.
- Added conservative parsing for common nested `message` / `payload` exports, isolated ambiguous runs in multi-session files, and made communication confirmation IDs independent of absolute transcript paths.
- Updated structured evidence to schema `1.5` and aligned documentation with generator version `0.4.0`.
- Added an EN / 中文 switch to visual reports.
- Every analysis now generates default, English, and Chinese JSON, Markdown, and HTML outputs.
- Made Chinese the default report language and the repository's primary README language.
- Replaced the commit-dump opening with a one-sentence story and at most seven turning points.
- Added optional `--context` input for confirmed role, outcome, key decision, summary, and resume bullets.
- Added portfolio, resume, and STAR material generated from confirmed context.
- Replaced prominent numeric dimension scores with evidence levels, reasons, and next-run recommendations.
- Completed visible Chinese localization for counts, evidence, attention areas, and report controls.
- Added exact dynamic-text translations so Chinese reports can localize commit subjects and conversation excerpts.
- Added short user-request and AI-response excerpts to evidence-backed turning points.
- Added a project-scoped activity pulse with calendar span, active development days, longest continuous run, and an interactive day story.
- Added a most-active-day explanation without treating commit volume as diligence or productivity.
- Added theme-level journey insights that classify repeated work as a blocked loop, necessary exploration, or direction change.
- Added evidence chains, confirmation questions, and local `insight_confirmations` for capturing the user's reason and lesson.
- Moved file paths, churn ratios, and loop candidates into supporting evidence instead of presenting them as the main conclusion.

## 0.1.0 - 2026-08-29

- Added the BuildStory Agent Skill.
- Added local Git and optional transcript evidence extraction.
- Added explicit reversal, repeated-topic, repeated-prompt, and high-churn loop candidates.
- Added transparent dimension scores without an overall score.
- Added self-contained JSON, Markdown, and HTML reports.
- Added deterministic English and Chinese demo reports.
- Added English and Chinese documentation, tests, and CI.
