import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "build_story.py"


def run(command, cwd, env=None):
    result = subprocess.run(
        command,
        cwd=str(cwd),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
    )
    if result.returncode != 0:
        raise AssertionError(f"Command failed: {' '.join(command)}\n{result.stdout}\n{result.stderr}")
    return result.stdout


class BuildStoryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.repo = Path(self.temp.name) / "sample-project"
        self.repo.mkdir()
        run(["git", "init", "-b", "main"], self.repo)
        run(["git", "config", "user.name", "BuildStory Test"], self.repo)
        run(["git", "config", "user.email", "buildstory@example.test"], self.repo)

    def tearDown(self):
        self.temp.cleanup()

    def commit(self, message, date, files):
        for name, content in files.items():
            path = self.repo / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
        run(["git", "add", "."], self.repo)
        env = os.environ.copy()
        env["GIT_AUTHOR_DATE"] = date
        env["GIT_COMMITTER_DATE"] = date
        run(["git", "commit", "-m", message], self.repo, env=env)

    def make_history(self):
        self.commit(
            "Initialize project structure",
            "2026-08-01T09:00:00+00:00",
            {
                "README.md": "# Sample Project\n\nA tiny project used to verify BuildStory.\n",
                "LICENSE": "MIT\n",
                "pyproject.toml": "[project]\nname='sample-project'\nversion='0.1.0'\n",
                "src/app.py": "def greet(name):\n    return f'Hello {name}'\n",
            },
        )
        self.commit(
            "Add persistent task cache",
            "2026-08-01T10:00:00+00:00",
            {"src/app.py": "CACHE = {}\n\ndef greet(name):\n    CACHE[name] = True\n    return f'Hello {name}'\n"},
        )
        self.commit(
            "Fix cache invalidation for repeated tasks",
            "2026-08-01T11:10:00+00:00",
            {"src/app.py": "CACHE = {}\n\ndef greet(name):\n    CACHE.clear()\n    CACHE[name] = True\n    return f'Hello {name}'\n"},
        )
        self.commit(
            "Refactor cache ownership",
            "2026-08-02T08:00:00+00:00",
            {"src/app.py": "def greet(name):\n    cache = {name: True}\n    return f'Hello {name}' if cache[name] else name\n"},
        )
        self.commit(
            'Revert "Add persistent task cache"',
            "2026-08-02T09:00:00+00:00",
            {"src/app.py": "def greet(name):\n    return f'Hello {name}'\n"},
        )
        self.commit(
            "Add tests for greeting behavior",
            "2026-08-03T09:00:00+00:00",
            {"tests/test_app.py": "from src.app import greet\n\ndef test_greet():\n    assert greet('Ada') == 'Hello Ada'\n"},
        )
        self.commit(
            "Document release workflow",
            "2026-08-04T09:00:00+00:00",
            {"docs/release.md": "# Release\n\nRun tests, tag, then publish.\n"},
        )
        run(["git", "tag", "v0.1.0"], self.repo)

    def test_generates_evidence_markdown_and_html(self):
        self.make_history()
        output = Path(self.temp.name) / "report"
        run(
            [sys.executable, str(SCRIPT), str(self.repo), "--output", str(output), "--language", "en"],
            self.repo,
        )
        self.assertTrue((output / "evidence.json").exists())
        self.assertTrue((output / "report.md").exists())
        self.assertTrue((output / "report.html").exists())
        self.assertTrue((output / "evidence.en.json").exists())
        self.assertTrue((output / "evidence.zh.json").exists())
        self.assertTrue((output / "report.en.html").exists())
        self.assertTrue((output / "report.zh.html").exists())
        data = json.loads((output / "evidence.json").read_text(encoding="utf-8"))
        self.assertEqual(data["metrics"]["commits"], 7)
        self.assertEqual(data["project"]["path"], "sample-project")
        self.assertEqual(len(data["dimensions"]), 5)
        self.assertTrue(any(item["type"] == "explicit-reversal" for item in data["loop_candidates"]))
        self.assertTrue(any(item["path"] == "src/app.py" for item in data["friction_zones"]))
        report = (output / "report.html").read_text(encoding="utf-8")
        self.assertIn("See how you built it", report)
        self.assertIn("Project life line", report)
        self.assertIn('class="lang-switch"', report)
        self.assertIn('href="report.zh.html"', report)
        self.assertNotIn(str(self.repo.parent), report)

    def test_authorized_transcript_adds_repeat_signal(self):
        self.make_history()
        transcript = Path(self.temp.name) / "session.jsonl"
        rows = [
            {"timestamp": "2026-08-03T10:00:00Z", "role": "user", "content": "Please fix the cache invalidation when the same task runs twice"},
            {"timestamp": "2026-08-03T10:05:00Z", "role": "assistant", "content": "I changed the cache ownership."},
            {"timestamp": "2026-08-03T10:10:00Z", "role": "user", "content": "Please fix cache invalidation when the same task is executed twice"},
            {"timestamp": "2026-08-03T10:14:00Z", "role": "assistant", "content": "Tests now pass."},
        ]
        transcript.write_text("\n".join(json.dumps(row) for row in rows), encoding="utf-8")
        output = Path(self.temp.name) / "report-with-session"
        run(
            [
                sys.executable,
                str(SCRIPT),
                str(self.repo),
                "--session",
                str(transcript),
                "--output",
                str(output),
                "--language",
                "zh",
            ],
            self.repo,
        )
        data = json.loads((output / "evidence.json").read_text(encoding="utf-8"))
        self.assertIn("transcripts", data["coverage"]["sources"])
        self.assertEqual(data["coverage"]["transcript_files"], ["session.jsonl"])
        self.assertTrue(data["transcripts"]["repeated_prompts"])
        self.assertNotIn(str(transcript.parent), (output / "report.html").read_text(encoding="utf-8"))
        report = (output / "report.html").read_text(encoding="utf-8")
        self.assertIn('href="report.en.html"', report)
        self.assertIn('class="is-current" lang="zh-CN"', report)


if __name__ == "__main__":
    unittest.main()
