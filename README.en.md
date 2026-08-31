# BuildStory

**See how you built it, not just what you built.**

BuildStory is a local-first Agent Skill and report generator that reconstructs how a software project was built. It turns Git history and explicitly authorized AI coding-session transcripts into a project story, turning points, rework and rollback signals, and evidence-backed career material. With authorized transcripts, it can also review which details became clear only after AI had acted and, when the evidence supports it, produce copy-ready rewrites for the next conversation.

[简体中文](README.md)

![BuildStory report preview](examples/demo-report/preview.png)

> Turn Git history and authorized AI sessions into a verifiable decision timeline.

## A 60-second run

```bash
git clone https://github.com/ZekerTop/build-story.git
cd build-story
python3 scripts/build_story.py /path/to/your/project --output ./build-story-report
open ./build-story-report/report.html
```

No API key, account, or upload is required. Start with the Chinese HTML report, then add authorized session files when you need conversation-level context.

## Why BuildStory

The finished repository shows what survived. It usually hides:

- the feature that was rebuilt three times;
- the component that absorbed most of the project's attention;
- the decision that simplified the entire system;
- the experiments that were discarded;
- the real evidence behind a resume claim.

BuildStory makes that invisible process inspectable without pretending Git can read a developer's mind.

## What it produces

One run creates a default report plus English and Chinese variants. The `--language` option chooses which language opens as `report.html`:

```text
build-story-report/
├── evidence.json       # evidence in the selected default language
├── evidence.en.json    # English evidence
├── evidence.zh.json    # Chinese evidence
├── report.md           # Markdown in the selected default language
├── report.en.md        # English Markdown
├── report.zh.md        # Chinese Markdown
├── report.html         # default report with EN / 中文 switch
├── report.en.html      # English visual report
└── report.zh.html      # Chinese visual report
```

The report includes:

1. a story-first opening that explains what changed;
2. five to seven turning points that changed direction, risk, understanding, or delivery state;
3. theme-level interpretations of repeated work as a blocked loop, necessary exploration, or direction change;
4. an attempted path, evidence basis, and one confirmation question for each interpretation;
5. project span, active development days, longest continuous run, and the most active day;
6. a project-scoped activity pulse that reveals what happened on a selected day;
7. estimated attention areas and active time;
8. evidence levels and actions for delivery, validation, traceability, iteration, and learning capture;
9. a communication review based on a `user → assistant → user correction` evidence chain, capped at three cards;
10. evidence cards for portfolios, resume bullets, achievement records, and STAR interview stories.

The activity pulse describes observable Git and conversation evidence. It does not turn commit volume into a judgment of effort or productivity.

The complete commit log and numeric calculations remain available as collapsed evidence. BuildStory deliberately does **not** calculate an overall project or prompt score, and it does not judge the user's communication ability.

The current generator version is **0.4.0** and the structured evidence schema is **1.5**.

## Quick start

Requirements:

- Python 3.10+
- Git
- a repository with at least one commit

Generate both languages and open English by default:

```bash
python3 scripts/build_story.py /path/to/project \
  --output /path/to/project/build-story-report \
  --language en
```

Generate both languages and open Chinese by default:

```bash
python3 scripts/build_story.py /path/to/project \
  --output /path/to/project/build-story-report \
  --language zh
```

Open `build-story-report/report.html` in a browser and use the **EN / 中文** switch in the top navigation. The language-specific files can also be opened or shared directly.

When `--language` is omitted, BuildStory opens Chinese by default.

### Add authorized AI-session evidence

BuildStory can read local `.jsonl`, `.json`, `.txt`, and `.md` transcripts when you explicitly provide their paths:

```bash
python3 scripts/build_story.py /path/to/project \
  --session /path/to/authorized/session.jsonl \
  --output /path/to/project/build-story-report \
  --language en
```

Repeat `--session` to add more authorized files or directories.

BuildStory does not automatically search private session directories.

The parser accepts generic `.jsonl`, `.json`, `.txt`, and `.md` inputs and conservatively recognizes common nested `message`, `payload`, and conversation-archive structures. When one file contains multiple sessions, message runs that cannot be assigned safely are isolated rather than joined across sessions. Agent-specific field names may still differ; when timestamps or roles cannot be identified, BuildStory keeps the Git report and lowers confidence instead of inventing context.

Large Codex `.jsonl` sessions are no longer discarded by the general file-size limit. JSONL input is accepted up to 128 MB and remains protected by the global event cap; non-streaming `.json`, `.txt`, and `.md` inputs keep the stricter 20 MB limit.

