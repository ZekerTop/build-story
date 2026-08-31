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

## Communication review

Communication review uses only transcripts the user explicitly authorizes. A candidate requires an ordered, same-session evidence chain:

1. a user request;
2. an assistant response that acts on or interprets the request;
3. a later user correction or clarification.

A repeated prompt by itself is not evidence of unclear wording. A short prompt is not automatically a weak prompt. BuildStory shows at most three communication cards and does not calculate a prompt-quality score or evaluate the user's communication ability.

Each card keeps the original request, assistant response, later clarification, neutral analysis, confidence, and one confirmation question. Short approvals may inherit the preceding concrete requirement; unrelated requests introduced with markers such as “另外” or “another issue” are excluded from the current card. Missing-information guidance, a copy-ready rewrite, and a reusable pattern appear only when the attribution supports user-side guidance. A copy-ready rewrite must synthesize a concrete target, scope, protected boundary, and verification step; simply prefixing or suffixing the user's later clarification does not qualify. The attribution must remain one of these distinct interpretations:

- **Information became clear later (`user-expression-insufficient`):** the later message added material scope, constraints, or acceptance criteria that were not explicit before. The label describes the interaction, not the user's ability.
- **AI missed an explicit requirement (`ai-ignored-explicit-requirement`):** the original request already contained the boundary and the assistant failed to preserve it.
- **Term meaning mismatch (`term-meaning-mismatch`):** both sides used the same word for different objects or outcomes.
- **Requirement evolution (`requirement-evolution`):** the user formed a new preference after seeing a result; this is not retroactive evidence that the first request was defective.
- **Insufficient evidence (`insufficient-evidence`):** the visible chain cannot support a fair attribution.

Candidates that remain `insufficient-evidence` after deterministic analysis are omitted by default rather than turned into speculative cards. A user may also downgrade an existing candidate to `insufficient-evidence` through confirmation.

When a Git commit occurs near a clarification, the report may show it as nearby project evidence. Temporal proximity does not establish that the clarification caused the commit. The narrative must say so explicitly.

`communication_confirmations` lets the user confirm or override a card without changing the source evidence. A confirmation entry uses the stable `communication:<digest>` id, which excludes the absolute transcript path so moving the same transcript does not invalidate the confirmation. It may contain `attribution`, `reason`, `analysis`, `improved_request`, `lesson`, and `topic`.

```json
{
  "communication_confirmations": {
    "communication:example-id": {
      "attribution": "term-meaning-mismatch",
      "reason": "We used 'history' to mean different things.",
      "improved_request": "By history, I mean the user and AI conversation timeline, not the Git commit log.",
      "lesson": "Define overloaded terms before asking for a cross-source analysis."
    }
  }
}
```

## Project rhythm

Project span runs from the first reachable commit date through the last, inclusive. An active development day contains at least one commit or timestamped event from an authorized transcript within that span.

The longest continuous run counts consecutive active dates. The most active day is selected by observable event count, then commit count and changed lines as tie-breakers. Calendar intensity is normalized only within the current project.

These values describe when recorded activity happened. They must not be labeled as diligence, productivity, effort, or personal performance. The day story should explain the commits or user requests behind the density.

## Time estimates

Git does not record thinking time. A Git-only estimate groups commits into sessions separated by more than two hours and treats short gaps as active time. It is a lower-bound approximation with low confidence.

When timestamped AI-session transcripts are supplied, BuildStory estimates activity from transcript event intervals capped at 30 minutes. This improves coverage but still does not capture offline thinking.

Always show the source used, estimated active hours, confidence, and the limitation that invisible work is missing.

Timestamp proximity between a transcript event and a Git commit is never treated as causal evidence.

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

`communication_confirmations` records the user's interpretation of a communication card. Supported attribution values are `user-expression-insufficient`, `ai-ignored-explicit-requirement`, `term-meaning-mismatch`, `requirement-evolution`, and `insufficient-evidence`. Agents should save it only after the user confirms the attribution or supplies a better rewrite.

## Privacy

Transcript parsing is local. The analyzer makes no upload and stores only short excerpts needed to explain a turning point, repeated-prompt candidate, or communication correction chain. It excludes injected environment and AGENTS instruction events, redacts local home and temporary paths, and does not intentionally copy complete conversations into the report.
