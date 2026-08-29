---
name: build-story
description: Reconstruct and review how a software project was built. Use when someone wants a project retrospective, development timeline, rework and rollback analysis, time-sink analysis, evidence-backed process scoring, lessons learned, portfolio case study, achievement summary, resume bullets, or interview stories from a Git repository and optional AI coding-session transcripts.
---

# BuildStory

BuildStory helps a person see **how** a project was built, not only what was shipped. It reconstructs a project timeline, surfaces repeated rework and likely time sinks, builds an evidence-backed capability profile, and turns the evidence into lessons and career material.

## Non-negotiable principles

- Treat Git and session logs as evidence, not mind-reading. Label inferences and confidence.
- Never collapse the project into one total score. Show a jagged profile across dimensions.
- Do not equate iteration with waste. Call suspicious patterns "loop candidates" until the evidence or user confirms them.
- Do not invent business impact, ownership, team size, performance gains, or resume metrics.
- Read only the current project by default. Ask before reading session files outside the authorized workspace.
- Keep analysis local unless the user explicitly requests an external service.
- Do not modify project source files. Write results to a dedicated output directory.

## Default workflow

### 1. Establish scope

Identify the repository root and the user's goal. Default to the current branch and the full Git history reachable from `HEAD`.

Use session transcripts only when they are already provided or the user authorizes their paths. Git-only reports are useful but must mark time estimates and intent-level conclusions as lower confidence.

### 2. Collect deterministic evidence

Run the bundled analyzer:

```bash
python3 <skill-dir>/scripts/build_story.py <repo-path> \
  --output <repo-path>/build-story-report \
  --language <zh|en>
```

Add one or more transcript sources when authorized:

```bash
python3 <skill-dir>/scripts/build_story.py <repo-path> \
  --session <authorized-session-file-or-directory> \
  --output <repo-path>/build-story-report \
  --language <zh|en>
```

The script generates a default report plus English and Chinese variants:

- `evidence.json`: machine-readable evidence and transparent metrics
- `report.md`: portable text report
- `report.html`: self-contained visual report with an EN / 中文 switch
- `evidence.en.json`, `report.en.md`, `report.en.html`: English outputs
- `evidence.zh.json`, `report.zh.md`, `report.zh.html`: Chinese outputs

### 3. Inspect the evidence before narrating

Read `evidence.json` and verify:

- data sources and stated limitations;
- project dates, commit counts, authors, and file counts;
- explicit reverts versus inferred high-churn loops;
- whether time estimates came from Git or timestamped sessions;
- the evidence and confidence behind every dimension score.

If the data contradicts the user's description, show the discrepancy and ask rather than silently choosing one version.

### 4. Ask only for missing human context

Do not turn the workflow into an interview. Ask at most the smallest set needed for the requested deliverable, usually:

1. What outcome did the project create?
2. What was the user's personal responsibility?
3. Which difficult decision or trade-off mattered most?

Skip questions whose answers are already documented in the repository.

### 5. Produce the requested story

Use the evidence for one or more of these outputs:

- **Project retrospective:** timeline, turning points, friction, lessons, next-run changes.
- **Portfolio case study:** problem, constraints, decisions, implementation, validation, outcome.
- **Resume bullets:** action + scope + method + verified result. Leave an explicit placeholder when impact is unknown.
- **Interview story:** STAR structure grounded in commits, diffs, tests, releases, and user-confirmed context.
- **Achievement record:** durable evidence cards that explain what the user actually did.

Read [references/narrative-guide.md](references/narrative-guide.md) when producing career or portfolio writing. Read [references/methodology.md](references/methodology.md) when explaining scores, time estimates, or loop detection.

## Output quality bar

A finished BuildStory report should let the user answer:

1. What phases did this project pass through?
2. Where did work repeatedly loop or reverse?
3. Which areas absorbed the most attention, and how confident is that estimate?
4. What did the user demonstrably learn or improve?
5. What credible achievement can be reused in a resume, portfolio, interview, or personal record?

If the available evidence cannot answer one of these, state what is missing. A smaller honest story is better than an impressive fictional one.
