# BuildStory design

Date: 2026-08-29

## Product promise

BuildStory reconstructs how a software project was actually built and turns that evidence into a useful retrospective, a jagged capability profile, lessons, and career proof.

Public brand: `BuildStory`  
Skill and repository name: `build-story`

Primary line:

> See how you built it, not just what you built.

## Audience

The first release serves individual developers, AI-assisted builders, students, and newcomers who finished a Git project but do not know how to review or explain their work.

The experience must work with one command and no external account. Advanced transcript analysis is optional.

## Scope

### Included

- Git timeline reconstruction;
- phase and turning-point classification;
- explicit revert and high-churn loop candidates;
- Git-based time estimate with visible confidence;
- optional local transcript analysis;
- evidence-backed dimension scores with no overall score;
- self-contained JSON, Markdown, and HTML reports;
- English and Chinese report variants with a visible language switch;
- guidance for retrospectives, portfolio cases, achievements, resume bullets, and STAR stories;
- English and Chinese documentation.

### Excluded from v0.1

- cloud accounts and hosted dashboards;
- team surveillance or employee ranking;
- IDE background agents;
- automatic public sharing;
- claims about productivity or human ability without evidence;
- provider-specific transcript discovery outside authorized paths.

## Architecture

The Skill has two layers:

1. **Deterministic evidence layer:** a standard-library Python script reads Git and optional local transcripts, then produces structured evidence and reports.
2. **Agent narrative layer:** `SKILL.md` instructs the agent to inspect confidence, ask only for missing human context, and create truthful retrospective and career narratives.

The deterministic layer never needs network access and never modifies source files.

## Data flow

```text
Git repository + optional authorized transcripts
                    |
                    v
          deterministic extraction
                    |
                    v
      evidence.json + report.md + report.html
                    |
                    v
        agent reviews confidence and gaps
                    |
                    v
 retrospective / portfolio / resume / STAR story
```

## Report structure

1. Project identity and data coverage
2. Project life line
3. Friction zones and loop candidates
4. Attention and time-sink estimates
5. Jagged capability profile
6. Evidence cards and career-story prompts
7. Methodology and confidence

Design read: a developer-facing, evidence-first report for non-experts, using an editorial technical language, monochrome surfaces, one orange accent, restrained motion, and print-friendly layout.

## Safety and truthfulness

- Session paths require user authorization.
- Full conversations are not reproduced by default.
- Low-confidence inferences are visibly labeled.
- Resume output cannot invent impact.
- Generated files go only into the chosen output directory.
- The script does not alter the analyzed repository.

## Validation

- Skill frontmatter and layout pass the bundled Skill validator.
- Unit tests create a temporary Git history containing features, fixes, tests, churn, and an explicit revert.
- Tests verify the three output formats, source metrics, loop candidates, and dimension-score evidence.
- The demo report is rendered and visually inspected at desktop and mobile widths.

## Self-review

- No placeholders remain in the design.
- v0.1 has one clear path and no hosted platform scope.
- Scores are evidence summaries, not personal judgments.
- Git-only time analysis explicitly states its limitations.
- The architecture matches the privacy and local-first promise.
