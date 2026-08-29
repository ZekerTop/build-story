# BuildStory methodology

BuildStory separates **observations**, **inferences**, and **user-confirmed facts**.

## Evidence levels

| Level | Meaning | Examples |
|---|---|---|
| High | Directly present in source data | Explicit `Revert` commit, test file, release tag |
| Medium | Repeatable signal with more than one supporting observation | A file changed in many commits with high add/delete churn |
| Low | Useful hypothesis that needs human confirmation | Time spent inferred only from gaps between commits |

Never present low-confidence evidence as a fact.

## Timeline

The deterministic analyzer reads commits reachable from the current `HEAD`, in chronological order. Each commit receives a working category based on its message and changed paths:

- foundation;
- feature;
- fix;
- refactor;
- validation;
- documentation;
- delivery;
- other.

These labels help navigation. They are not claims about the author's intent.

The default report selects at most seven turning points. The first and final commits anchor the story; explicit reversals, the attempts they undo, new directions, validation, documentation, and delivery milestones receive priority. The complete timeline stays available in a collapsed evidence section.

## Rework and loop candidates

BuildStory uses three signals:

1. **Explicit reversals:** commit subjects containing `revert`, `rollback`, `back out`, or equivalent Chinese terms. High confidence.
2. **Repeated topics:** similar normalized commit subjects recurring during the project. Medium confidence when repeated three or more times.
3. **High-churn files:** files repeatedly receiving both additions and deletions. Medium confidence when the file has enough commits and change volume.

High churn may mean central, valuable iteration rather than waste. The narrative must explain the evidence and ask the user when the distinction matters.

## Time estimates

Git does not record thinking time. A Git-only estimate groups commits into sessions separated by more than two hours and treats short gaps as active time. It is a lower-bound approximation with low confidence.

When timestamped AI-session transcripts are supplied, BuildStory estimates activity from transcript event intervals capped at 30 minutes. This improves coverage but still does not capture offline thinking.

Always show the source used, estimated active hours, confidence, and the limitation that invisible work is missing.

## Capability profile

There is no overall score. The analyzer reports separate dimensions:

- **Delivery evidence:** release, packaging, documentation, and completion signals.
- **Validation discipline:** tests, CI configuration, and validation-related changes.
- **Change traceability:** meaningful commit messages and reviewable commit size.
- **Iteration control:** explicit reversals and concentrated rework signals.
- **Learning capture:** README, changelog, ADR, docs, or retrospective artifacts.

The report converts each score into a human-readable evidence level, explains the reason, and provides a concrete next-run recommendation. The raw score remains available only inside the calculation details.

Scores summarize observable repository evidence, not a person's intrinsic ability. Each score includes evidence and confidence, and there is no overall score.

## User-confirmed context

Git and transcripts cannot prove personal responsibility, final impact, or the meaning of a trade-off. Career output therefore requires three confirmed facts:

1. the user's real responsibility;
2. the final outcome;
3. the decision that best demonstrates the user's ability.

Optional `summary` and `resume_bullets` fields let the user preserve exact wording. Context may contain separate `zh` and `en` objects and is included only in the locally generated report.

## Privacy

Transcript parsing is local. The analyzer stores only short excerpts needed to explain repeated-prompt candidates. It does not intentionally copy complete conversations into the report.