Communication cards require a same-session `user → assistant → user correction` chain and are capped at three distinct cases. The analyzer can recover the real requirement before a short approval such as “go ahead,” and it separates a later “another bug” from the current correction chain instead of merging unrelated requests. A repeated prompt is not automatically unclear wording. BuildStory distinguishes an AI miss of an explicit requirement, a term-meaning mismatch, and requirement evolution after seeing a result instead of assigning blame to the user by default. Candidates that still have insufficient evidence are omitted by default, and users can also confirm an existing candidate as insufficient evidence. BuildStory offers a rewrite only when the evidence supports user-side guidance, and the rewrite must reorganize the target, scope, protected boundary, and verification rather than wrapping the user's later words in boilerplate.

Temporal proximity between a clarification and a Git commit is only an inspectable clue; **it does not prove causation**. Reports keep only the short excerpts needed to support a conclusion. They do not upload or copy complete conversations.

As an Agent Skill, you can ask:

```text
Use $build-story to review this project and the authorized sessions. Show at most three cases where important information became clear only after AI had acted, and provide a copy-ready version only when the evidence supports one. Do not score my prompts.
```

### Confirm the journey, then add three career facts

Git can show what changed, but it cannot prove your responsibility, the final outcome, or why a decision mattered. For resume, portfolio, or STAR output, confirm only:

1. What was your real responsibility?
2. What outcome did the project create for users or for you?
3. Which decision best demonstrates your ability?

Create `context.json`:

```json
{
  "en": {
    "role": "product direction, core implementation, and release validation",
    "outcome": "shipped 1.0 with user-controlled data export",
    "key_decision": "removed increasingly complex automatic sync in favor of explicit export",
    "summary": "From complex automatic sync back to a user-controlled local-first product.",
    "resume_bullets": [
      "Reversed automatic sync after queue and retry complexity grew, replacing it with explicit export."
    ],
    "insight_confirmations": {
      "path:src/sync.py": {
        "classification": "direction-change",
        "reason": "Automatic sync conflicted with a beginner-friendly product.",
        "lesson": "When a feature keeps adding recovery machinery, reconsider whether it deserves to exist."
      }
    },
    "communication_confirmations": {
      "communication:example-id": {
        "attribution": "ai-ignored-explicit-requirement",
        "reason": "The original request already said to preserve the language switch, so this was an AI execution miss.",
        "analysis": "The user did not need a longer prompt. The AI should restate the protected boundary before editing.",
        "lesson": "When a clear boundary is still missed, inspect AI execution before blaming user wording."
      }
    }
  }
}
```

Regenerate the report:

```bash
python3 scripts/build_story.py /path/to/project \
  --context /path/to/project/context.json \
  --output /path/to/project/build-story-report \
  --language en
```

BuildStory then creates a portfolio summary, resume bullets, and a STAR story without treating commit volume as impact.

If Git subjects or AI conversations use another language, add exact source-to-display mappings under `translations`. The localized report shows the translated development story while retaining the original text in structured evidence. When authorized transcripts exist, turning points can also show the corresponding user request and AI response excerpts.

## Install as an Agent Skill

### Codex

```bash
git clone https://github.com/ZekerTop/build-story.git \
  "${CODEX_HOME:-$HOME/.codex}/skills/build-story"
```

Then invoke:

```text
$build-story Review this project and show where I repeatedly reworked decisions.
```

### Other Agent Skills-compatible clients

Clone or copy the `build-story` folder into the client's user-level or project-level skills directory. Keep `SKILL.md`, `scripts/`, `references/`, and `agents/` together.

Example prompts:

```text
Use $build-story to create a project retrospective from this repository.
```

```text
Use $build-story to identify repeated loops, likely time sinks, and the most defensible achievements from this project.
```

```text
Use $build-story to turn this project's evidence into a portfolio case study and three truthful resume bullets. Ask me only for impact that cannot be verified from the repository.
```

```text
Use $build-story to review correction chains in the authorized sessions. Distinguish AI misses, term-meaning mismatches, requirement evolution, and insufficient evidence. Show at most three cases, and provide a copy-ready rewrite only when the evidence supports one.
```

## Evidence model

BuildStory keeps three things separate:

| Type | Meaning | Example |
|---|---|---|
| Observation | Directly present in data | An explicit `Revert` commit |
| Inference | A repeatable signal that needs interpretation | A file with high bidirectional churn |
| Confirmed context | Supplied by the user | Why a design was abandoned |

