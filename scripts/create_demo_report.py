#!/usr/bin/env python3
"""Create deterministic English and Chinese BuildStory demo reports."""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
from pathlib import Path

import build_story


ROOT = Path(__file__).resolve().parents[1]
DEMO_OUTPUT = ROOT / "examples" / "demo-report"


def run(command: list[str], cwd: Path, env: dict[str, str] | None = None) -> None:
    result = subprocess.run(command, cwd=str(cwd), text=True, capture_output=True, env=env)
    if result.returncode != 0:
        raise RuntimeError(result.stderr or result.stdout)


def commit(repo: Path, message: str, date: str, files: dict[str, str]) -> None:
    for relative, content in files.items():
        path = repo / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    run(["git", "add", "."], repo)
    env = os.environ.copy()
    env["GIT_AUTHOR_DATE"] = date
    env["GIT_COMMITTER_DATE"] = date
    run(["git", "commit", "-m", message], repo, env)


def build_demo_repository(repo: Path) -> Path:
    run(["git", "init", "-b", "main"], repo)
    run(["git", "config", "user.name", "Alex Builder"], repo)
    run(["git", "config", "user.email", "alex@example.test"], repo)

    commit(
        repo,
        "Initialize PocketTasks CLI",
        "2026-07-01T09:00:00+00:00",
        {
            "README.md": "# PocketTasks\n\nA tiny local-first task manager.\n",
            "LICENSE": "MIT\n",
            "pyproject.toml": "[project]\nname='pockettasks'\nversion='0.1.0'\n",
            "src/cli.py": "def main():\n    print('PocketTasks')\n",
        },
    )
    commit(
        repo,
        "Add JSON task storage",
        "2026-07-02T09:20:00+00:00",
        {"src/store.py": "import json\n\ndef save(tasks, path):\n    path.write_text(json.dumps(tasks))\n"},
    )
    commit(
        repo,
        "Add experimental cloud sync queue",
        "2026-07-03T10:15:00+00:00",
        {"src/sync.py": "QUEUE = []\n\ndef push(task):\n    QUEUE.append(task)\n"},
    )
    commit(
        repo,
        "Fix cloud sync duplicate queue entries",
        "2026-07-03T11:40:00+00:00",
        {"src/sync.py": "QUEUE = []\n\ndef push(task):\n    if task not in QUEUE:\n        QUEUE.append(task)\n"},
    )
    commit(
        repo,
        "Refactor cloud sync retry ownership",
        "2026-07-04T09:30:00+00:00",
        {
            "src/sync.py": "QUEUE = []\n\ndef push(task, retries=3):\n    item = {'task': task, 'retries': retries}\n    if item not in QUEUE:\n        QUEUE.append(item)\n"
        },
    )
    commit(
        repo,
        'Revert "Add experimental cloud sync queue"',
        "2026-07-05T09:10:00+00:00",
        {"src/sync.py": "def push(task):\n    raise RuntimeError('sync disabled')\n"},
    )
    commit(
        repo,
        "Replace cloud sync with local export",
        "2026-07-06T10:00:00+00:00",
        {"src/sync.py": "import json\n\ndef export(tasks, path):\n    path.write_text(json.dumps(tasks, indent=2))\n"},
    )
    commit(
        repo,
        "Add tests for storage and export",
        "2026-07-08T09:00:00+00:00",
        {
            "tests/test_store.py": "def test_store_roundtrip():\n    assert True\n",
            "tests/test_export.py": "def test_export_is_local():\n    assert True\n",
        },
    )
    commit(
        repo,
        "Add CI validation workflow",
        "2026-07-09T09:00:00+00:00",
        {
            ".github/workflows/ci.yml": "name: CI\non: [push]\njobs:\n  test:\n    runs-on: ubuntu-latest\n    steps:\n      - run: python -m unittest\n"
        },
    )
    commit(
        repo,
        "Document local-first architecture decision",
        "2026-07-12T09:00:00+00:00",
        {"docs/adr/001-local-first.md": "# Local first\n\nWe chose export over hidden cloud sync.\n"},
    )
    commit(
        repo,
        "Prepare v1 release documentation",
        "2026-07-15T09:00:00+00:00",
        {"CHANGELOG.md": "# Changelog\n\n## 1.0.0\n\nLocal tasks and explicit export.\n"},
    )
    commit(
        repo,
        "Release PocketTasks 1.0",
        "2026-07-18T09:00:00+00:00",
        {"README.md": "# PocketTasks\n\nA local-first task manager with explicit JSON export.\n"},
    )
    run(["git", "tag", "v1.0.0"], repo)

    transcript = repo.parent / "pockettasks-session.jsonl"
    transcript_rows = [
        {"timestamp": "2026-07-03T10:00:00Z", "role": "user", "content": "Add automatic cloud sync but keep the task manager simple for beginners"},
        {"timestamp": "2026-07-03T10:06:00Z", "role": "assistant", "content": "I added a queue and background push."},
        {"timestamp": "2026-07-03T11:20:00Z", "role": "user", "content": "Fix automatic cloud sync because duplicate tasks are appearing in the queue"},
        {"timestamp": "2026-07-03T11:28:00Z", "role": "assistant", "content": "I added duplicate prevention."},
        {"timestamp": "2026-07-04T09:10:00Z", "role": "user", "content": "Fix the automatic cloud sync queue again and make retries easier to understand"},
        {"timestamp": "2026-07-04T09:18:00Z", "role": "assistant", "content": "Retry state now lives with each queue item."},
        {"timestamp": "2026-07-05T08:50:00Z", "role": "user", "content": "The cloud sync is too complex. Remove it and keep all user data local"},
        {"timestamp": "2026-07-05T09:00:00Z", "role": "assistant", "content": "I removed the automatic sync path."},
        {"timestamp": "2026-07-06T09:40:00Z", "role": "user", "content": "Add an explicit JSON export so users control when data leaves the app"},
        {"timestamp": "2026-07-06T09:50:00Z", "role": "assistant", "content": "Export is implemented and remains local."},
        {"timestamp": "2026-07-08T08:45:00Z", "role": "user", "content": "Add tests for the local store and JSON export"},
        {"timestamp": "2026-07-08T08:55:00Z", "role": "assistant", "content": "The storage and export paths now have tests."},
    ]
    transcript.write_text("\n".join(json.dumps(row) for row in transcript_rows), encoding="utf-8")
    return transcript


