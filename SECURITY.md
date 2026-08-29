# Security and privacy

BuildStory analyzes local source history and optionally authorized AI-session transcripts. Privacy failures are treated as security issues.

## Default behavior

- no network requests;
- no automatic transcript discovery outside the selected inputs;
- no source-file modification;
- no absolute local paths in generated reports;
- no intentional copying of complete conversations into output;
- reports are private local files until the user chooses to share them.

## Reporting a vulnerability

Please open a GitHub security advisory for vulnerabilities involving path exposure, unintended file access, command injection, transcript leakage, or unsafe HTML generation. Avoid placing private logs or secrets in a public issue.

For ordinary bugs that do not expose private data, use a normal GitHub issue with a synthetic reproduction.

