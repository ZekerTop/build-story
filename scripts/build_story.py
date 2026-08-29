#!/usr/bin/env python3
"""BuildStory: local, evidence-first project retrospective generator.

The script uses only the Python standard library and Git. It writes JSON,
Markdown, and self-contained HTML reports without modifying source files.
"""

from __future__ import annotations

import argparse
import collections
import datetime as dt
import html
import json
import math
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable


VERSION = "0.1.0"
MAX_TRANSCRIPT_BYTES = 20 * 1024 * 1024
MAX_TRANSCRIPT_EVENTS = 20_000
SESSION_GAP_HOURS = 2.0
TRANSCRIPT_ACTIVE_GAP_MINUTES = 30.0


COPY = {
    "en": {
        "tagline": "See how you built it, not just what you built.",
        "generated": "Generated locally from project evidence",
        "coverage": "Evidence coverage",
        "timeline": "Project life line",
        "timeline_intro": "A navigable history of changes, grouped by observable intent signals.",
        "friction": "Where the project fought back",
        "friction_intro": "High-change areas and loop candidates. These are prompts for review, not verdicts.",
        "attention": "Attention map",
        "attention_intro": "Estimated from change density and activity timestamps. Invisible thinking time is not captured.",
        "profile": "Evidence-backed profile",
        "profile_intro": "Separate dimensions, never one total score. Each score describes repository evidence, not personal worth.",
        "proof": "What this project proves",
        "proof_intro": "Evidence cards that can support a retrospective, portfolio, resume, or interview story.",
        "method": "Method and limits",
        "commits": "commits",
        "files": "files",
        "days": "calendar days",
        "hours": "estimated active hours",
        "authors": "authors",
        "added": "lines added",
        "deleted": "lines deleted",
        "confidence": "confidence",
        "high": "high",
        "medium": "medium",
        "low": "low",
        "none": "No signal found",
        "all": "All",
        "source_git": "Git history",
        "source_sessions": "authorized session transcripts",
        "git_limit": "Git records saved changes, not all thinking, experiments, or uncommitted work.",
        "session_limit": "Transcript analysis stores only short excerpts used to explain repeated-prompt candidates.",
        "resume_prompt": "Add the verified user or business outcome before using this as a resume bullet.",
    },
    "zh": {
        "tagline": "不只看你做出了什么，更看你是怎么做到的。",
        "generated": "基于本地项目证据生成",
        "coverage": "证据覆盖范围",
        "timeline": "项目生命线",
        "timeline_intro": "按照可观察到的变更信号，重建可浏览的开发历程。",
        "friction": "项目在哪里卡住了",
        "friction_intro": "高频变更区域与循环候选。它们用于复盘，不是对人的判决。",
        "attention": "注意力地图",
        "attention_intro": "根据变更密度和活动时间估算，无法覆盖离线思考时间。",
        "profile": "基于证据的能力画像",
        "profile_intro": "只看分维度画像，不给一个虚假的总分。分数描述仓库证据，不评价人的价值。",
        "proof": "这个项目证明了什么",
        "proof_intro": "可用于项目复盘、作品集、简历和面试故事的证据卡片。",
        "method": "方法与限制",
        "commits": "次提交",
        "files": "个文件",
        "days": "个自然日",
        "hours": "小时估算活跃时间",
        "authors": "位贡献者",
        "added": "行新增",
        "deleted": "行删除",
        "confidence": "置信度",
        "high": "高",
        "medium": "中",
        "low": "低",
        "none": "未发现信号",
        "all": "全部",
        "source_git": "Git 历史",
        "source_sessions": "已授权的会话记录",
        "git_limit": "Git 只记录已保存的变更，无法覆盖全部思考、实验和未提交工作。",
        "session_limit": "会话分析只保存用于解释重复提示候选的短摘录，不复制完整对话。",
        "resume_prompt": "用于简历前，请补充经过验证的用户结果或业务结果。",
    },
}


CATEGORY_LABELS = {
    "en": {
        "foundation": "Foundation",
        "feature": "Feature",
        "fix": "Fix",
        "refactor": "Refactor",
        "validation": "Validation",
        "documentation": "Documentation",
        "delivery": "Delivery",
        "other": "Other",
    },
    "zh": {
        "foundation": "搭建",
        "feature": "功能",
        "fix": "修复",
        "refactor": "重构",
        "validation": "验证",
        "documentation": "文档",
        "delivery": "交付",
        "other": "其他",
    },
}


DIMENSION_LABELS = {
    "en": {
        "delivery": "Delivery evidence",
        "validation": "Validation discipline",
        "traceability": "Change traceability",
        "iteration": "Iteration control",
        "learning": "Learning capture",
    },
    "zh": {
        "delivery": "交付证据",
        "validation": "验证纪律",
        "traceability": "变更可追溯性",
        "iteration": "迭代控制",
        "learning": "经验沉淀",
    },
}


GENERIC_SUBJECTS = {
    "update",
    "updates",
    "changes",
    "fix",
    "fixes",
    "wip",
    "test",
    "temp",
    "misc",
    "cleanup",
    "修改",
    "更新",
    "修复",
    "调整",
    "测试",
}


STOPWORDS = {
    "a",
    "an",
    "and",
    "the",
    "to",
    "for",
    "of",
    "in",
    "on",
    "with",
    "from",
    "this",
    "that",
    "feat",
    "fix",
    "chore",
    "refactor",
    "docs",
    "test",
    "update",
    "add",
    "added",
    "support",
}


@dataclass
class Commit:
    commit_hash: str
    timestamp: dt.datetime
    author: str
    subject: str
    files: list[dict[str, Any]]
    category: str = "other"

    @property
    def additions(self) -> int:
        return sum(item["added"] for item in self.files)

    @property
    def deletions(self) -> int:
        return sum(item["deleted"] for item in self.files)


def run(command: list[str], cwd: Path, check: bool = True) -> str:
    result = subprocess.run(
        command,
        cwd=str(cwd),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if check and result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "Command failed: " + " ".join(command))
    return result.stdout


def git(repo: Path, *args: str, check: bool = True) -> str:
    return run(["git", *args], repo, check=check)


def parse_datetime(value: Any) -> dt.datetime | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        number = float(value)
        if number > 10_000_000_000:
            number /= 1000.0
        try:
            return dt.datetime.fromtimestamp(number, tz=dt.timezone.utc)
        except (OverflowError, OSError, ValueError):
            return None
    text = str(value).strip()
    if not text:
        return None
    text = text.replace("Z", "+00:00")
    try:
        parsed = dt.datetime.fromisoformat(text)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=dt.timezone.utc)
        return parsed
    except ValueError:
        return None


