import json
import importlib.util
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "build_story.py"
SPEC = importlib.util.spec_from_file_location("build_story_module", SCRIPT)
BUILD_STORY = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = BUILD_STORY
SPEC.loader.exec_module(BUILD_STORY)


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

    def transcript_events(self, messages, source="session.jsonl", session_id=None, source_key=None):
        events = []
        for index, (role, text) in enumerate(messages):
            events.append(
                {
                    "timestamp": BUILD_STORY.parse_datetime(f"2026-08-30T10:{index:02d}:00Z"),
                    "role": role,
                    "canonical_role": role,
                    "text": text,
                    "source": source,
                    "source_key": source_key or source,
                    "session_id": session_id or source,
                    "event_index": index,
                }
            )
        return events

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
        self.assertEqual(data["schema_version"], "1.5")
        self.assertEqual(data["generator_version"], "0.4.0")
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
        self.assertNotIn("max-width:1040px", report)
        self.assertLess(report.index('id="story-map"'), report.index('id="insights"'))
        self.assertLess(report.index('id="insights"'), report.index('id="rhythm"'))
        self.assertNotIn('id="communication"', report)
        self.assertNotIn("## Communication review", (output / "report.md").read_text(encoding="utf-8"))
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
        self.assertEqual(data["communication_insights"], [])
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
        self.assertIn('id="communication"', report)
        self.assertIn("沟通复盘", visible)
        self.assertIn("没有达到证据门槛的沟通纠正链", visible)
        self.assertIn("## 沟通复盘", (output / "report.md").read_text(encoding="utf-8"))
        self.assertLess(report.index('id="insights"'), report.index('id="communication"'))
        self.assertLess(report.index('id="communication"'), report.index('id="rhythm"'))
        self.assertNotIn("Add tests for greeting behavior", visible)
        self.assertNotIn(" files ·", visible)
        self.assertNotIn(" commits ·", visible)
        self.assertNotIn(" touches", visible)
        self.assertNotIn("explicit reversal", visible)
        self.assertNotIn("test files", visible)
        self.assertNotIn("CI workflow", visible)

    def test_communication_review_finds_information_clarified_later(self):
        events = self.transcript_events(
            [
                ("user", "GitHub 上进去应该是中文为主。"),
                ("assistant", "README 和 About 已改为中文。"),
                ("user", "我说的是动态标题和用户与 AI 的对话历程也要中文。"),
            ]
        )
        insights = BUILD_STORY.build_communication_insights(events, [], {}, "zh")
        self.assertEqual(len(insights), 1)
        self.assertEqual(insights[0]["attribution"], "user-expression-insufficient")
        self.assertEqual(insights[0]["gap_type"], "ambiguous-reference")
        self.assertIn("目标：", insights[0]["suggested_rewrite"])
        self.assertIn("范围：", insights[0]["suggested_rewrite"])
        self.assertNotIn("请按这个完整要求执行", insights[0]["suggested_rewrite"])

    def test_communication_rewrite_synthesizes_guidance_and_splits_another_bug(self):
        events = self.transcript_events(
            [
                ("user", "不要每次都弹出"),
                ("assistant", "我已经调整应用的桌面通知，避免每次任务完成都重复显示。"),
                (
                    "user",
                    "我说的桌面通知，不是说应用的桌面通知，而是说允许访问的桌面通知，"
                    "另外我在 Mac 系统中将应用隐藏到托盘之后，就没办法打开了，这是为什么？检查一下",
                ),
            ]
        )
        insight = BUILD_STORY.build_communication_insights(events, [], {}, "zh")[0]
        self.assertEqual(insight["attribution"], "term-meaning-mismatch")
        self.assertEqual(insight["later_clarification"], "我说的桌面通知，不是说应用的桌面通知，而是说允许访问的桌面通知")
        self.assertIn("系统通知权限请求", insight["analysis"])
        self.assertIn("另一个问题", insight["analysis"])
        self.assertIn("系统通知权限请求重复出现", insight["suggested_rewrite"])
        self.assertIn("边界：不要改动“应用发出的通知”相关功能", insight["suggested_rewrite"])
        self.assertIn("验收：", insight["suggested_rewrite"])
        self.assertNotIn("托盘", insight["suggested_rewrite"])
        self.assertNotIn("请按这个完整要求执行", insight["suggested_rewrite"])
        self.assertTrue(any("拆成单独任务" in item for item in insight["missing_information"]))

    def test_communication_review_recovers_requirement_before_short_approval(self):
        events = self.transcript_events(
            [
                ("user", "读取真实会话，找出用户和 AI 说岔的地方，并给出真正改进后的表达。"),
                ("assistant", "我会增加沟通复盘和改写。"),
                ("user", "可以的，开始吧，完成后上传到github上"),
                ("assistant", "已经完成。"),
                ("user", "为什么我还是没有看到新加的功能？根本没有真正的改写。"),
            ]
        )
        insights = BUILD_STORY.build_communication_insights(events, [], {}, "zh")
        self.assertEqual(len(insights), 1)
        self.assertEqual(insights[0]["attribution"], "ai-ignored-explicit-requirement")
        self.assertEqual(
            insights[0]["original_request"],
            "读取真实会话，找出用户和 AI 说岔的地方，并给出真正改进后的表达。",
        )
        self.assertEqual(insights[0]["event_range"], [0, 4])

    def test_communication_review_keeps_three_distinct_cases(self):
        events = self.transcript_events(
            [
                ("user", "Make storage better for beginners"),
                ("assistant", "I connected the task list to a hosted database."),
                ("user", "I mean local JSON storage, not a hosted service. Keep all task data on the device."),
                ("user", "Make sure the local data flow works"),
                ("assistant", "I ran the CLI once and the command completed."),
                ("user", "I mean add automated tests for local storage and JSON export. Do not add cloud dependencies."),
                ("user", "Document it"),
                ("assistant", "I added another usage example."),
                ("user", "I mean document why we chose local-first export instead of hidden cloud sync, not only how to use the CLI."),
            ]
        )
        insights = BUILD_STORY.build_communication_insights(events, [], {}, "en")
        self.assertEqual(len(insights), 3)
        self.assertEqual(
            {item["original_request"] for item in insights},
            {
                "Make storage better for beginners",
                "Make sure the local data flow works",
                "Document it",
            },
        )

    def test_communication_review_attributes_clear_requirement_miss_to_ai(self):
        events = self.transcript_events(
            [
                ("user", "README、GitHub About、动态标题和对话摘录都要中文；英文版继续保留英文。"),
                ("assistant", "README 和 About 已经改完。"),
                ("user", "动态标题和对话摘录还是英文，我已经说了它们也要中文。"),
            ]
        )
        insights = BUILD_STORY.build_communication_insights(events, [], {}, "zh")
        self.assertEqual(len(insights), 1)
        self.assertEqual(insights[0]["attribution"], "ai-ignored-explicit-requirement")
        self.assertIsNone(insights[0]["suggested_rewrite"])
        self.assertEqual(insights[0]["missing_information"], [])
        self.assertIsNone(insights[0]["reusable_pattern"])

    def test_communication_review_preserves_requirement_evolution(self):
        events = self.transcript_events(
            [
                ("user", "先做中文版本就可以。"),
                ("assistant", "中文报告已经生成。"),
                ("user", "看了以后，我觉得还是加上中英文切换比较好。"),
            ]
        )
        insights = BUILD_STORY.build_communication_insights(events, [], {}, "zh")
        self.assertEqual(len(insights), 1)
        self.assertEqual(insights[0]["attribution"], "requirement-evolution")
        self.assertIsNone(insights[0]["suggested_rewrite"])
        self.assertEqual(insights[0]["missing_information"], [])
        self.assertIsNone(insights[0]["reusable_pattern"])

    def test_communication_review_skips_successful_clarification_and_cross_session_chain(self):
        clarification = self.transcript_events(
            [
                ("user", "页面更有记忆点一点。"),
                ("assistant", "你更想加强叙事结构、视觉风格，还是交互动效？"),
                ("user", "加强叙事结构，不要增加复杂动画。"),
            ]
        )
        self.assertEqual(BUILD_STORY.build_communication_insights(clarification, [], {}, "zh"), [])

        cross_session = self.transcript_events(
            [("user", "报告需要中文。"), ("assistant", "好的。")],
            source="session-a.jsonl",
        )
        cross_session.extend(
            self.transcript_events(
                [("user", "动态标题也要中文。")],
                source="session-b.jsonl",
            )
        )
        self.assertEqual(BUILD_STORY.build_communication_insights(cross_session, [], {}, "zh"), [])

    def test_communication_review_handles_segmented_assistant_response(self):
        events = self.transcript_events(
            [
                ("user", "GitHub 上进去应该是中文为主。"),
                ("assistant", "我先检查 README。"),
                ("assistant", "README 和 About 已改为中文。"),
                ("user", "我说的是动态标题和用户与 AI 的对话历程也要中文。"),
            ]
        )
        insights = BUILD_STORY.build_communication_insights(events, [], {}, "zh")
        self.assertEqual(len(insights), 1)
        self.assertIn("README 和 About", insights[0]["ai_response"])
        self.assertEqual(insights[0]["event_range"], [0, 3])

    def test_communication_review_skips_normal_bug_followup(self):
        events = self.transcript_events(
            [
                ("user", "Fix automatic cloud sync because duplicate tasks are appearing in the queue"),
                ("assistant", "I added duplicate prevention."),
                ("user", "Fix the automatic cloud sync queue again and make retries easier to understand"),
            ]
        )
        self.assertEqual(BUILD_STORY.build_communication_insights(events, [], {}, "en"), [])

    def test_communication_review_is_language_neutral(self):
        events = self.transcript_events(
            [
                ("user", "Make storage better for beginners"),
                ("assistant", "I connected the task list to a hosted database."),
                ("user", "I mean local JSON storage, not a hosted service. Keep all task data on the device."),
                ("user", "Keep exports local too."),
            ]
        )
        zh_context = {
            "translations": {
                "Make storage better for beginners": "让存储体验对新手更友好。",
                "I connected the task list to a hosted database.": "我把任务列表连接到了托管数据库。",
                "I mean local JSON storage, not a hosted service. Keep all task data on the device.": "我说的是本地 JSON 存储，不是托管服务。所有任务数据都保留在设备上。",
                "Keep exports local too.": "导出也要保留在本地。",
            }
        }
        en = BUILD_STORY.build_communication_insights(events, [], {}, "en")
        zh = BUILD_STORY.build_communication_insights(events, [], zh_context, "zh")
        self.assertEqual(
            [(item["id"], item["attribution"], item["gap_type"]) for item in en],
            [(item["id"], item["attribution"], item["gap_type"]) for item in zh],
        )
        self.assertEqual(en[0]["attribution"], "term-meaning-mismatch")
        self.assertNotEqual(en[0]["original_request"], zh[0]["original_request"])
        self.assertNotIn("导出也要保留在本地", zh[0]["later_clarification"])
        self.assertNotIn("Keep exports local", zh[0]["later_clarification"])

    def test_communication_confirmation_rebuilds_guidance_after_attribution_override(self):
        events = self.transcript_events(
            [
                ("user", "GitHub 上进去应该是中文为主。"),
                ("assistant", "README 和 About 已改为中文。"),
                ("user", "我说的是动态标题和用户与 AI 的对话历程也要中文。"),
            ]
        )
        initial = BUILD_STORY.build_communication_insights(events, [], {}, "zh")[0]
        context = {
            "communication_confirmations": {
                initial["id"]: {
                    "attribution": "ai-ignored-explicit-requirement",
                    "reason": "原始要求已经足够明确，是执行时遗漏。",
                }
            }
        }
        confirmed = BUILD_STORY.build_communication_insights(events, [], context, "zh")[0]
        self.assertEqual(confirmed["attribution"], "ai-ignored-explicit-requirement")
        self.assertEqual(confirmed["gap_type"], "ai-execution-miss")
        self.assertIsNone(confirmed["suggested_rewrite"])
        self.assertEqual(confirmed["missing_information"], [])
        self.assertIsNone(confirmed["reusable_pattern"])

        context["communication_confirmations"][initial["id"]]["attribution"] = "insufficient-evidence"
        insufficient = BUILD_STORY.build_communication_insights(events, [], context, "zh")[0]
        self.assertEqual(insufficient["attribution"], "insufficient-evidence")
        self.assertEqual(insufficient["gap_type"], "insufficient-evidence")
        self.assertIsNone(insufficient["suggested_rewrite"])

    def test_transcript_reader_separates_same_named_files_and_propagates_session_id(self):
        transcript_root = Path(self.temp.name) / "transcripts"
        first = transcript_root / "a" / "session.jsonl"
        second = transcript_root / "b" / "session.jsonl"
        first.parent.mkdir(parents=True)
        second.parent.mkdir(parents=True)
        first.write_text(
            "\n".join(
                json.dumps(row)
                for row in [
                    {"timestamp": "2026-08-30T10:00:00Z", "sessionId": "thread-a", "role": "user", "content": "报告需要中文。"},
                    {"timestamp": "2026-08-30T10:01:00Z", "role": "assistant", "content": "好的。"},
                ]
            ),
            encoding="utf-8",
        )
        second.write_text(
            json.dumps(
                {"timestamp": "2026-08-30T10:02:00Z", "role": "user", "content": "我说的是动态标题也要中文。"},
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        events, files = BUILD_STORY.read_transcript_events([transcript_root])
        self.assertEqual(files.count("session.jsonl"), 2)
        self.assertEqual(len({event["source_key"] for event in events}), 2)
        first_source = events[0]["source_key"]
        self.assertTrue(all(event["session_id"] == "thread-a" for event in events if event["source_key"] == first_source))
        self.assertEqual(BUILD_STORY.build_communication_insights(events, [], {}, "zh"), [])

    def test_codex_nested_events_are_parsed_and_multi_session_runs_stay_isolated(self):
        codex = Path(self.temp.name) / "codex.jsonl"
        codex_rows = [
            {"timestamp": "2026-08-30T10:00:00Z", "type": "session_meta", "payload": {"id": "codex-a"}},
            {"timestamp": "2026-08-30T10:01:00Z", "type": "response_item", "payload": {"role": "user", "content": [{"type": "input_text", "text": "Make storage better for beginners"}]}},
            {"timestamp": "2026-08-30T10:02:00Z", "type": "response_item", "payload": {"role": "assistant", "content": [{"type": "output_text", "text": "I connected the task list to a hosted database."}]}},
            {"timestamp": "2026-08-30T10:03:00Z", "type": "response_item", "payload": {"role": "user", "content": [{"type": "input_text", "text": "I mean local JSON storage, not a hosted service. Keep all task data on the device."}]}},
        ]
        codex.write_text("\n".join(json.dumps(row) for row in codex_rows), encoding="utf-8")
        events, _ = BUILD_STORY.read_transcript_events([codex])
        messages = [event for event in events if event["canonical_role"] in {"user", "assistant"}]
        self.assertEqual([event["canonical_role"] for event in messages], ["user", "assistant", "user"])
        self.assertTrue(all(event["session_id"] == "codex-a" for event in messages))
        self.assertEqual(len(BUILD_STORY.build_communication_insights(events, [], {}, "en")), 1)

        archive = Path(self.temp.name) / "archive.json"
        archive.write_text(
            json.dumps(
                {
                    "conversations": [
                        {
                            "id": "archive-a",
                            "messages": [
                                {"timestamp": "2026-08-30T10:10:00Z", "role": "user", "content": "Document it"},
                                {"timestamp": "2026-08-30T10:11:00Z", "role": "assistant", "content": "I added another usage example."},
                                {"timestamp": "2026-08-30T10:12:00Z", "role": "user", "content": "I mean document the architecture decision, not only CLI usage."},
                            ],
                        }
                    ]
                }
            ),
            encoding="utf-8",
        )
        events, _ = BUILD_STORY.read_transcript_events([archive])
        self.assertTrue(all(event["session_id"] == "archive-a" for event in events))
        self.assertEqual(len(BUILD_STORY.build_communication_insights(events, [], {}, "en")), 1)

        multi = Path(self.temp.name) / "multi-session.jsonl"
        multi_rows = [
            {"timestamp": "2026-08-30T11:00:00Z", "type": "session_meta", "payload": {"id": "session-a"}},
            {"timestamp": "2026-08-30T11:01:00Z", "type": "response_item", "payload": {"role": "user", "content": [{"text": "报告需要中文。"}]}},
            {"timestamp": "2026-08-30T11:02:00Z", "type": "response_item", "payload": {"role": "assistant", "content": [{"text": "好的。"}]}},
            {"timestamp": "2026-08-30T11:03:00Z", "type": "session_meta", "payload": {"id": "session-b"}},
            {"timestamp": "2026-08-30T11:04:00Z", "type": "response_item", "payload": {"role": "user", "content": [{"text": "我说的是动态标题也要中文。"}]}},
        ]
        multi.write_text("\n".join(json.dumps(row, ensure_ascii=False) for row in multi_rows), encoding="utf-8")
        events, _ = BUILD_STORY.read_transcript_events([multi])
        user_sessions = [event["session_id"] for event in events if event["canonical_role"] == "user"]
        self.assertEqual(len(set(user_sessions)), 2)
        self.assertEqual(BUILD_STORY.build_communication_insights(events, [], {}, "zh"), [])

    def test_communication_id_survives_moving_the_same_transcript(self):
        rows = [
            {"timestamp": "2026-08-30T10:00:00Z", "role": "user", "content": "Make storage better for beginners"},
            {"timestamp": "2026-08-30T10:01:00Z", "role": "assistant", "content": "I connected the task list to a hosted database."},
            {"timestamp": "2026-08-30T10:02:00Z", "role": "user", "content": "I mean local JSON storage, not a hosted service. Keep all task data on the device."},
        ]
        ids = []
        for directory in ("move-a", "move-b"):
            transcript = Path(self.temp.name) / directory / "session.jsonl"
            transcript.parent.mkdir()
            transcript.write_text("\n".join(json.dumps(row) for row in rows), encoding="utf-8")
            events, _ = BUILD_STORY.read_transcript_events([transcript])
            ids.append(BUILD_STORY.build_communication_insights(events, [], {}, "en")[0]["id"])
        self.assertEqual(ids[0], ids[1])

    def test_transcript_injections_are_excluded_and_local_paths_are_redacted(self):
        transcript = Path(self.temp.name) / "session.jsonl"
        rows = [
            {"timestamp": "2026-08-30T09:59:00Z", "role": "user", "content": "<environment_context><cwd>/Users/zt/Desktop/private-project</cwd></environment_context>"},
            {"timestamp": "2026-08-30T10:00:00Z", "role": "user", "content": "Document it"},
            {"timestamp": "2026-08-30T10:01:00Z", "role": "assistant", "content": "I updated /Users/zt/Desktop/private-project/README.md with another usage example."},
            {"timestamp": "2026-08-30T10:02:00Z", "role": "user", "content": "I mean document the architecture decision, not only CLI usage."},
        ]
        transcript.write_text("\n".join(json.dumps(row) for row in rows), encoding="utf-8")
        events, files = BUILD_STORY.read_transcript_events([transcript])
        analysis = BUILD_STORY.analyze_transcripts(events, files, "en")
        self.assertEqual(analysis["events"], 3)
        self.assertFalse(analysis["repeated_prompts"])
        insight = BUILD_STORY.build_communication_insights(events, [], {}, "en")[0]
        self.assertNotIn("/Users/", insight["ai_response"])
        self.assertIn("~/Desktop/private-project/README.md", insight["ai_response"])
        sanitized = BUILD_STORY.sanitize_report_value(
            {"home": "/Users/zt/Desktop/private-project", "temp": "/tmp/build-story-secret.txt"}
        )
        self.assertEqual(sanitized["home"], "~/Desktop/private-project")
        self.assertEqual(sanitized["temp"], "<local-path>")

    def test_communication_html_hides_user_guidance_for_ai_miss(self):
        self.make_history()
        data = BUILD_STORY.build_evidence(self.repo, [], "zh", None, {})
        data["coverage"]["sources"].append("transcripts")
        data["communication_insights"] = [
            {
                "id": "communication:test",
                "topic": "明确要求在执行中被遗漏",
                "gap_type": "ai-execution-miss",
                "gap_label": "明确要求在执行中被遗漏",
                "attribution": "ai-ignored-explicit-requirement",
                "attribution_label": "AI 忽略了明确要求",
                "confidence": "high",
                "original_request": "README、动态标题和对话摘录都要中文。",
                "ai_response": "README 已改为中文。",
                "later_clarification": "动态标题和对话摘录还是英文，我已经说了它们也要中文。",
                "analysis": "原要求已经明确，主要问题是执行遗漏。",
                "missing_information": [],
                "suggested_rewrite": None,
                "reusable_pattern": None,
                "question": "原始要求是否已经足够明确？",
                "observed_impact": "没有找到足够接近的 Git 提交。",
                "related_commits": [],
                "source": "session.jsonl",
                "event_range": [0, 2],
                "confirmation": None,
                "lesson": None,
            }
        ]
        report = BUILD_STORY.render_html(data)
        communication = report.split('id="communication"', 1)[1].split('id="rhythm"', 1)[0]
        self.assertIn("这不主要是用户表述问题", communication)
        self.assertIn("列出必须完成、明确排除和需要验证的清单", communication)
        self.assertNotIn("当时缺少的信息", communication)
        self.assertNotIn("下次可以这样说", communication)
        self.assertNotIn("可以复用的表达方式", communication)

        data["communication_insights"][0].update(
            {
                "topic": "证据不足，暂不归因",
                "gap_type": "insufficient-evidence",
                "gap_label": "证据不足，暂不归因",
                "attribution": "insufficient-evidence",
                "attribution_label": "证据不足，无法归因",
            }
        )
        report = BUILD_STORY.render_html(data)
        communication = report.split('id="communication"', 1)[1].split('id="rhythm"', 1)[0]
        self.assertIn("现有证据不足以支持用户侧改写", communication)
        self.assertNotIn("这不主要是用户表述问题", communication)

    def test_large_jsonl_transcript_is_not_skipped_when_it_can_be_streamed(self):
        transcript = Path(self.temp.name) / "large-session.jsonl"
        transcript.write_text("{}\n", encoding="utf-8")
        with transcript.open("r+b") as handle:
            handle.truncate(BUILD_STORY.MAX_TRANSCRIPT_BYTES + 1)

        archive = Path(self.temp.name) / "large-session.json"
        archive.write_text("{}", encoding="utf-8")
        with archive.open("r+b") as handle:
            handle.truncate(BUILD_STORY.MAX_TRANSCRIPT_BYTES + 1)

        self.assertEqual(list(BUILD_STORY.iter_transcript_files([transcript])), [transcript.resolve()])
        self.assertEqual(list(BUILD_STORY.iter_transcript_files([archive])), [])

    def test_non_conversation_events_do_not_consume_the_transcript_event_cap(self):
        first = Path(self.temp.name) / "first.jsonl"
        second = Path(self.temp.name) / "second.jsonl"
        first_rows = [
            {"timestamp": f"2026-08-30T10:0{index}:00Z", "role": "system", "content": "tool output"}
            for index in range(5)
        ]
        first_rows.append(
            {"timestamp": "2026-08-30T10:06:00Z", "role": "user", "content": "First real request"}
        )
        second_rows = [
            {"timestamp": "2026-08-30T10:07:00Z", "role": "assistant", "content": "Second real response"}
        ]
        first.write_text("\n".join(json.dumps(row) for row in first_rows), encoding="utf-8")
        second.write_text("\n".join(json.dumps(row) for row in second_rows), encoding="utf-8")

        original_cap = BUILD_STORY.MAX_TRANSCRIPT_EVENTS
        BUILD_STORY.MAX_TRANSCRIPT_EVENTS = 2
        try:
            events, files = BUILD_STORY.read_transcript_events([first, second])
        finally:
            BUILD_STORY.MAX_TRANSCRIPT_EVENTS = original_cap

        self.assertEqual(files, ["first.jsonl", "second.jsonl"])
        self.assertEqual([event["canonical_role"] for event in events], ["user", "assistant"])

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
