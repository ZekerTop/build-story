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
        context = Path(self.temp.name) / "context.json"
        context.write_text(
            json.dumps(
                {
                    "en": {
                        "role": "the product direction and implementation",
                        "outcome": "shipped a tagged release with a tested local workflow.",
                        "key_decision": "removed the persistent cache after repeated invalidation work.",
                        "summary": "From a fragile persistent cache back to a simpler local workflow.",
                        "resume_bullets": ["Shipped a tested local workflow after reversing a fragile cache design."],
                    }
                }
            ),
            encoding="utf-8",
        )
        run(
            [
                sys.executable,
                str(SCRIPT),
                str(self.repo),
                "--output",
                str(output),
                "--language",
                "en",
                "--context",
                str(context),
            ],
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
        self.assertEqual(data["schema_version"], "1.4")
        self.assertEqual(data["generator_version"], "0.3.0")
        self.assertEqual(data["metrics"]["commits"], 7)
        self.assertEqual(data["project"]["path"], "sample-project")
        self.assertEqual(data["activity"]["calendar_days"], 4)
        self.assertEqual(data["activity"]["active_days"], 4)
        self.assertEqual(data["activity"]["longest_streak"], 4)
        self.assertEqual(data["activity"]["busiest_day"]["date"], "2026-08-01")
        self.assertEqual(len(data["activity"]["days"]), 4)
        self.assertEqual(len(data["dimensions"]), 5)
        self.assertLessEqual(len(data["turning_points"]), 7)
        self.assertEqual(data["story"]["headline"], "From a fragile persistent cache back to a simpler local workflow.")
        self.assertTrue(data["career_material"]["confirmed"])
        self.assertTrue(all(item["level"] and item["recommendation"] for item in data["dimensions"]))
        self.assertTrue(any(item["type"] == "explicit-reversal" for item in data["loop_candidates"]))
        self.assertTrue(any(item["path"] == "src/app.py" for item in data["friction_zones"]))
        self.assertTrue(data["journey_insights"])
        insight = data["journey_insights"][0]
        self.assertEqual(insight["classification"], "direction-change")
        self.assertEqual(insight["topic"], "Add persistent task cache")
        self.assertEqual(
            [item["subject"] for item in insight["evidence_chain"]],
            [
                "Initialize project structure",
                "Add persistent task cache",
                "Fix cache invalidation for repeated tasks",
                "Refactor cache ownership",
                'Revert "Add persistent task cache"',
            ],
        )
        report = (output / "report.html").read_text(encoding="utf-8")
        self.assertIn("From a fragile persistent cache", report)
        self.assertIn("The turns that changed the project", report)
        self.assertIn("Project rhythm", report)
        self.assertIn('id="story-map"', report)
        self.assertIn('id="insights"', report)
        self.assertIn('class="section-nav"', report)
        self.assertIn('data-turn-index="1"', report)
        self.assertIn('data-focus-date="2026-08-01"', report)
        self.assertIn('aria-pressed="true"', report)
        self.assertIn("Related turning points", report)
        self.assertIn("The story behind the rework", report)
        self.assertIn("Direction change", report)
        self.assertIn("Current judgment", report)
        self.assertIn("Needs your confirmation", report)
        self.assertLess(report.index('id="story-map"'), report.index('id="insights"'))
        self.assertLess(report.index('id="insights"'), report.index('id="rhythm"'))
        self.assertIn('class="activity-cell', report)
        self.assertIn("View every commit", report)
        self.assertIn("Turn evidence into a story", report)
        self.assertIn('class="lang-switch"', report)
        self.assertIn('href="report.zh.html"', report)
        self.assertNotIn(str(self.repo.parent), report)

    def test_authorized_transcript_adds_repeat_signal(self):
        self.make_history()
        transcript = Path(self.temp.name) / "session.jsonl"
        rows = [
            {"timestamp": "2026-08-03T08:30:00Z", "role": "user", "content": "Please fix the cache invalidation when the same task runs twice"},
            {"timestamp": "2026-08-03T08:35:00Z", "role": "assistant", "content": "I changed the cache ownership."},
            {"timestamp": "2026-08-03T08:45:00Z", "role": "user", "content": "Please fix cache invalidation when the same task is executed twice"},
            {"timestamp": "2026-08-03T08:50:00Z", "role": "assistant", "content": "Tests now pass."},
        ]
        transcript.write_text("\n".join(json.dumps(row) for row in rows), encoding="utf-8")
        context = Path(self.temp.name) / "context.zh.json"
        context.write_text(
            json.dumps(
                {
                    "zh": {
                        "insight_confirmations": {
                            "path:src/app.py": {
                                "classification": "direction-change",
                                "reason": "持久缓存带来的失效复杂度超过了它的价值。",
                                "lesson": "同一状态问题连续修复后，先重新判断是否需要这层状态。",
                            }
                        },
                        "translations": {
                            "Add tests for greeting behavior": "为问候行为补充测试",
                            "Please fix cache invalidation when the same task is executed twice": "修复同一任务重复执行时的缓存失效问题。",
                            "Tests now pass.": "测试现在已经通过。",
                        }
                    }
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        output = Path(self.temp.name) / "report-with-session"
        run(
            [
                sys.executable,
                str(SCRIPT),
                str(self.repo),
                "--session",
                str(transcript),
                "--context",
                str(context),
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
        self.assertEqual(data["activity"]["busiest_day"]["date"], "2026-08-03")
        self.assertEqual(data["activity"]["busiest_day"]["transcript_events"], 4)
        validation_point = next(item for item in data["turning_points"] if item["category"] == "validation")
        self.assertEqual(validation_point["subject"], "为问候行为补充测试")
        self.assertEqual(validation_point["original_subject"], "Add tests for greeting behavior")
        self.assertEqual(validation_point["dialogue"]["user"], "修复同一任务重复执行时的缓存失效问题。")
        self.assertEqual(validation_point["dialogue"]["ai"], "测试现在已经通过。")
        insight = next(item for item in data["journey_insights"] if item["supporting_path"] == "src/app.py")
        self.assertEqual(insight["confidence"], "confirmed")
        self.assertEqual(insight["confirmation"], "持久缓存带来的失效复杂度超过了它的价值。")
        self.assertEqual(insight["lesson"], "同一状态问题连续修复后，先重新判断是否需要这层状态。")
        self.assertNotIn(str(transcript.parent), (output / "report.html").read_text(encoding="utf-8"))
        report = (output / "report.html").read_text(encoding="utf-8")
        self.assertIn('href="report.en.html"', report)
        self.assertIn('class="is-current" lang="zh-CN"', report)
        visible = report.split('<script type="application/json"', 1)[0]
        self.assertIn("真正改变项目的转折点", visible)
        self.assertIn("项目节奏", visible)
        self.assertIn("活跃开发日", visible)
        self.assertIn("最长连续推进", visible)
        self.assertIn("变更最密集日", visible)
        self.assertNotIn("最勤快", visible)
        self.assertIn("查看全部提交", visible)
        self.assertIn("核心代码", visible)
        self.assertIn("项目根目录", visible)
        self.assertIn("查看计算方法", visible)
        self.assertIn("为问候行为补充测试", visible)
        self.assertIn("用户", visible)
        self.assertIn("AI", visible)
        self.assertIn("修复同一任务重复执行时的缓存失效问题。", visible)
        self.assertIn("你的确认", visible)
        self.assertIn("沉淀的经验", visible)
        self.assertNotIn("Add tests for greeting behavior", visible)
        self.assertNotIn(" files ·", visible)
        self.assertNotIn(" commits ·", visible)
        self.assertNotIn(" touches", visible)
        self.assertNotIn("explicit reversal", visible)
        self.assertNotIn("test files", visible)
        self.assertNotIn("CI workflow", visible)

    def test_classifies_necessary_exploration_when_changes_reach_validation(self):
        self.commit(
            "Initialize parser project",
            "2026-08-01T09:00:00+00:00",
            {
                "README.md": "# Parser\n",
                "src/parser.py": "def parse(text):\n    return text.split()\n",
            },
        )
        self.commit(
            "Add quoted value parsing",
            "2026-08-02T09:00:00+00:00",
            {
                "src/parser.py": "def parse(text):\n    parts = []\n    current = ''\n    quoted = False\n    for char in text:\n        if char == '\"':\n            quoted = not quoted\n        elif char == ' ' and not quoted:\n            parts.append(current)\n            current = ''\n        else:\n            current += char\n    return parts + [current]\n",
            },
        )
        self.commit(
            "Refactor parser state boundaries",
            "2026-08-03T09:00:00+00:00",
            {
                "src/parser.py": "def parse(text):\n    result = []\n    token = []\n    quote = None\n    for char in text:\n        if char in {'\"', \"'\"}:\n            quote = None if quote == char else char\n        elif char.isspace() and quote is None:\n            if token:\n                result.append(''.join(token))\n                token = []\n        else:\n            token.append(char)\n    if token:\n        result.append(''.join(token))\n    return result\n",
            },
        )
        self.commit(
            "Add parser regression tests",
            "2026-08-04T09:00:00+00:00",
            {
                "src/parser.py": "# Covered by regression tests.\n\ndef parse(text):\n    result = []\n    token = []\n    quote = None\n    for char in text:\n        if char in {'\"', \"'\"}:\n            quote = None if quote == char else char\n        elif char.isspace() and quote is None:\n            if token:\n                result.append(''.join(token))\n                token = []\n        else:\n            token.append(char)\n    if token:\n        result.append(''.join(token))\n    return result\n",
                "tests/test_parser.py": "from src.parser import parse\n\ndef test_quotes():\n    assert parse('a \"b c\"') == ['a', 'b c']\n",
            },
        )
        output = Path(self.temp.name) / "exploration-report"
        run([sys.executable, str(SCRIPT), str(self.repo), "--output", str(output)], self.repo)
        data = json.loads((output / "evidence.json").read_text(encoding="utf-8"))
        insight = next(item for item in data["journey_insights"] if item["supporting_path"] == "src/parser.py")
        self.assertEqual(insight["classification"], "necessary-exploration")
        self.assertEqual(insight["confidence"], "medium")

    def test_classifies_blocked_loop_when_repairs_repeat_without_closure(self):
        self.commit(
            "Initialize retry worker",
            "2026-08-01T09:00:00+00:00",
            {
                "README.md": "# Retry Worker\n",
                "src/retry.py": "def retry(job):\n    return job()\n",
            },
        )
        self.commit(
            "Add retry queue",
            "2026-08-02T09:00:00+00:00",
            {
                "src/retry.py": "QUEUE = []\n\ndef retry(job):\n    QUEUE.append(job)\n    return job()\n",
            },
        )
        self.commit(
            "Fix retry timeout handling",
            "2026-08-03T09:00:00+00:00",
            {
                "src/retry.py": "QUEUE = []\n\ndef retry(job, timeout=3):\n    QUEUE.append((job, timeout))\n    return job()\n",
            },
        )
        self.commit(
            "Fix retry timeout state again",
            "2026-08-04T09:00:00+00:00",
            {
                "src/retry.py": "QUEUE = {}\n\ndef retry(job, timeout=3):\n    QUEUE[id(job)] = timeout\n    return job()\n",
            },
        )
        self.commit(
            "Refactor retry backoff ownership",
            "2026-08-05T09:00:00+00:00",
            {
                "src/retry.py": "QUEUE = {}\n\ndef retry(job, timeout=3, backoff=1):\n    QUEUE[id(job)] = {'timeout': timeout, 'backoff': backoff}\n    return job()\n",
            },
        )
        output = Path(self.temp.name) / "blocked-report"
        run([sys.executable, str(SCRIPT), str(self.repo), "--output", str(output)], self.repo)
        data = json.loads((output / "evidence.json").read_text(encoding="utf-8"))
        insight = next(item for item in data["journey_insights"] if item["supporting_path"] == "src/retry.py")
        self.assertEqual(insight["classification"], "blocked-loop")
        self.assertEqual(insight["confidence"], "high")

    def test_malformed_json_session_does_not_break_git_report(self):
        self.make_history()
        transcript = Path(self.temp.name) / "broken.json"
        transcript.write_text("{not valid json", encoding="utf-8")
        output = Path(self.temp.name) / "report-with-broken-session"
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
        self.assertEqual(data["metrics"]["commits"], 7)
        self.assertEqual(data["coverage"]["transcript_files"], ["broken.json"])
        self.assertEqual(data["transcripts"]["events"], 0)
        self.assertEqual(data["transcripts"]["confidence"], "low")


if __name__ == "__main__":
    unittest.main()