Every theme-level journey interpretation and time estimate includes a confidence level. Until the user confirms it, the interpretation remains an evidence-backed hypothesis rather than a career claim.

### Loop detection

The analyzer uses:

- explicit `revert`, `rollback`, and equivalent commit messages;
- repeated normalized commit topics;
- files changed repeatedly with substantial additions and deletions;
- repeated prompts in authorized session transcripts.

High churn can mean productive iteration. BuildStory combines reversal, replacement, repeated-fix, and validation signals to propose one of three interpretations: blocked loop, necessary exploration, or direction change. File paths, change counts, and churn ratios remain collapsed evidence rather than verdicts of failure or waste.

### Time estimates

Git does not record thinking time. A Git-only estimate groups nearby commits into work sessions and is labeled low confidence.

Authorized timestamped transcripts improve coverage, but still miss offline thinking, meetings, research, and unrecorded experiments.

### Communication review

Communication review only examines transcripts the user explicitly authorizes. It requires a same-session `user → assistant → user correction` chain and keeps at most three distinct examples. Short approvals are resolved back to the preceding requirement, while unrelated follow-up bugs are split out before analysis.

Repeated prompts do not automatically mean unclear wording. An interpretation may be that information became clear later, AI ignored an explicit requirement, both sides used a term differently, the requirement evolved after seeing the result, or evidence is insufficient to attribute. These labels review human-AI alignment; they do not evaluate the user's communication ability.

## Evidence-backed profile

BuildStory reports separate dimensions:

- **Delivery evidence:** release, packaging, documentation, and completion signals.
- **Validation discipline:** tests, CI, linting, and validation-related changes.
- **Change traceability:** descriptive commit messages and reviewable commit size.
- **Iteration control:** reversals and concentrated rework signals.
- **Learning capture:** README, changelog, ADRs, documentation, and retrospectives.

The report shows human-readable levels such as Strong, Clear, Needs review, and Limited evidence, then gives a reason and a concrete next action. Raw numbers appear only under “View calculation.”

These levels describe repository evidence. They do not measure a person's intelligence, seniority, or worth.

## Demo

The repository includes deterministic reports for a synthetic project called PocketTasks:

- [English HTML report](examples/demo-report/en/report.html)
- [English Markdown report](examples/demo-report/en/report.md)
- [Chinese HTML report](examples/demo-report/zh/report.html)
- [Chinese Markdown report](examples/demo-report/zh/report.md)

Regenerate them with:

```bash
python3 scripts/create_demo_report.py
```

## Privacy and safety

- Analysis runs locally.
- The generator makes no network requests.
- Source files are never modified.
- Output is written only to the selected directory.
- Absolute local paths are not included in generated reports.
- Full transcripts are not copied into reports.
- Communication review retains only short excerpts needed to support a conclusion and never uploads transcripts.
- Injected environment or AGENTS instruction events are excluded, and local home or temporary paths are redacted.
- Resume and portfolio output must not invent impact metrics.

See [SECURITY.md](SECURITY.md) for responsible reporting.

## Limitations

- Git-only analysis cannot see uncommitted experiments or invisible thinking.
- Commit-message classification is heuristic.
- High churn is not automatically waste.
- Transcript formats vary across tools; v0.4.0 still uses a conservative generic parser.
- A communication correction chain shows how alignment changed; it cannot by itself prove whether responsibility belongs to the user or AI.
- Temporal proximity between a conversation and a Git commit does not prove causation.
- Career outcomes require the user's verified role and result.

## Development

Run tests:

```bash
python3 -m unittest discover -s tests -v
```

Validate the Skill structure:

```bash
python3 /path/to/skill-creator/scripts/quick_validate.py .
```

The example reports and tests cover Git-only input, authorized sessions, localized dynamic text, activity-pulse interaction, malformed JSON input, and mobile layout.

## Project structure

```text
build-story/
├── SKILL.md
├── agents/openai.yaml
├── scripts/
│   ├── build_story.py
│   └── create_demo_report.py
├── references/
│   ├── methodology.md
│   └── narrative-guide.md
├── examples/demo-report/
├── tests/
└── docs/superpowers/specs/
```

## Roadmap

- richer Codex, Claude Code, Cursor, and OpenCode transcript adapters;
- phase-level comparison between planned and actual work;
- project-to-project comparison without employee ranking;
- export templates for portfolio pages and promotion packets.

## Contributing

Issues and focused pull requests are welcome. Please read [CONTRIBUTING.md](CONTRIBUTING.md).

## License

[MIT](LICENSE)