def main() -> int:
    context = {
        "zh": {
            "role": "产品方向判断、核心实现与发布验证",
            "outcome": "发布 PocketTasks 1.0，保留本地任务存储和显式 JSON 导出，让用户决定数据何时离开设备。",
            "key_decision": "在同步队列与重试逻辑持续复杂化后，撤销自动云同步，改为用户主动导出。",
            "summary": "从复杂的自动云同步，回到用户可控的本地优先。",
            "resume_bullets": [
                "独立完成 PocketTasks 从方案试验到 1.0 发布，在发现自动云同步持续引入队列与重试复杂度后，主动回滚并改为显式 JSON 导出。",
                "为本地存储与导出路径补充测试和 CI，把关键方向调整沉淀为架构决策记录。",
            ],
        },
        "en": {
            "role": "product direction, core implementation, and release validation",
            "outcome": "shipped PocketTasks 1.0 with local task storage and explicit JSON export, leaving users in control of when data leaves the device.",
            "key_decision": "removed automatic cloud sync after queue and retry complexity kept growing, replacing it with user-initiated export.",
            "summary": "From complex automatic cloud sync back to a user-controlled local-first product.",
            "resume_bullets": [
                "Took PocketTasks from early experiments to a 1.0 release; reversed automatic cloud sync when queue and retry complexity grew, replacing it with explicit JSON export.",
                "Added tests and CI for local storage and export, then captured the direction change in an architecture decision record.",
            ],
        },
    }
    with tempfile.TemporaryDirectory() as directory:
        repo = Path(directory) / "PocketTasks"
        repo.mkdir()
        transcript = build_demo_repository(repo)
        datasets = {}
        for language in ("en", "zh"):
            data = build_story.build_evidence(repo, [transcript], language, "PocketTasks", context)
            data["generated_at"] = "2026-08-29T00:00:00+00:00"
            datasets[language] = data
        build_story.write_outputs(
            datasets["en"],
            DEMO_OUTPUT / "en",
            {"en": "report.html", "zh": "../zh/report.html"},
        )
        build_story.write_outputs(
            datasets["zh"],
            DEMO_OUTPUT / "zh",
            {"en": "../en/report.html", "zh": "report.html"},
        )
    print(f"Demo reports created: {DEMO_OUTPUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
