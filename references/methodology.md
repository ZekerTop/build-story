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

When authorized transcripts contain timestamped user and assistant messages, BuildStory attaches the nearest short request/response pair to a turning point when it falls within the same working window. It stores only short excerpts and does not reproduce the complete conversation.

Localized reports may use exact source-to-display translations supplied in context. The translated subject or excerpt is shown to the reader while `original_subject` and the source transcript remain the underlying evidence.

## Rework signals and journey insights

BuildStory uses three signals:

1. **Explicit reversals:** commit subjects containing `revert`, `rollback`, `back out`, or equivalent Chinese terms. High confidence.
2. **Repeated topics:** similar normalized commit subjects recurring during the project. Medium confidence when repeated three or more times.
3. **High-churn files:** files repeatedly receiving both additions and deletions. Medium confidence when the file has enough commits and change volume.

High churn may mean central, valuable iteration rather than waste. The narrative must explain the evidence and ask the user when the distinction matters.

For each high-change path that meets the evidence threshold, BuildStory groups the commits touching that path into one tentative journey insight:

- **Direction change:** an explicit reversal or a replacement/switch/removal signal is present.
- **Blocked loop:** fixes or refactors repeat without a visible direction change or validation closure.
- **Necessary exploration:** repeated change exists, but the evidence does not show a repair-dominated loop; validation raises confidence that the exploration reached closure.

These are deterministic hypotheses, not intent detection. Each insight must include the related commit chain, a plain-language judgment, an evidence summary, confidence, and one confirmation question. A user confirmation may override the classification and add the reason and lesson through `insight_confirmations` in local context.

## Project rhythm

Project span runs from the first reachable commit date through the last, inclusive. An active development day contains at least one commit or timestamped event from an authorized transcript within that span.

The longest continuous run counts consecutive active dates. The most active day is selected by observable event count, then commit count and changed lines as tie-breakers. Calendar intensity is normalized only within the current project.

These values describe when recorded activity happened. They must not be labeled as diligence, productivity, effort, or personal performance. The day story should explain the commits or user requests behind the density.

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

`insight_confirmations` records the user's interpretation of a journey insight. The key is the stable insight id, such as `path:src/sync.py`; the value may contain `classification`, `reason`, `lesson`, and an optional human-readable `topic`. Agents should write this field after a confirmation conversation rather than asking users to edit it manually.

## Privacy

Transcript parsing is local. The analyzer stores only short excerpts needed to explain repeated-prompt candidates. It does not intentionally copy complete conversations into the report.
