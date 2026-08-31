# BuildStory: PocketTasks

> **From complex automatic cloud sync back to a user-controlled local-first product.**

- 1 confirmed direction change
- 3 communication examples to review
- Most visible attention: Core code

<details>
<summary>View supporting evidence</summary>

- 12 commits
- 11 files
- 18 calendar days
- 5.1 estimated active hours (confidence: medium)

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
  - **User:** I mean add automated tests for local storage and JSON export. Do not add cloud dependencies.
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

## The story behind the rework

> BuildStory groups related changes into a tentative explanation, shows the evidence, and asks you to confirm what Git cannot know.

### Add experimental cloud sync queue · Direction change

- **Current judgment:** User confirmed the current classification: Direction change.
- **Evidence basis:** 5 related commits, 3 fixes or refactors, 1 explicit reversal, and 1 replacement direction.
- **Attempted path:**
  - `2026-07-03` Add experimental cloud sync queue (`a4ffcd52`)
  - `2026-07-03` Fix cloud sync duplicate queue entries (`55eaaed9`)
  - `2026-07-04` Refactor cloud sync retry ownership (`9de0c2d9`)
  - `2026-07-05` Revert "Add experimental cloud sync queue" (`d678a8a2`)
  - `2026-07-06` Replace cloud sync with local export (`25929cfc`)
- **Your confirmation:** The queue and retry complexity of automatic sync conflicted with a beginner-friendly product.
- **Lesson captured:** When a feature keeps adding recovery machinery, reconsider whether the feature deserves to exist.

<details>
<summary>View file-level evidence</summary>

### Where the project fought back

- `src/sync.py` · 5 commits · +16 / -12 · 86% bidirectional churn

### Loop candidates

- **Revert "Add experimental cloud sync queue"** · 2026-07-05 · d678a8a2 (confidence: high)
- **src/sync.py** · Changed in 5 commits with 86% bidirectional churn. (confidence: medium)

</details>

## Communication review

> See which details became clear only after AI had already acted. This reviews how the human and AI aligned; it never scores the user's communication ability.

### Term meaning clarified later · The same term meant different things

- **What you said:** Make storage better for beginners
- **What you clarified later:** I mean local JSON storage, not a hosted service. Keep all task data on the device.
- **Where the gap appeared:** Both sides kept using the same term, but the term referred to different things.
- **Observed project evidence:** 1 topic-overlapping commit(s) appeared within 24 hours of the clarification; timing alone does not prove causation.
- **Information that was missing:** the exact meaning of the core term, the interpretation to exclude
- **A clearer way to say it next time:** Please follow this complete requirement: local JSON storage, not a hosted service. Keep all task data on the device. Before changing anything, restate the goal, scope, and what must remain unchanged.
- **Reusable pattern:** By [term], I mean [exact meaning], not [likely interpretation]; the expected result is [outcome].
- **Needs your confirmation:** Was this mainly a case of both sides assigning different meanings to the same term?

<details>
<summary>Evidence</summary>

- **How AI responded:** I connected the task list to a hosted database.
- `2026-07-02` Add JSON task storage (`9acce59f`)

</details>

### Constraint clarified later · Information became clear later

- **What you said:** Make sure the local data flow works
- **What you clarified later:** I mean add automated tests for local storage and JSON export. Do not add cloud dependencies.
- **Where the gap appeared:** The initial wording allowed multiple reasonable interpretations. The later clarification made the object, scope, or constraint unique.
- **Observed project evidence:** 1 topic-overlapping commit(s) appeared within 24 hours of the clarification; timing alone does not prove causation.
- **Information that was missing:** behavior that must remain, explicit non-goals
- **A clearer way to say it next time:** Please follow this complete requirement: add automated tests for local storage and JSON export. Do not add cloud dependencies. Before changing anything, restate the goal, scope, and what must remain unchanged.
- **Reusable pattern:** Complete [goal], but do not change [boundary]; preserve [existing behavior].
- **Needs your confirmation:** Was this information missing at the start, or did the more specific judgment form only after you saw the result?

<details>
<summary>Evidence</summary>

- **How AI responded:** I ran the CLI once and the command completed.
- `2026-07-08` Add tests for storage and export (`ea9798bf`)

</details>

### Ambiguous reference · Information became clear later

- **What you said:** Document it
- **What you clarified later:** I mean document why we chose local-first export instead of hidden cloud sync, not only how to use the CLI.
- **Where the gap appeared:** The initial wording allowed multiple reasonable interpretations. The later clarification made the object, scope, or constraint unique.
- **Observed project evidence:** 1 topic-overlapping commit(s) appeared within 24 hours of the clarification; timing alone does not prove causation.
- **Information that was missing:** the exact object, the change boundary
- **A clearer way to say it next time:** Please follow this complete requirement: document why we chose local-first export instead of hidden cloud sync, not only how to use the CLI. Before changing anything, restate the goal, scope, and what must remain unchanged.
- **Reusable pattern:** Change [specific part] of [specific object] to achieve [expected result]; do not change [boundary].
- **Needs your confirmation:** Was this information missing at the start, or did the more specific judgment form only after you saw the result?

<details>
<summary>Evidence</summary>

- **How AI responded:** I added another usage example.
- `2026-07-12` Document local-first architecture decision (`684b02c3`)

</details>


## Project rhythm

> A project-scoped activity pulse. It shows when observable work happened, not how hard someone worked.

- **Project span:** 18 calendar days
- **Active development days:** 11 days
- **Longest continuous run:** 6 days

### Most active day · 2026-07-03

2 commits · 4 conversation events · 7 lines changed

Add experimental cloud sync queue; Fix cloud sync duplicate queue entries

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
- Transcript analysis keeps only short excerpts needed for review; it never copies the full conversation.