def category_for(subject: str, paths: Iterable[str]) -> str:
    lower = subject.lower()
    joined_paths = " ".join(paths).lower()
    tests_path = re.search(r"(^|/)(test|tests|spec|specs|__tests__)(/|$)", joined_paths)
    if re.search(r"\b(revert|rollback|back out|backout)\b|回滚|撤销", lower):
        return "fix"
    groups = [
        ("delivery", r"\b(release|publish|deploy|version|ship)\b|发布|部署|上线"),
        ("validation", r"\b(test|tests|testing|ci|lint|verify|benchmark)\b|测试|验证|校验"),
        ("documentation", r"\b(doc|docs|readme|guide|documentation)\b|文档|说明|指南"),
        ("refactor", r"\b(refactor|cleanup|simplify|rename|restructure)\b|重构|清理|简化"),
        ("fix", r"\b(fix|bug|repair|resolve|patch|hotfix)\b|修复|修正|解决"),
        ("foundation", r"\b(init|initial|bootstrap|scaffold|setup|configure|config)\b|初始化|搭建|配置"),
        ("feature", r"\b(feat|feature|add|implement|create|support|introduce)\b|新增|实现|增加|支持"),
    ]
    for name, pattern in groups:
        if re.search(pattern, lower):
            return name
    if tests_path or ".github/workflows" in joined_paths:
        return "validation"
    if any(path.lower().endswith((".md", ".rst")) for path in paths):
        return "documentation"
    return "other"


def parse_commits(repo: Path) -> list[Commit]:
    marker = "@@BUILDSTORY_COMMIT@@"
    output = git(
        repo,
        "log",
        "--reverse",
        "--date=iso-strict",
        f"--format={marker}%H%x1f%aI%x1f%an%x1f%s",
        "--numstat",
        "HEAD",
    )
    commits: list[Commit] = []
    current: Commit | None = None
    for raw in output.splitlines():
        if raw.startswith(marker):
            if current is not None:
                current.category = category_for(current.subject, [item["path"] for item in current.files])
                commits.append(current)
            parts = raw[len(marker) :].split("\x1f", 3)
            if len(parts) != 4:
                continue
            timestamp = parse_datetime(parts[1]) or dt.datetime.now(dt.timezone.utc)
            current = Commit(parts[0], timestamp, parts[2], parts[3], [])
            continue
        if current is None or not raw.strip():
            continue
        parts = raw.split("\t", 2)
        if len(parts) != 3:
            continue
        added = int(parts[0]) if parts[0].isdigit() else 0
        deleted = int(parts[1]) if parts[1].isdigit() else 0
        current.files.append({"path": parts[2], "added": added, "deleted": deleted})
    if current is not None:
        current.category = category_for(current.subject, [item["path"] for item in current.files])
        commits.append(current)
    return commits


def normalized_topic(subject: str) -> str:
    text = re.sub(r"^[a-z]+(?:\([^)]*\))?[!:] ?", "", subject.lower()).strip()
    tokens = re.findall(r"[a-z0-9_]+|[\u4e00-\u9fff]{2,}", text)
    tokens = [token for token in tokens if token not in STOPWORDS and len(token) > 1]
    return " ".join(tokens[:4])


def file_statistics(commits: list[Commit]) -> dict[str, dict[str, Any]]:
    stats: dict[str, dict[str, Any]] = collections.defaultdict(
        lambda: {"commits": 0, "added": 0, "deleted": 0, "hashes": []}
    )
    for commit in commits:
        for item in commit.files:
            row = stats[item["path"]]
            row["commits"] += 1
            row["added"] += item["added"]
            row["deleted"] += item["deleted"]
            row["hashes"].append(commit.commit_hash[:8])
    for row in stats.values():
        gross = row["added"] + row["deleted"]
        row["gross"] = gross
        row["rework_ratio"] = round((2 * min(row["added"], row["deleted"]) / gross), 3) if gross else 0.0
        row["friction_score"] = round(
            math.log1p(gross) * row["rework_ratio"] * (1 + min(row["commits"], 20) / 10), 3
        )
    return dict(stats)


def likely_generated(path: str) -> bool:
    lower = path.lower()
    name = Path(lower).name
    return (
        name in {"package-lock.json", "pnpm-lock.yaml", "yarn.lock", "poetry.lock", "uv.lock"}
        or lower.startswith(("dist/", "build/", "vendor/", "generated/"))
        or "/dist/" in lower
        or "/vendor/" in lower
    )


