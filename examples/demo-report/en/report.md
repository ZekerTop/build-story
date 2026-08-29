# BuildStory: PocketTasks

> **From complex automatic cloud sync back to a user-controlled local-first product.**

- 1 explicit direction change
- 2 loop candidates worth reviewing
- Most visible attention: Core code

<details>
<summary>View supporting evidence</summary>

- 12 commits
- 11 files
- 18 calendar days
- 3.4 estimated active hours (confidence: medium)

</details>

## The turns that changed the project

- `2026-07-01` **Project start** · Initialize PocketTasks CLI (`7205f097`)
- `2026-07-03` **Attempt later reversed** · Add experimental cloud sync queue (`a4ffcd52`)
  - **User:** Add automatic cloud sync but keep the task manager simple for beginners
  - **AI:** I added a queue and background push.
- `2026-07-04` **Repeated refinement** · Refactor cloud sync retry ownership (`9de0c2d9`)
  - **User:** Fix the automatic cloud sync queue again and make retries easier to understand
  - **AI:** Retry state now lives with each queue item.
- `2026-07-05` **Direction change** · Revert "Add experimental cloud sync queue" (`d678a8a2`)
  - **User:** The cloud sync is too complex. Remove it and keep all user data local
  - **AI:** I removed the automatic sync path.
- `2026-07-06` **New direction** · Replace cloud sync with local export (`25929cfc`)
  - **User:** Add an explicit JSON export so users control when data leaves the app
  - **AI:** Export is implemented and remains local.
- `2026-07-08` **Validation established** · Add tests for storage and export (`ea9798bf`)
  - **User:** Add tests for the local store and JSON export
  - **AI:** The storage and export paths now have tests.
- `2026-07-18` **Delivery milestone** · Release PocketTasks 1.0 (`5e5bebe5`)

<details>
<summary>View every commit · 12 commits</summary>

- `2026-07-01` **Foundation** · Initialize PocketTasks CLI (`7205f097`)
- `2026-07-02` **Feature** · Add JSON task storage (`9acce59f`)
- `2026-07-03` **Feature** · Add experimental cloud sync queue (`a4ffcd52`)
- `2026-07-03` **Fix** · Fix cloud sync duplicate queue entries (`55eaaed9`)
- `2026-07-04` **Refactor** · Refactor cloud sync retry ownership (`9de0c2d9`)
- `2026-07-05` **Fix** · Revert "Add experimental cloud sync queue" (`d678a8a2`)
- `2026-07-06` **Refactor** · Replace cloud sync with local export (`25929cfc`)
- `2026-07-08` **Validation** · Add tests for storage and export (`ea9798bf`)
- `2026-07-09` **Validation** · Add CI validation workflow (`a3e930e6`)
- `2026-07-12` **Documentation** · Document local-first architecture decision (`684b02c3`)
- `2026-07-15` **Delivery** · Prepare v1 release documentation (`b621c977`)
- `2026-07-18` **Delivery** · Release PocketTasks 1.0 (`5e5bebe5`)

</details>

## Where the project fought back

- `src/sync.py` · 5 commits · +16 / -12 · 86% bidirectional churn

### Loop candidates

- **Revert "Add experimental cloud sync queue"** · 2026-07-05 · d678a8a2 (confidence: high)
- **src/sync.py** · Changed in 5 commits with 86% bidirectional churn. (confidence: medium)

## Attention map

- **Core code** · 34 lines changed · 7 commit touches
- **Project root** · 14 lines changed · 5 commit touches
- **Automation workflows** · 7 lines changed · 1 commit touches
- **Tests** · 4 lines changed · 2 commit touches
- **Documentation** · 3 lines changed · 1 commit touches

## Evidence-backed profile

### Delivery evidence · Strong

- **Why:** README; license; package manifest; 1 Git tag; project documentation
- **Next time:** Keep release tags, change notes, and usage documentation as the definition of done.

<details>
<summary>View calculation · 100/100</summary>

- README
- license
- package manifest
- 1 Git tag
- project documentation

</details>

### Validation discipline · Healthy

- **Why:** test files; CI workflow; 2 validation-related commits
- **Next time:** Add regression tests around the paths that absorbed the most rework before the next release.

<details>
<summary>View calculation · 78/100</summary>

- test files
- CI workflow
- 2 validation-related commits

</details>

### Change traceability · Clear

- **Why:** 100% descriptive commit subjects; 100% reviewable-size commits
- **Next time:** Keep commits small and describe the decision each change preserves or replaces.

<details>
<summary>View calculation · 100/100</summary>

- 100% descriptive commit subjects
- 100% reviewable-size commits

</details>

### Iteration control · Needs review

- **Why:** 1 explicit reversal; 1 high-change file candidate; High churn may represent productive iteration and still requires context
- **Next time:** Before implementing cross-boundary state, write down failure recovery and an exit condition. After two repeated fixes, pause and reconsider the direction.

<details>
<summary>View calculation · 50/100</summary>

- 1 explicit reversal
- 1 high-change file candidate
- High churn may represent productive iteration and still requires context

</details>

### Learning capture · Strong

- **Why:** README; docs directory or architecture guide; changelog; architecture decision records
- **Next time:** Keep the decision record connected to the release or behavior it changed.

<details>
<summary>View calculation · 93/100</summary>

- README
- docs directory or architecture guide
- changelog
- architecture decision records

</details>

## What this project proves

### Sustained delivery

12 commits across 18 calendar days and 11 tracked files.

> Took PocketTasks from early experiments to a 1.0 release; reversed automatic cloud sync when queue and retry complexity grew, replacing it with explicit JSON export.

### Core implementation areas

Most change activity concentrated in: Core code, Project root, Automation workflows.

> Added tests and CI for local storage and export, then captured the direction change in an architecture decision record.

### Validation infrastructure

The repository contains tests and CI.

## Turn evidence into a story

### Portfolio summary

From complex automatic cloud sync back to a user-controlled local-first product. removed automatic cloud sync after queue and retry complexity kept growing, replacing it with user-initiated export. shipped PocketTasks 1.0 with local task storage and explicit JSON export, leaving users in control of when data leaves the device.

### Resume bullets

- Took PocketTasks from early experiments to a 1.0 release; reversed automatic cloud sync when queue and retry complexity grew, replacing it with explicit JSON export.
- Added tests and CI for local storage and export, then captured the direction change in an architecture decision record.

### STAR interview story

- **Situation:** Initialize PocketTasks CLI
- **Task:** product direction, core implementation, and release validation
- **Action:** removed automatic cloud sync after queue and retry complexity kept growing, replacing it with user-initiated export.
- **Result:** shipped PocketTasks 1.0 with local task storage and explicit JSON export, leaving users in control of when data leaves the device.

## Method and limits

- Git records saved changes, not all thinking, experiments, or uncommitted work.
- Transcript analysis stores only short excerpts used to explain repeated-prompt candidates.
