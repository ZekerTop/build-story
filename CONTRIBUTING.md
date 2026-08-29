# Contributing to BuildStory

Thank you for helping make project retrospectives more truthful and useful.

## Good contributions

- focused transcript adapters with realistic fixtures;
- improvements to evidence extraction and confidence labeling;
- accessibility and print improvements to the report;
- corrections to English or Chinese documentation;
- tests demonstrating a real failure before changing a heuristic.

Avoid adding scoring rules based only on intuition. A new metric should explain what it observes, what it cannot prove, and how it can fail.

## Development

```bash
python3 -m unittest discover -s tests -v
python3 scripts/create_demo_report.py
```

Run the Skill validator when available:

```bash
python3 /path/to/skill-creator/scripts/quick_validate.py .
```

## Pull requests

Keep pull requests narrow. Include:

1. the user-visible problem;
2. the evidence or fixture that reproduces it;
3. the behavior before and after;
4. privacy or compatibility implications.

Do not include real private transcripts in fixtures.