def build_friction(file_stats: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for path, stat in file_stats.items():
        if likely_generated(path) or stat["commits"] < 3 or stat["gross"] < 8:
            continue
        rows.append({"path": path, **stat})
    rows.sort(key=lambda row: (row["friction_score"], row["gross"]), reverse=True)
    return rows[:10]


def build_loops(commits: list[Commit], friction: list[dict[str, Any]], language: str) -> list[dict[str, Any]]:
    loops: list[dict[str, Any]] = []
    for commit in commits:
        if re.search(r"\b(revert|rollback|back out|backout)\b|回滚|撤销", commit.subject.lower()):
            loops.append(
                {
                    "type": "explicit-reversal",
                    "title": commit.subject,
                    "detail": f"{commit.timestamp.date().isoformat()} · {commit.commit_hash[:8]}",
                    "confidence": "high",
                }
            )

    topic_groups: dict[str, list[Commit]] = collections.defaultdict(list)
    for commit in commits:
        topic = normalized_topic(commit.subject)
        if topic:
            topic_groups[topic].append(commit)
    for topic, group in topic_groups.items():
        if len(group) >= 3:
            text = (
                f"The topic appeared in {len(group)} commits from {group[0].timestamp.date()} to {group[-1].timestamp.date()}."
                if language == "en"
                else f"该主题在 {group[0].timestamp.date()} 至 {group[-1].timestamp.date()} 之间出现于 {len(group)} 次提交。"
            )
            loops.append({"type": "repeated-topic", "title": topic, "detail": text, "confidence": "medium"})

    for row in friction[:5]:
        if row["commits"] >= 5 and row["rework_ratio"] >= 0.35:
            text = (
                f"Changed in {row['commits']} commits with {row['rework_ratio']:.0%} bidirectional churn."
                if language == "en"
                else f"在 {row['commits']} 次提交中被修改，双向变更比例约为 {row['rework_ratio']:.0%}。"
            )
            loops.append(
                {"type": "high-churn-file", "title": row["path"], "detail": text, "confidence": "medium"}
            )
    return loops[:12]


def git_time_estimate(commits: list[Commit]) -> dict[str, Any]:
    if not commits:
        return {"hours": 0.0, "sessions": 0, "source": "git", "confidence": "low"}
    timestamps = sorted(commit.timestamp for commit in commits)
    total_hours = 0.25
    sessions = 1
    for previous, current in zip(timestamps, timestamps[1:]):
        gap = max(0.0, (current - previous).total_seconds() / 3600)
        if gap > SESSION_GAP_HOURS:
            sessions += 1
            total_hours += 0.25
        else:
            total_hours += gap
    return {"hours": round(total_hours, 1), "sessions": sessions, "source": "git", "confidence": "low"}


def iter_transcript_files(paths: list[Path]) -> Iterable[Path]:
    allowed = {".jsonl", ".json", ".txt", ".md"}
    seen: set[Path] = set()
    for source in paths:
        candidates = [source] if source.is_file() else source.rglob("*") if source.is_dir() else []
        for candidate in candidates:
            try:
                resolved = candidate.resolve()
            except OSError:
                continue
            if resolved in seen or not resolved.is_file() or resolved.suffix.lower() not in allowed:
                continue
            try:
                if resolved.stat().st_size > MAX_TRANSCRIPT_BYTES:
                    continue
            except OSError:
                continue
            seen.add(resolved)
            yield resolved


def flatten_text(value: Any, depth: int = 0) -> str:
    if depth > 4 or value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        parts = [flatten_text(item, depth + 1) for item in value]
        return " ".join(part for part in parts if part)
    if isinstance(value, dict):
        for key in ("text", "content", "message", "prompt", "input", "output"):
            if key in value:
                text = flatten_text(value[key], depth + 1)
                if text:
                    return text
    return ""


def event_from_object(value: Any, source: str) -> dict[str, Any] | None:
    if not isinstance(value, dict):
        return None
    timestamp = None
    for key in ("timestamp", "created_at", "createdAt", "time", "ts", "date"):
        if key in value:
            timestamp = parse_datetime(value[key])
            if timestamp:
                break
    role = str(value.get("role") or value.get("type") or value.get("kind") or "unknown")
    text = re.sub(r"\s+", " ", flatten_text(value)).strip()
    if not timestamp and not text:
        return None
    return {"timestamp": timestamp, "role": role.lower(), "text": text[:2000], "source": source}


def read_transcript_events(paths: list[Path]) -> tuple[list[dict[str, Any]], list[str]]:
    events: list[dict[str, Any]] = []
    files: list[str] = []
    for path in iter_transcript_files(paths):
        files.append(path.name)
        try:
            if path.suffix.lower() == ".jsonl":
                values = []
                with path.open("r", encoding="utf-8", errors="replace") as handle:
                    for line in handle:
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            values.append(json.loads(line))
                        except json.JSONDecodeError:
                            values.append({"text": line})
            elif path.suffix.lower() == ".json":
                parsed = json.loads(path.read_text(encoding="utf-8", errors="replace"))
                values = parsed if isinstance(parsed, list) else [parsed]
            else:
                values = [{"text": line} for line in path.read_text(encoding="utf-8", errors="replace").splitlines()]
        except (OSError, json.JSONDecodeError):
            continue
        for value in values:
            event = event_from_object(value, path.name)
            if event:
                events.append(event)
                if len(events) >= MAX_TRANSCRIPT_EVENTS:
                    return events, files
    return events, files


def text_signature(text: str) -> set[str]:
    words = re.findall(r"[a-z0-9_]+|[\u4e00-\u9fff]{2,}", text.lower())
    return {word for word in words if word not in STOPWORDS and len(word) > 1}


def analyze_transcripts(events: list[dict[str, Any]], files: list[str], language: str) -> dict[str, Any]:
    timestamped = sorted((event for event in events if event["timestamp"]), key=lambda event: event["timestamp"])
    active_seconds = 0.0
    for previous, current in zip(timestamped, timestamped[1:]):
        gap = max(0.0, (current["timestamp"] - previous["timestamp"]).total_seconds())
        active_seconds += min(gap, TRANSCRIPT_ACTIVE_GAP_MINUTES * 60)

    user_events = [
        event
        for event in events
        if any(token in event["role"] for token in ("user", "human", "prompt")) and len(event["text"]) >= 24
    ]
    repeats: list[dict[str, Any]] = []
    used: set[int] = set()
    signatures = [text_signature(event["text"]) for event in user_events]
    for i, left in enumerate(user_events):
        if i in used or not signatures[i]:
            continue
        matches = [i]
        for j in range(i + 1, min(len(user_events), i + 80)):
            if not signatures[j]:
                continue
            score = len(signatures[i] & signatures[j]) / max(1, len(signatures[i] | signatures[j]))
            if score >= 0.62:
                matches.append(j)
        if len(matches) >= 2:
            used.update(matches)
            excerpt = re.sub(r"\s+", " ", left["text"])[:150]
            detail = (
                f"A similar request appeared {len(matches)} times. Confirm whether this was productive refinement or a blocked loop."
                if language == "en"
                else f"相似请求出现了 {len(matches)} 次。需要确认这是有效细化，还是受阻循环。"
            )
            repeats.append({"excerpt": excerpt, "count": len(matches), "detail": detail, "confidence": "medium"})

    error_events = sum(
        1
        for event in events
        if re.search(r"\b(error|failed|failure|exception|denied|timeout)\b|错误|失败|异常|拒绝|超时", event["text"], re.I)
    )
    return {
        "files": files,
        "events": len(events),
        "timestamped_events": len(timestamped),
        "estimated_active_hours": round(active_seconds / 3600, 1),
        "confidence": "medium" if len(timestamped) >= 10 else "low",
        "repeated_prompts": repeats[:10],
        "error_signals": error_events,
    }


def tracked_files(repo: Path) -> list[str]:
    output = git(repo, "ls-files", "-z")
    return [item for item in output.split("\0") if item]


def project_signals(repo: Path, files: list[str]) -> dict[str, Any]:
    lower = {item.lower() for item in files}
    names = {Path(item).name.lower() for item in files}
    has_readme = any(name.startswith("readme") for name in names)
    has_license = any(name.startswith("license") or name == "copying" for name in names)
    manifests = {
        "package.json",
        "pyproject.toml",
        "setup.py",
        "cargo.toml",
        "go.mod",
        "pom.xml",
        "build.gradle",
        "gemfile",
    }
    has_manifest = bool(names & manifests)
    has_tests = any(re.search(r"(^|/)(test|tests|spec|specs|__tests__)(/|$)", path.lower()) for path in files)
    has_ci = any(path.startswith(".github/workflows/") for path in lower)
    has_docs = any(path.startswith("docs/") for path in lower) or any(name in names for name in {"contributing.md", "architecture.md"})
    has_changelog = any(name.startswith("changelog") for name in names)
    has_adr = any("/adr/" in f"/{path}" or path.startswith("adr/") for path in lower)
    has_lint = bool(names & {"eslint.config.js", ".eslintrc", "ruff.toml", ".pylintrc", "biome.json"})
    tags = [line for line in git(repo, "tag", "--list", check=False).splitlines() if line.strip()]
    return {
        "readme": has_readme,
        "license": has_license,
        "manifest": has_manifest,
        "tests": has_tests,
        "ci": has_ci,
        "docs": has_docs,
        "changelog": has_changelog,
        "adr": has_adr,
        "lint": has_lint,
        "tags": tags,
    }


def score_dimensions(
    commits: list[Commit], files: list[str], signals: dict[str, Any], friction: list[dict[str, Any]], loops: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    delivery_score = min(
        100,
        15
        + 22 * signals["readme"]
        + 15 * signals["license"]
        + 18 * signals["manifest"]
        + 15 * bool(signals["tags"])
        + 15 * signals["docs"],
    )
    delivery_evidence = [
        label
        for present, label in [
            (signals["readme"], "README"),
            (signals["license"], "license"),
            (signals["manifest"], "package manifest"),
            (bool(signals["tags"]), f"{len(signals['tags'])} Git tag(s)"),
            (signals["docs"], "project documentation"),
        ]
        if present
    ] or ["No strong delivery artifact detected"]

    validation_commits = sum(commit.category == "validation" for commit in commits)
    validation_score = min(
        100,
        8
        + 34 * signals["tests"]
        + 26 * signals["ci"]
        + min(24, validation_commits * 5)
        + 8 * signals["lint"],
    )
    validation_evidence = []
    if signals["tests"]:
        validation_evidence.append("test files")
    if signals["ci"]:
        validation_evidence.append("CI workflow")
    if signals["lint"]:
        validation_evidence.append("lint configuration")
    validation_evidence.append(f"{validation_commits} validation-related commit(s)")

    meaningful = 0
    reviewable = 0
    for commit in commits:
        normalized = re.sub(r"^[a-z]+(?:\([^)]*\))?[!:] ?", "", commit.subject.lower()).strip()
        if len(normalized) >= 10 and normalized not in GENERIC_SUBJECTS:
            meaningful += 1
        if len(commit.files) <= 12 and commit.additions + commit.deletions <= 1200:
            reviewable += 1
    divisor = max(1, len(commits))
    meaningful_ratio = meaningful / divisor
    reviewable_ratio = reviewable / divisor
    traceability_score = round(min(100, meaningful_ratio * 65 + reviewable_ratio * 35))
    traceability_evidence = [
        f"{meaningful_ratio:.0%} descriptive commit subjects",
        f"{reviewable_ratio:.0%} reviewable-size commits",
    ]

    explicit_reverts = sum(loop["type"] == "explicit-reversal" for loop in loops)
    top_rework = sum(row["rework_ratio"] for row in friction[:3]) / max(1, len(friction[:3]))
    iteration_score = round(max(0, min(100, 92 - explicit_reverts * 13 - top_rework * 34)))
    iteration_evidence = [
        f"{explicit_reverts} explicit reversal(s)",
        f"{len(friction)} high-change file candidate(s)",
        "High churn may represent productive iteration and requires review",
    ]

    learning_score = min(
        100,
        12
        + 28 * signals["readme"]
        + 18 * signals["docs"]
        + 20 * signals["changelog"]
        + 15 * signals["adr"]
        + 7 * any("retrospect" in path.lower() or "build-story" in path.lower() for path in files),
    )
    learning_evidence = [
        label
        for present, label in [
            (signals["readme"], "README"),
            (signals["docs"], "docs directory or architecture guide"),
            (signals["changelog"], "changelog"),
            (signals["adr"], "architecture decision records"),
        ]
        if present
    ] or ["No durable learning artifact detected"]

    return [
        {"key": "delivery", "score": int(delivery_score), "confidence": "high", "evidence": delivery_evidence},
        {
            "key": "validation",
            "score": int(validation_score),
            "confidence": "high" if signals["tests"] or signals["ci"] else "medium",
            "evidence": validation_evidence,
        },
        {
            "key": "traceability",
            "score": int(traceability_score),
            "confidence": "high" if len(commits) >= 8 else "medium",
            "evidence": traceability_evidence,
        },
        {
            "key": "iteration",
            "score": int(iteration_score),
            "confidence": "medium",
            "evidence": iteration_evidence,
        },
        {"key": "learning", "score": int(learning_score), "confidence": "high", "evidence": learning_evidence},
    ]


def directory_attention(file_stats: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[str, dict[str, float]] = collections.defaultdict(lambda: {"gross": 0, "commits": 0, "files": 0})
    for path, row in file_stats.items():
        if likely_generated(path):
            continue
        directory = path.split("/", 1)[0] if "/" in path else "(root)"
        groups[directory]["gross"] += row["gross"]
        groups[directory]["commits"] += row["commits"]
        groups[directory]["files"] += 1
    results = []
    for name, row in groups.items():
        score = math.log1p(row["gross"]) * (1 + math.log1p(row["commits"]))
        results.append({"area": name, **row, "attention_score": round(score, 2)})
    results.sort(key=lambda item: item["attention_score"], reverse=True)
    return results[:8]


def evidence_cards(
    project_name: str,
    commits: list[Commit],
    files: list[str],
    signals: dict[str, Any],
    attention: list[dict[str, Any]],
    language: str,
) -> list[dict[str, Any]]:
    if not commits:
        return []
    start = commits[0].timestamp.date()
    end = commits[-1].timestamp.date()
    span = max(1, (end - start).days + 1)
    cards = []
    if language == "en":
        cards.append(
            {
                "title": "Sustained delivery",
                "evidence": f"{len(commits)} commits across {span} calendar days and {len(files)} tracked files.",
                "career": f"Built and iterated on {project_name} across {len(files)} tracked files over {span} calendar days; add the verified user or business outcome.",
            }
        )
    else:
        cards.append(
            {
                "title": "持续交付",
                "evidence": f"在 {span} 个自然日内完成 {len(commits)} 次提交，涉及 {len(files)} 个受版本控制的文件。",
                "career": f"在 {span} 个自然日内持续构建并迭代 {project_name}，覆盖 {len(files)} 个受版本控制的文件；请补充经过验证的用户或业务结果。",
            }
        )
    if attention:
        top = ", ".join(row["area"] for row in attention[:3])
        cards.append(
            {
                "title": "Core implementation areas" if language == "en" else "核心实现区域",
                "evidence": (
                    f"Most change activity concentrated in: {top}."
                    if language == "en"
                    else f"主要变更活动集中在：{top}。"
                ),
                "career": (
                    f"Implemented and refined the project's core areas across {top}; add the concrete technical decision and outcome."
                    if language == "en"
                    else f"实现并持续完善项目核心区域 {top}；请补充关键技术决策和最终结果。"
                ),
            }
        )
    if signals["tests"] or signals["ci"]:
        pieces = []
        if signals["tests"]:
            pieces.append("tests")
        if signals["ci"]:
            pieces.append("CI")
        joined = " and ".join(pieces)
        cards.append(
            {
                "title": "Validation infrastructure" if language == "en" else "验证基础设施",
                "evidence": (
                    f"The repository contains {joined}."
                    if language == "en"
                    else f"仓库中已包含 {' 和 '.join(pieces)}。"
                ),
                "career": (
                    f"Added {joined} to make changes verifiable; add the confirmed reliability or release outcome."
                    if language == "en"
                    else f"通过 {' 和 '.join(pieces)} 让变更可验证；请补充经过确认的稳定性或发布结果。"
                ),
            }
        )
    return cards


def build_evidence(repo: Path, session_paths: list[Path], language: str, project_name: str | None) -> dict[str, Any]:
    inside = git(repo, "rev-parse", "--is-inside-work-tree", check=False).strip()
    if inside != "true":
        raise RuntimeError(f"Not a Git repository: {repo}")
    root = Path(git(repo, "rev-parse", "--show-toplevel").strip()).resolve()
    commits = parse_commits(root)
    if not commits:
        raise RuntimeError("The repository has no commits reachable from HEAD.")
    files = tracked_files(root)
    file_stats = file_statistics(commits)
    friction = build_friction(file_stats)
    loops = build_loops(commits, friction, language)
    git_time = git_time_estimate(commits)
    transcript_events, transcript_files = read_transcript_events(session_paths) if session_paths else ([], [])
    transcript_analysis = analyze_transcripts(transcript_events, transcript_files, language) if transcript_files else None
    time_estimate = git_time.copy()
    if transcript_analysis and transcript_analysis["timestamped_events"] >= 10:
        time_estimate = {
            "hours": transcript_analysis["estimated_active_hours"],
            "sessions": None,
            "source": "transcripts",
            "confidence": transcript_analysis["confidence"],
        }
        for repeat in transcript_analysis["repeated_prompts"]:
            loops.append(
                {
                    "type": "repeated-prompt",
                    "title": repeat["excerpt"],
                    "detail": repeat["detail"],
                    "confidence": repeat["confidence"],
                }
            )
    signals = project_signals(root, files)
    dimensions = score_dimensions(commits, files, signals, friction, loops)
    attention = directory_attention(file_stats)
    name = project_name or root.name
    authors = sorted({commit.author for commit in commits})
    categories = collections.Counter(commit.category for commit in commits)
    start = commits[0].timestamp
    end = commits[-1].timestamp
    span_days = max(1, (end.date() - start.date()).days + 1)
    branch = git(root, "rev-parse", "--abbrev-ref", "HEAD", check=False).strip() or "HEAD"

    timeline = [
        {
            "hash": commit.commit_hash,
            "short_hash": commit.commit_hash[:8],
            "timestamp": commit.timestamp.isoformat(),
            "date": commit.timestamp.date().isoformat(),
            "author": commit.author,
            "subject": commit.subject,
            "category": commit.category,
            "files": len(commit.files),
            "added": commit.additions,
            "deleted": commit.deletions,
        }
        for commit in commits
    ]
    source_list = ["git"] + (["transcripts"] if transcript_files else [])
    return {
        "schema_version": "1.0",
        "generator_version": VERSION,
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "language": language,
        "project": {
            "name": name,
            "path": root.name,
            "branch": branch,
            "start": start.isoformat(),
            "end": end.isoformat(),
            "calendar_days": span_days,
        },
        "coverage": {
            "sources": source_list,
            "commit_count": len(commits),
            "tracked_files": len(files),
            "authors": authors,
            "transcript_files": transcript_files,
            "limitations": [COPY[language]["git_limit"]]
            + ([COPY[language]["session_limit"]] if transcript_files else []),
        },
        "metrics": {
            "commits": len(commits),
            "files": len(files),
            "authors": len(authors),
            "calendar_days": span_days,
            "lines_added": sum(commit.additions for commit in commits),
            "lines_deleted": sum(commit.deletions for commit in commits),
            "category_counts": dict(categories),
            "time_estimate": time_estimate,
        },
        "timeline": timeline,
        "friction_zones": friction,
        "loop_candidates": loops[:15],
        "attention_areas": attention,
        "dimensions": dimensions,
        "signals": signals,
        "transcripts": transcript_analysis,
        "evidence_cards": evidence_cards(name, commits, files, signals, attention, language),
    }


def confidence_label(value: str, language: str) -> str:
    return COPY[language].get(value, value)


def render_markdown(data: dict[str, Any]) -> str:
    language = data["language"]
    c = COPY[language]
    p = data["project"]
    m = data["metrics"]
    lines = [
        f"# BuildStory: {p['name']}",
        "",
        f"> {c['tagline']}",
        "",
        f"- {m['commits']} {c['commits']}",
        f"- {m['files']} {c['files']}",
        f"- {m['calendar_days']} {c['days']}",
        f"- {m['time_estimate']['hours']} {c['hours']} ({c['confidence']}: {confidence_label(m['time_estimate']['confidence'], language)})",
        "",
        f"## {c['timeline']}",
        "",
    ]
    for event in data["timeline"]:
        label = CATEGORY_LABELS[language][event["category"]]
        lines.append(f"- `{event['date']}` **{label}** · {event['subject']} (`{event['short_hash']}`)")
    lines.extend(["", f"## {c['friction']}", ""])
    if data["friction_zones"]:
        for item in data["friction_zones"]:
            lines.append(
                f"- `{item['path']}` · {item['commits']} commits · {item['added']}+ / {item['deleted']}- · rework signal {item['rework_ratio']:.0%}"
            )
    else:
        lines.append(f"- {c['none']}")
    lines.extend(["", "### Loop candidates", ""])
    if data["loop_candidates"]:
        for item in data["loop_candidates"]:
            lines.append(
                f"- **{item['title']}** · {item['detail']} ({c['confidence']}: {confidence_label(item['confidence'], language)})"
            )
    else:
        lines.append(f"- {c['none']}")
    lines.extend(["", f"## {c['profile']}", ""])
    for item in data["dimensions"]:
        lines.append(
            f"- **{DIMENSION_LABELS[language][item['key']]}: {item['score']}/100** ({c['confidence']}: {confidence_label(item['confidence'], language)})"
        )
        for evidence in item["evidence"]:
            lines.append(f"  - {evidence}")
    lines.extend(["", f"## {c['proof']}", ""])
    for card in data["evidence_cards"]:
        lines.extend([f"### {card['title']}", "", card["evidence"], "", f"> {card['career']}", ""])
    lines.extend([f"## {c['method']}", ""])
    for limitation in data["coverage"]["limitations"]:
        lines.append(f"- {limitation}")
    return "\n".join(lines).rstrip() + "\n"


def esc(value: Any) -> str:
    return html.escape(str(value), quote=True)


def render_html(data: dict[str, Any]) -> str:
    language = data["language"]
    c = COPY[language]
    p = data["project"]
    m = data["metrics"]
    category_labels = CATEGORY_LABELS[language]

    filters = [
        f'<button class="filter is-active" data-filter="all">{esc(c["all"])}</button>'
    ] + [
        f'<button class="filter" data-filter="{key}">{esc(category_labels[key])} <span>{count}</span></button>'
        for key, count in sorted(m["category_counts"].items())
    ]
    timeline_rows = []
    for event in data["timeline"][-160:]:
        timeline_rows.append(
            f'''<article class="event" data-category="{esc(event['category'])}">
  <div class="event-date">{esc(event['date'])}</div>
  <div class="event-mark" aria-hidden="true"></div>
  <div class="event-body">
    <div class="event-meta"><span>{esc(category_labels[event['category']])}</span><code>{esc(event['short_hash'])}</code></div>
    <h3>{esc(event['subject'])}</h3>
    <p>{event['files']} files · <strong>+{event['added']}</strong> / -{event['deleted']}</p>
  </div>
</article>'''
        )

    friction_rows = []
    for index, item in enumerate(data["friction_zones"][:8], start=1):
        friction_rows.append(
            f'''<div class="friction-row">
  <div class="rank">{index:02d}</div>
  <div><code>{esc(item['path'])}</code><p>{item['commits']} commits · +{item['added']} / -{item['deleted']}</p></div>
  <div class="ratio"><strong>{item['rework_ratio']:.0%}</strong><span>{'bidirectional churn' if language == 'en' else '双向变更信号'}</span></div>
</div>'''
        )
    if not friction_rows:
        friction_rows.append(f'<p class="empty">{esc(c["none"])}</p>')

    loop_rows = []
    for item in data["loop_candidates"]:
        loop_rows.append(
            f'''<details class="loop">
  <summary><span class="confidence {esc(item['confidence'])}">{esc(confidence_label(item['confidence'], language))}</span><strong>{esc(item['title'])}</strong></summary>
  <p>{esc(item['detail'])}</p>
</details>'''
        )
    if not loop_rows:
        loop_rows.append(f'<p class="empty">{esc(c["none"])}</p>')

    attention_rows = []
    maximum = max((item["attention_score"] for item in data["attention_areas"]), default=1)
    for item in data["attention_areas"]:
        relative = item["attention_score"] / maximum
        attention_rows.append(
            f'''<div class="attention-row">
  <strong>{esc(item['area'])}</strong>
  <div class="attention-dots" aria-label="relative attention {relative:.0%}">{''.join('<i></i>' for _ in range(max(1, round(relative * 10))))}</div>
  <span>{int(item['gross'])} Δ · {int(item['commits'])} touches</span>
</div>'''
        )

    dimension_rows = []
    for item in data["dimensions"]:
        evidence = "".join(f"<li>{esc(line)}</li>" for line in item["evidence"])
        dimension_rows.append(
            f'''<div class="dimension">
  <div class="dimension-heading"><h3>{esc(DIMENSION_LABELS[language][item['key']])}</h3><strong>{item['score']}</strong></div>
  <div class="score-axis" aria-label="{item['score']} out of 100"><span style="left:{item['score']}%"></span></div>
  <div class="dimension-foot"><span class="confidence {esc(item['confidence'])}">{esc(c['confidence'])}: {esc(confidence_label(item['confidence'], language))}</span><details><summary>{'Evidence' if language == 'en' else '查看证据'}</summary><ul>{evidence}</ul></details></div>
</div>'''
        )

    card_rows = []
    for card in data["evidence_cards"]:
        card_rows.append(
            f'''<article class="proof-card">
  <h3>{esc(card['title'])}</h3>
  <p>{esc(card['evidence'])}</p>
  <blockquote>{esc(card['career'])}</blockquote>
</article>'''
        )

    sources = ", ".join(
        c["source_git"] if source == "git" else c["source_sessions"] for source in data["coverage"]["sources"]
    )
    limitations = "".join(f"<li>{esc(item)}</li>" for item in data["coverage"]["limitations"])
    generated_date = data["generated_at"][:10]
    source_data = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")

    return f'''<!doctype html>
<html lang="{language}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="light">
<title>BuildStory · {esc(p['name'])}</title>
<style>
:root {{ --ink:#171717; --muted:#6f6f6f; --paper:#f4f2ed; --surface:#fff; --line:#d8d4cb; --accent:#f05a28; --radius:14px; }}
* {{ box-sizing:border-box; }}
html {{ scroll-behavior:smooth; }}
body {{ margin:0; color:var(--ink); background:var(--paper); font-family:ui-sans-serif,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif; line-height:1.5; }}
button {{ font:inherit; }}
code {{ font-family:ui-monospace,SFMono-Regular,Menlo,monospace; overflow-wrap:anywhere; }}
.shell {{ width:min(1180px,calc(100% - 40px)); margin:0 auto; }}
.masthead {{ min-height:78dvh; padding:28px 0 64px; display:grid; grid-template-rows:auto 1fr auto; border-bottom:1px solid var(--line); }}
.nav {{ display:flex; align-items:center; justify-content:space-between; gap:20px; }}
.wordmark {{ font-weight:850; letter-spacing:-.04em; font-size:20px; }}
.wordmark i {{ color:var(--accent); font-style:normal; }}
.nav-meta {{ color:var(--muted); font-size:13px; }}
.hero {{ align-self:center; display:grid; grid-template-columns:minmax(0,1.45fr) minmax(260px,.55fr); gap:8vw; align-items:end; padding:54px 0; }}
.kicker {{ color:var(--accent); font:700 12px/1 ui-monospace,SFMono-Regular,Menlo,monospace; letter-spacing:.14em; text-transform:uppercase; }}
h1 {{ margin:18px 0 20px; max-width:12ch; font-size:clamp(54px,9vw,132px); line-height:.88; letter-spacing:-.075em; }}
.tagline {{ margin:0; max-width:44ch; font-size:clamp(18px,2.1vw,28px); line-height:1.25; color:#3b3b3b; }}
.coverage {{ padding:18px 0 0 20px; border-left:3px solid var(--accent); }}
.coverage span {{ display:block; color:var(--muted); font-size:12px; text-transform:uppercase; letter-spacing:.1em; }}
.coverage strong {{ display:block; margin-top:8px; font-size:18px; }}
.stats {{ display:grid; grid-template-columns:repeat(4,1fr); border-top:1px solid var(--line); }}
.stat {{ padding:24px 18px 0 0; }}
.stat strong {{ display:block; font-size:clamp(30px,4vw,56px); letter-spacing:-.06em; }}
.stat span {{ color:var(--muted); font-size:13px; }}
main {{ background:var(--surface); }}
.section {{ padding:96px 0; border-bottom:1px solid var(--line); }}
.section-head {{ max-width:700px; margin-bottom:48px; }}
.section-head h2 {{ margin:0 0 12px; font-size:clamp(38px,6vw,74px); line-height:.95; letter-spacing:-.055em; }}
.section-head p {{ margin:0; color:var(--muted); font-size:18px; }}
.filters {{ display:flex; gap:8px; flex-wrap:wrap; margin-bottom:34px; }}
.filter {{ border:1px solid var(--line); background:transparent; color:var(--ink); padding:8px 12px; border-radius:9px; cursor:pointer; }}
.filter span {{ color:var(--muted); margin-left:4px; }}
.filter:hover,.filter.is-active {{ border-color:var(--ink); background:var(--ink); color:white; }}
.filter.is-active span {{ color:#c8c8c8; }}
.timeline {{ max-width:900px; }}
.event {{ display:grid; grid-template-columns:112px 18px 1fr; gap:18px; min-height:116px; transition:opacity .2s ease; }}
.event[hidden] {{ display:none; }}
.event-date {{ padding-top:2px; color:var(--muted); font:12px/1.4 ui-monospace,SFMono-Regular,Menlo,monospace; }}
.event-mark {{ position:relative; border-left:1px solid var(--line); }}
.event-mark::before {{ content:""; position:absolute; top:3px; left:-5px; width:9px; height:9px; border-radius:50%; background:var(--surface); border:2px solid var(--accent); }}
.event-body {{ padding-bottom:30px; }}
.event-meta {{ display:flex; align-items:center; gap:10px; color:var(--accent); font-size:12px; text-transform:uppercase; letter-spacing:.08em; }}
.event-meta code {{ color:var(--muted); text-transform:none; letter-spacing:0; }}
.event h3 {{ margin:8px 0 5px; font-size:20px; letter-spacing:-.02em; }}
.event p {{ margin:0; color:var(--muted); font-size:13px; }}
.event p strong {{ color:var(--ink); }}
.friction-layout {{ display:grid; grid-template-columns:minmax(0,1.3fr) minmax(280px,.7fr); gap:70px; align-items:start; }}
.friction-row {{ display:grid; grid-template-columns:44px minmax(0,1fr) auto; gap:16px; align-items:center; padding:18px 0; border-bottom:1px solid var(--line); }}
.rank {{ color:var(--muted); font:12px ui-monospace,SFMono-Regular,Menlo,monospace; }}
.friction-row p {{ margin:5px 0 0; color:var(--muted); font-size:13px; }}
.ratio {{ text-align:right; }}
.ratio strong,.ratio span {{ display:block; }}
.ratio strong {{ font-size:24px; color:var(--accent); }}
.ratio span {{ color:var(--muted); font-size:11px; }}
.loops h3 {{ margin:0 0 18px; font-size:15px; text-transform:uppercase; letter-spacing:.08em; }}
.loop {{ border-top:1px solid var(--line); padding:14px 0; }}
.loop summary {{ cursor:pointer; list-style:none; display:grid; grid-template-columns:auto 1fr; gap:10px; align-items:start; }}
.loop summary::-webkit-details-marker {{ display:none; }}
.loop p {{ margin:10px 0 0; color:var(--muted); font-size:14px; }}
.confidence {{ display:inline-block; width:max-content; border:1px solid var(--line); border-radius:7px; padding:2px 6px; color:var(--muted); font:10px/1.4 ui-monospace,SFMono-Regular,Menlo,monospace; text-transform:uppercase; }}
.confidence.high {{ color:var(--ink); border-color:var(--ink); }}
.confidence.medium {{ color:var(--accent); border-color:var(--accent); }}
.attention-grid {{ display:grid; grid-template-columns:minmax(0,1fr) 300px; gap:70px; }}
.attention-row {{ display:grid; grid-template-columns:minmax(120px,.6fr) minmax(130px,1fr) auto; gap:18px; align-items:center; padding:16px 0; border-bottom:1px solid var(--line); }}
.attention-dots {{ display:flex; gap:5px; }}
.attention-dots i {{ width:8px; height:8px; border-radius:50%; background:var(--accent); }}
.attention-row span {{ color:var(--muted); font-size:12px; text-align:right; }}
.time-callout {{ align-self:start; padding:24px; background:var(--paper); border-radius:var(--radius); }}
.time-callout strong {{ display:block; font-size:54px; letter-spacing:-.06em; }}
.time-callout p {{ color:var(--muted); margin:8px 0 0; font-size:13px; }}
.dimensions {{ display:grid; grid-template-columns:1fr 1fr; gap:0 64px; }}
.dimension {{ padding:24px 0; border-top:1px solid var(--line); }}
.dimension-heading {{ display:flex; justify-content:space-between; align-items:baseline; gap:20px; }}
.dimension-heading h3 {{ margin:0; font-size:18px; }}
.dimension-heading strong {{ font-size:34px; letter-spacing:-.05em; }}
.score-axis {{ position:relative; height:18px; margin:16px 5px 10px; border-top:1px solid var(--line); }}
.score-axis::before,.score-axis::after {{ content:""; position:absolute; top:-4px; height:7px; border-left:1px solid var(--line); }}
.score-axis::before {{ left:0; }} .score-axis::after {{ right:0; }}
.score-axis span {{ position:absolute; top:-7px; width:13px; height:13px; border:3px solid var(--surface); outline:2px solid var(--accent); border-radius:50%; background:var(--accent); transform:translateX(-50%); }}
.dimension-foot {{ display:flex; justify-content:space-between; align-items:start; gap:18px; }}
.dimension-foot details {{ color:var(--muted); font-size:12px; text-align:right; }}
.dimension-foot summary {{ cursor:pointer; }}
.dimension-foot ul {{ max-width:300px; text-align:left; padding-left:18px; }}
.proof-list {{ display:grid; grid-template-columns:repeat(3,1fr); gap:28px; }}
.proof-card {{ padding-top:20px; border-top:3px solid var(--accent); }}
.proof-card h3 {{ margin:0 0 14px; font-size:24px; letter-spacing:-.03em; }}
.proof-card p {{ color:var(--muted); }}
.proof-card blockquote {{ margin:24px 0 0; padding:16px 0 0; border-top:1px solid var(--line); font-size:15px; }}
.method {{ display:grid; grid-template-columns:1fr 1fr; gap:80px; }}
.method h3 {{ margin-top:0; }}
.method li {{ margin:10px 0; color:var(--muted); }}
.empty {{ color:var(--muted); }}
footer {{ padding:36px 0; background:var(--ink); color:white; }}
footer .shell {{ display:flex; justify-content:space-between; gap:30px; }}
footer span {{ color:#aaa; }}
@media (max-width:800px) {{
  .shell {{ width:min(100% - 28px,1180px); }}
  .masthead {{ min-height:auto; padding-bottom:36px; }}
  .hero,.friction-layout,.attention-grid,.method {{ grid-template-columns:1fr; gap:34px; }}
  .hero {{ padding:70px 0 54px; }}
  h1 {{ font-size:clamp(52px,17vw,86px); }}
  .coverage {{ max-width:420px; }}
  .stats {{ grid-template-columns:1fr 1fr; gap:24px 0; }}
  .section {{ padding:68px 0; }}
  .event {{ grid-template-columns:84px 14px 1fr; gap:12px; }}
  .friction-row {{ grid-template-columns:34px 1fr; }}
  .ratio {{ grid-column:2; text-align:left; display:flex; align-items:baseline; gap:8px; }}
  .dimensions,.proof-list {{ grid-template-columns:1fr; }}
  .attention-row {{ grid-template-columns:100px 1fr; }}
  .attention-row span {{ grid-column:2; text-align:left; }}
}}
@media (prefers-reduced-motion:reduce) {{ * {{ scroll-behavior:auto!important; transition:none!important; animation:none!important; }} }}
@media print {{
  body,.section,main {{ background:white; }} .masthead {{ min-height:auto; }} .filters {{ display:none; }}
  .section {{ padding:36px 0; break-inside:avoid; }} .event {{ min-height:80px; }} footer {{ background:white; color:var(--ink); border-top:1px solid var(--line); }}
}}
</style>
</head>
<body>
<header class="masthead">
  <nav class="shell nav"><div class="wordmark">Build<i>Story</i></div><div class="nav-meta">{esc(c['generated'])} · {generated_date}</div></nav>
  <div class="shell hero">
    <div><div class="kicker">Project retrospective</div><h1>{esc(p['name'])}</h1><p class="tagline">{esc(c['tagline'])}</p></div>
    <div class="coverage"><span>{esc(c['coverage'])}</span><strong>{esc(sources)}</strong><p>{esc(p['branch'])} · {esc(p['start'][:10])} to {esc(p['end'][:10])}</p></div>
  </div>
  <div class="shell stats">
    <div class="stat"><strong>{m['commits']}</strong><span>{esc(c['commits'])}</span></div>
    <div class="stat"><strong>{m['files']}</strong><span>{esc(c['files'])}</span></div>
    <div class="stat"><strong>{m['calendar_days']}</strong><span>{esc(c['days'])}</span></div>
    <div class="stat"><strong>{m['time_estimate']['hours']}</strong><span>{esc(c['hours'])} · {esc(confidence_label(m['time_estimate']['confidence'], language))}</span></div>
  </div>
</header>
<main>
  <section class="section"><div class="shell">
    <div class="section-head"><h2>{esc(c['timeline'])}</h2><p>{esc(c['timeline_intro'])}</p></div>
    <div class="filters">{''.join(filters)}</div>
    <div class="timeline">{''.join(timeline_rows)}</div>
  </div></section>
  <section class="section"><div class="shell">
    <div class="section-head"><h2>{esc(c['friction'])}</h2><p>{esc(c['friction_intro'])}</p></div>
    <div class="friction-layout"><div>{''.join(friction_rows)}</div><aside class="loops"><h3>{'Loop candidates' if language == 'en' else '循环候选'}</h3>{''.join(loop_rows)}</aside></div>
  </div></section>
  <section class="section"><div class="shell">
    <div class="section-head"><h2>{esc(c['attention'])}</h2><p>{esc(c['attention_intro'])}</p></div>
    <div class="attention-grid"><div>{''.join(attention_rows)}</div><aside class="time-callout"><span class="confidence {esc(m['time_estimate']['confidence'])}">{esc(c['confidence'])}: {esc(confidence_label(m['time_estimate']['confidence'], language))}</span><strong>{m['time_estimate']['hours']}h</strong><p>{'Estimated from ' if language == 'en' else '估算来源：'}{esc(m['time_estimate']['source'])}. {esc(c['git_limit'] if m['time_estimate']['source']=='git' else c['session_limit'])}</p></aside></div>
  </div></section>
  <section class="section"><div class="shell">
    <div class="section-head"><h2>{esc(c['profile'])}</h2><p>{esc(c['profile_intro'])}</p></div>
    <div class="dimensions">{''.join(dimension_rows)}</div>
  </div></section>
  <section class="section"><div class="shell">
    <div class="section-head"><h2>{esc(c['proof'])}</h2><p>{esc(c['proof_intro'])}</p></div>
    <div class="proof-list">{''.join(card_rows)}</div>
  </div></section>
  <section class="section"><div class="shell method">
    <div><div class="section-head"><h2>{esc(c['method'])}</h2></div><p><strong>{esc(c['coverage'])}:</strong> {esc(sources)}</p><ul>{limitations}</ul></div>
    <div><h3>{'Career-output rule' if language == 'en' else '职业输出规则'}</h3><p>{esc(c['resume_prompt'])}</p><h3>{'Local-first' if language == 'en' else '本地优先'}</h3><p>{'No source code or transcript is uploaded by this generator.' if language == 'en' else '生成器不会上传源代码或会话记录。'}</p></div>
  </div></section>
</main>
<footer><div class="shell"><strong>BuildStory</strong><span>See how you built it.</span></div></footer>
<script type="application/json" id="buildstory-data">{source_data}</script>
<script>
document.querySelectorAll('.filter').forEach(function(button) {{
  button.addEventListener('click', function() {{
    document.querySelectorAll('.filter').forEach(function(item) {{ item.classList.remove('is-active'); }});
    button.classList.add('is-active');
    var selected = button.dataset.filter;
    document.querySelectorAll('.event').forEach(function(event) {{
      event.hidden = selected !== 'all' && event.dataset.category !== selected;
    }});
  }});
}});
</script>
</body>
</html>
'''


def write_outputs(data: dict[str, Any], output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    (output / "evidence.json").write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (output / "report.md").write_text(render_markdown(data), encoding="utf-8")
    (output / "report.html").write_text(render_html(data), encoding="utf-8")


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Turn a Git project history into an evidence-backed BuildStory report."
    )
    parser.add_argument("repo", nargs="?", default=".", help="Git repository to analyze. Defaults to the current directory.")
    parser.add_argument("--output", "-o", help="Output directory. Defaults to <repo>/build-story-report.")
    parser.add_argument("--session", action="append", default=[], help="Authorized session file or directory. Repeatable.")
    parser.add_argument("--language", choices=("en", "zh"), default="en", help="Report language.")
    parser.add_argument("--project-name", help="Override the project name shown in the report.")
    parser.add_argument("--version", action="version", version=f"BuildStory {VERSION}")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    repo = Path(args.repo).expanduser().resolve()
    output = Path(args.output).expanduser().resolve() if args.output else repo / "build-story-report"
    sessions = [Path(item).expanduser().resolve() for item in args.session]
    try:
        data = build_evidence(repo, sessions, args.language, args.project_name)
        write_outputs(data, output)
    except (RuntimeError, OSError) as error:
        print(f"BuildStory error: {error}", file=sys.stderr)
        return 1
    print(f"BuildStory report created: {output}")
    print(f"  HTML: {output / 'report.html'}")
    print(f"  Markdown: {output / 'report.md'}")
    print(f"  Evidence: {output / 'evidence.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
