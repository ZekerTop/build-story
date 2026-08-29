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


VERSION = "0.2.0"
MAX_TRANSCRIPT_BYTES = 20 * 1024 * 1024
MAX_TRANSCRIPT_EVENTS = 20_000
SESSION_GAP_HOURS = 2.0
TRANSCRIPT_ACTIVE_GAP_MINUTES = 30.0


COPY = {
    "en": {
        "tagline": "See how you built it, not just what you built.",
        "generated": "Generated locally from project evidence",
        "coverage": "Evidence coverage",
        "story_kicker": "The build story",
        "story_fallback": "A project moved from its first implementation through visible friction to a reviewable delivery.",
        "story_evidence": "View supporting evidence",
        "turning_points": "The turns that changed the project",
        "turning_points_intro": "Only the moments that changed direction, risk, understanding, or delivery state.",
        "full_timeline": "View every commit",
        "full_timeline_intro": "The complete Git history remains available as evidence, but it is not the story itself.",
        "friction": "Where the project fought back",
        "friction_intro": "High-change areas and loop candidates. These are prompts for review, not verdicts.",
        "attention": "Attention map",
        "attention_intro": "Estimated from change density and activity timestamps. Invisible thinking time is not captured.",
        "profile": "Evidence-backed profile",
        "profile_intro": "Human-readable evidence levels first. The numeric method stays available for inspection, never as a judgment of personal worth.",
        "proof": "What this project proves",
        "proof_intro": "Evidence cards that can support a retrospective, portfolio, resume, or interview story.",
        "career_material": "Turn evidence into a story",
        "career_confirmed": "Built from repository evidence and user-confirmed context.",
        "career_missing": "Confirm three facts before turning repository activity into career material.",
        "portfolio_summary": "Portfolio summary",
        "resume_bullets": "Resume bullets",
        "star_story": "STAR interview story",
        "situation": "Situation",
        "task": "Task",
        "action": "Action",
        "result": "Result",
        "context_role": "What was your real responsibility?",
        "context_outcome": "What outcome did the project create?",
        "context_decision": "Which decision best demonstrates your ability?",
        "dialogue_user": "User",
        "dialogue_ai": "AI",
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
        "evidence": "Evidence",
        "calculation": "View calculation",
        "recommendation": "Next time",
        "reason": "Why",
        "loop_candidates": "Loop candidates",
        "change_volume": "lines changed",
        "touches": "commit touches",
        "project_root": "Project root",
        "source_code": "Core code",
        "automation": "Automation workflows",
        "tests_area": "Tests",
        "docs_area": "Documentation",
        "scripts_area": "Tooling scripts",
        "career_output_rule": "Career-output rule",
        "career_confirmed_rule": "Use only confirmed responsibility, decisions, and outcomes. Never present commit volume as impact.",
        "local_first": "Local-first",
        "local_first_detail": "No source code, context file, or transcript is uploaded by this generator.",
        "footer": "See how you built it.",
    },
    "zh": {
        "tagline": "不只看你做出了什么，更看你是怎么做到的。",
        "generated": "基于本地项目证据生成",
        "coverage": "证据覆盖范围",
        "story_kicker": "项目故事",
        "story_fallback": "这个项目从第一次实现出发，穿过可见的阻力，最终形成了一次可以复盘的交付。",
        "story_evidence": "查看支撑证据",
        "turning_points": "真正改变项目的转折点",
        "turning_points_intro": "只保留改变方向、风险、理解或交付状态的关键时刻。",
        "full_timeline": "查看全部提交",
        "full_timeline_intro": "完整 Git 历史仍然保留为证据，但它本身不是故事。",
        "friction": "项目在哪里卡住了",
        "friction_intro": "高频变更区域与循环候选。它们用于复盘，不是对人的判决。",
        "attention": "注意力地图",
        "attention_intro": "根据变更密度和活动时间估算，无法覆盖离线思考时间。",
        "profile": "基于证据的能力画像",
        "profile_intro": "先展示人能理解的证据等级，数字计算方法只放在详情中，不评价人的价值。",
        "proof": "这个项目证明了什么",
        "proof_intro": "可用于项目复盘、作品集、简历和面试故事的证据卡片。",
        "career_material": "把证据变成能讲述的故事",
        "career_confirmed": "由仓库证据与用户确认的真实语境共同生成。",
        "career_missing": "把仓库活动写成职业材料前，只需要确认三件事。",
        "portfolio_summary": "作品集摘要",
        "resume_bullets": "简历要点",
        "star_story": "STAR 面试故事",
        "situation": "背景",
        "task": "任务",
        "action": "行动",
        "result": "结果",
        "context_role": "你在项目中的真实职责是什么？",
        "context_outcome": "最终给用户或自己带来了什么结果？",
        "context_decision": "哪个决定最能代表你的能力？",
        "dialogue_user": "用户",
        "dialogue_ai": "AI",
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
        "evidence": "证据",
        "calculation": "查看计算方法",
        "recommendation": "下次建议",
        "reason": "原因",
        "loop_candidates": "循环候选",
        "change_volume": "行变更",
        "touches": "次提交触达",
        "project_root": "项目根目录",
        "source_code": "核心代码",
        "automation": "自动化工作流",
        "tests_area": "测试",
        "docs_area": "文档",
        "scripts_area": "工具脚本",
        "career_output_rule": "职业输出规则",
        "career_confirmed_rule": "只使用用户确认的职责、决策与结果，不把提交次数写成影响指标。",
        "local_first": "本地优先",
        "local_first_detail": "生成器不会上传源代码、语境文件或会话记录。",
        "footer": "看见你是怎么做到的。",
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


def load_context(path: Path | None) -> dict[str, Any]:
    if path is None:
        return {}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise RuntimeError(f"Invalid context JSON: {error}") from error
    if not isinstance(value, dict):
        raise RuntimeError("Context JSON must contain an object.")
    return value


def context_for_language(context: dict[str, Any], language: str) -> dict[str, Any]:
    value = context.get(language, context)
    if not isinstance(value, dict):
        return {}
    allowed = {"role", "outcome", "key_decision", "summary", "resume_bullets", "translations"}
    result = {key: value[key] for key in allowed if key in value}
    if "resume_bullets" in result and not isinstance(result["resume_bullets"], list):
        result["resume_bullets"] = []
    if "translations" in result and not isinstance(result["translations"], dict):
        result["translations"] = {}
    return result


def localized_dynamic_text(text: str, context: dict[str, Any], language: str) -> str:
    translations = context.get("translations", {})
    translated = translations.get(text) if isinstance(translations, dict) else None
    if translated:
        return str(translated)
    if language != "zh":
        return text

    quoted_revert = re.fullmatch(r'Revert ["“](.*?)["”]', text, re.I)
    if quoted_revert:
        inner = localized_dynamic_text(quoted_revert.group(1), context, language)
        return f"回滚“{inner}”"

    templates = [
        (r"^Initialize (.+)$", "初始化 {}"),
        (r"^Add (.+)$", "新增 {}"),
        (r"^Fix (.+)$", "修复 {}"),
        (r"^Refactor (.+)$", "重构 {}"),
        (r"^Replace (.+) with (.+)$", "用 {} 替代 {}"),
        (r"^Document (.+)$", "记录 {}"),
        (r"^Prepare (.+)$", "准备 {}"),
        (r"^Release (.+)$", "发布 {}"),
    ]
    for pattern, template in templates:
        match = re.fullmatch(pattern, text, re.I)
        if not match:
            continue
        groups = [group.strip() for group in match.groups()]
        if pattern.startswith("^Replace"):
            return template.format(groups[1], groups[0])
        return template.format(*groups)
    return text


def count_text(value: int, noun: str, language: str) -> str:
    if language == "zh":
        units = {"commit": "次提交", "file": "个文件", "day": "个自然日", "loop": "个循环候选"}
        return f"{value} {units[noun]}"
    singular = {"commit": "commit", "file": "file", "day": "calendar day", "loop": "loop candidate"}[noun]
    return f"{value} {singular if value == 1 else singular + 's'}"


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
        ("refactor", r"\b(refactor|cleanup|simplify|rename|restructure|replace|migrate|switch)\b|重构|清理|简化|替换|迁移"),
        ("fix", r"\b(fix|bug|repair|resolve|patch|hotfix)\b|修复|修正|解决"),
        ("foundation", r"\b(init|initialize|initial|bootstrap|scaffold|setup|configure|config)\b|初始化|搭建|配置"),
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


def dimension_level(key: str, score: int, language: str) -> str:
    if key == "traceability":
        thresholds = [(85, "Clear", "清晰"), (70, "Mostly clear", "较清晰"), (50, "Needs review", "需要复盘")]
    elif key == "iteration":
        thresholds = [(80, "Stable", "稳定"), (65, "Mostly stable", "基本稳定"), (45, "Needs review", "需要复盘")]
    else:
        thresholds = [(85, "Strong", "充分"), (70, "Healthy", "较强"), (50, "Needs review", "需要复盘")]
    for minimum, english, chinese in thresholds:
        if score >= minimum:
            return english if language == "en" else chinese
    return "Limited evidence" if language == "en" else "证据不足"


def dimension_recommendation(
    key: str,
    language: str,
    signals: dict[str, Any],
    explicit_reverts: int,
    friction: list[dict[str, Any]],
    meaningful_ratio: float,
) -> str:
    if key == "delivery":
        if not signals["tags"]:
            return "Add a release tag and changelog entry when the project reaches a usable milestone." if language == "en" else "项目达到可用里程碑时，用发布标签和变更说明明确收尾。"
        return "Keep release tags, change notes, and usage documentation as the definition of done." if language == "en" else "继续把发布标签、变更说明和使用文档作为一次交付的收尾。"
    if key == "validation":
        if not signals["tests"] or not signals["ci"]:
            return "Turn the most frequently changed path into a regression test, then run it in CI." if language == "en" else "把修改最频繁的核心路径写成回归测试，并放进 CI 自动验证。"
        return "Add regression tests around the paths that absorbed the most rework before the next release." if language == "en" else "下次发布前，优先为返工最集中的路径补充回归测试。"
    if key == "traceability":
        if meaningful_ratio < 0.8:
            return "Write commit subjects around decisions and user-visible change, not generic activity." if language == "en" else "提交说明围绕决策和用户可见变化来写，避免只写“更新”或“修复”。"
        return "Keep commits small and describe the decision each change preserves or replaces." if language == "en" else "保持提交规模可审查，并说明每次变更保留或替代了什么决定。"
    if key == "iteration":
        if explicit_reverts or friction:
            return "Before implementing cross-boundary state, write down failure recovery and an exit condition. After two repeated fixes, pause and reconsider the direction." if language == "en" else "实现跨边界状态前，先写清失败恢复与退出条件；同一方案连续修复两次后，暂停并重新判断方向。"
        return "Keep marking experiments explicitly so productive exploration stays distinguishable from blocked loops." if language == "en" else "继续明确标记实验，让有效探索与受阻循环始终可以区分。"
    if not signals["adr"]:
        return "Record the most important trade-off as a short decision note: context, options, decision, and consequence." if language == "en" else "把最重要的取舍写成一条简短决策记录：背景、选项、决定与后果。"
    return "Keep the decision record connected to the release or behavior it changed." if language == "en" else "继续把关键决策记录与它改变的发布结果或产品行为连接起来。"


def score_dimensions(
    commits: list[Commit],
    files: list[str],
    signals: dict[str, Any],
    friction: list[dict[str, Any]],
    loops: list[dict[str, Any]],
    language: str,
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
            (signals["license"], "license" if language == "en" else "许可证"),
            (signals["manifest"], "package manifest" if language == "en" else "项目清单"),
            (
                bool(signals["tags"]),
                f"{len(signals['tags'])} Git {'tag' if len(signals['tags']) == 1 else 'tags'}"
                if language == "en"
                else f"{len(signals['tags'])} 个 Git 标签",
            ),
            (signals["docs"], "project documentation" if language == "en" else "项目文档"),
        ]
        if present
    ] or ["No strong delivery artifact detected" if language == "en" else "未发现明确的交付产物"]

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
        validation_evidence.append("test files" if language == "en" else "测试文件")
    if signals["ci"]:
        validation_evidence.append("CI workflow" if language == "en" else "CI 工作流")
    if signals["lint"]:
        validation_evidence.append("lint configuration" if language == "en" else "代码检查配置")
    validation_evidence.append(
        f"{validation_commits} validation-related {'commit' if validation_commits == 1 else 'commits'}"
        if language == "en"
        else f"{validation_commits} 次验证相关提交"
    )

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
        f"{meaningful_ratio:.0%} descriptive commit subjects"
        if language == "en"
        else f"{meaningful_ratio:.0%} 的提交说明具有描述性",
        f"{reviewable_ratio:.0%} reviewable-size commits"
        if language == "en"
        else f"{reviewable_ratio:.0%} 的提交规模便于审查",
    ]

    explicit_reverts = sum(loop["type"] == "explicit-reversal" for loop in loops)
    top_rework = sum(row["rework_ratio"] for row in friction[:3]) / max(1, len(friction[:3]))
    iteration_score = round(max(0, min(100, 92 - explicit_reverts * 13 - top_rework * 34)))
    iteration_evidence = [
        f"{explicit_reverts} explicit {'reversal' if explicit_reverts == 1 else 'reversals'}"
        if language == "en"
        else f"{explicit_reverts} 次明确回滚",
        f"{len(friction)} high-change file {'candidate' if len(friction) == 1 else 'candidates'}"
        if language == "en"
        else f"{len(friction)} 个高频变更文件候选",
        "High churn may represent productive iteration and still requires context"
        if language == "en"
        else "高频变更可能是有效探索，仍需结合真实语境复盘",
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
            (signals["docs"], "docs directory or architecture guide" if language == "en" else "文档目录或架构说明"),
            (signals["changelog"], "changelog" if language == "en" else "变更记录"),
            (signals["adr"], "architecture decision records" if language == "en" else "架构决策记录"),
        ]
        if present
    ] or ["No durable learning artifact detected" if language == "en" else "未发现可长期复用的经验记录"]

    rows = [
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
    for row in rows:
        row["level"] = dimension_level(row["key"], row["score"], language)
        row["reason"] = "；".join(row["evidence"]) if language == "zh" else "; ".join(row["evidence"])
        row["recommendation"] = dimension_recommendation(
            row["key"], language, signals, explicit_reverts, friction, meaningful_ratio
        )
    return rows


def humanize_area_name(area: str, language: str) -> str:
    lower = area.lower()
    if lower == "(root)":
        return COPY[language]["project_root"]
    if lower in {"src", "source", "app", "lib"}:
        return COPY[language]["source_code"]
    if lower == ".github":
        return COPY[language]["automation"]
    if lower in {"test", "tests", "spec", "specs", "__tests__"}:
        return COPY[language]["tests_area"]
    if lower in {"doc", "docs"}:
        return COPY[language]["docs_area"]
    if lower in {"script", "scripts", "tools"}:
        return COPY[language]["scripts_area"]
    return area


def directory_attention(file_stats: dict[str, dict[str, Any]], language: str) -> list[dict[str, Any]]:
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
        results.append({"area": name, "label": humanize_area_name(name, language), **row, "attention_score": round(score, 2)})
    results.sort(key=lambda item: item["attention_score"], reverse=True)
    return results[:8]


def evidence_cards(
    project_name: str,
    commits: list[Commit],
    files: list[str],
    signals: dict[str, Any],
    attention: list[dict[str, Any]],
    language: str,
    context: dict[str, Any],
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
            }
        )
    else:
        cards.append(
            {
                "title": "持续交付",
                "evidence": f"在 {span} 个自然日内完成 {len(commits)} 次提交，涉及 {len(files)} 个受版本控制的文件。",
            }
        )
    if attention:
        top = ", ".join(row["label"] for row in attention[:3])
        cards.append(
            {
                "title": "Core implementation areas" if language == "en" else "核心实现区域",
                "evidence": (
                    f"Most change activity concentrated in: {top}."
                    if language == "en"
                    else f"主要变更活动集中在：{top}。"
                ),
            }
        )
    if signals["tests"] or signals["ci"]:
        pieces = []
        if signals["tests"]:
            pieces.append("tests" if language == "en" else "测试")
        if signals["ci"]:
            pieces.append("CI")
        joined = " and ".join(pieces) if language == "en" else " 和 ".join(pieces)
        cards.append(
            {
                "title": "Validation infrastructure" if language == "en" else "验证基础设施",
                "evidence": (
                    f"The repository contains {joined}."
                    if language == "en"
                    else f"仓库中已包含 {joined}。"
                ),
            }
        )
    bullets = [str(item) for item in context.get("resume_bullets", []) if str(item).strip()]
    for index, card in enumerate(cards):
        if index < len(bullets):
            card["career"] = bullets[index]
    return cards


def turning_point_reason(event: dict[str, Any], language: str, role: str | None = None) -> str:
    labels = {
        "en": {
            "start": "Project start",
            "reversed_attempt": "Attempt later reversed",
            "friction": "Repeated refinement",
            "reversal": "Direction change",
            "new_direction": "New direction",
            "validation": "Validation established",
            "documentation": "Decision captured",
            "delivery": "Delivery milestone",
            "default": "Key implementation",
        },
        "zh": {
            "start": "项目起点",
            "reversed_attempt": "引入后续被撤销的方案",
            "friction": "反复打磨",
            "reversal": "方向调整",
            "new_direction": "确立新方向",
            "validation": "建立验证",
            "documentation": "沉淀决策",
            "delivery": "完成交付",
            "default": "关键实现",
        },
    }[language]
    if role:
        return labels[role]
    if event["category"] in {"validation", "documentation", "delivery"}:
        return labels[event["category"]]
    return labels["default"]


def select_turning_points(timeline: list[dict[str, Any]], language: str, limit: int = 7) -> list[dict[str, Any]]:
    if not timeline:
        return []
    candidates: dict[int, tuple[int, str]] = {}

    def add(index: int, priority: int, role: str) -> None:
        if index < 0 or index >= len(timeline):
            return
        current = candidates.get(index)
        if current is None or priority > current[0]:
            candidates[index] = (priority, role)

    add(0, 100, "start")
    add(len(timeline) - 1, 99, "delivery" if timeline[-1]["category"] == "delivery" else "default")

    for index, event in enumerate(timeline):
        if re.search(r"\b(revert|rollback|back out|backout)\b|回滚|撤销", event["subject"].lower()):
            add(index, 98, "reversal")
            quoted = re.search(r'["“](.*?)["”]', event["subject"])
            if quoted:
                target = quoted.group(1).strip().lower()
                for previous in range(index - 1, -1, -1):
                    if timeline[previous]["subject"].strip().lower() == target:
                        add(previous, 96, "reversed_attempt")
                        break
            add(index - 1, 90, "friction")
            add(index + 1, 95, "new_direction")

    category_priority = {
        "validation": 88,
        "documentation": 78,
        "delivery": 86,
        "feature": 70,
        "refactor": 68,
        "fix": 66,
        "foundation": 60,
        "other": 40,
    }
    seen_categories: set[str] = set()
    for index, event in enumerate(timeline):
        category = event["category"]
        if category not in seen_categories:
            add(index, category_priority[category], category if category in {"validation", "documentation", "delivery"} else "default")
            seen_categories.add(category)
        if index and category != timeline[index - 1]["category"]:
            add(index, category_priority[category] - 4, category if category in {"validation", "documentation", "delivery"} else "default")

    if len(candidates) < limit:
        volumes = sorted(
            range(len(timeline)),
            key=lambda index: timeline[index]["added"] + timeline[index]["deleted"],
            reverse=True,
        )
        for index in volumes:
            add(index, 50, "default")
            if len(candidates) >= limit:
                break

    chosen = sorted(candidates.items(), key=lambda item: (-item[1][0], item[0]))[:limit]
    results = []
    for index, (_, role) in sorted(chosen):
        event = dict(timeline[index])
        event["turning_point_reason"] = turning_point_reason(event, language, role)
        results.append(event)
    return results


def attach_dialogue_to_turning_points(
    turning_points: list[dict[str, Any]],
    transcript_events: list[dict[str, Any]],
    context: dict[str, Any],
    language: str,
) -> list[dict[str, Any]]:
    timestamped = sorted(
        (event for event in transcript_events if event.get("timestamp") and event.get("text")),
        key=lambda event: event["timestamp"],
    )
    users = [
        event
        for event in timestamped
        if any(token in event["role"] for token in ("user", "human", "prompt"))
    ]
    assistants = [
        event
        for event in timestamped
        if any(token in event["role"] for token in ("assistant", "agent", "ai"))
    ]
    results = []
    for point in turning_points:
        row = dict(point)
        point_time = parse_datetime(point["timestamp"])
        if point_time is None:
            results.append(row)
            continue
        candidates = [
            event
            for event in users
            if 0 <= (point_time - event["timestamp"]).total_seconds() <= 6 * 3600
        ]
        if not candidates:
            results.append(row)
            continue
        user_event = candidates[-1]
        response_candidates = [
            event
            for event in assistants
            if user_event["timestamp"] <= event["timestamp"] <= point_time + dt.timedelta(minutes=30)
        ]
        dialogue = {
            "user": localized_dynamic_text(user_event["text"][:220], context, language),
        }
        if response_candidates:
            dialogue["ai"] = localized_dynamic_text(response_candidates[0]["text"][:220], context, language)
        row["dialogue"] = dialogue
        results.append(row)
    return results


def build_story_summary(
    project_name: str,
    timeline: list[dict[str, Any]],
    loops: list[dict[str, Any]],
    signals: dict[str, Any],
    attention: list[dict[str, Any]],
    context: dict[str, Any],
    language: str,
) -> dict[str, Any]:
    explicit_reverts = sum(item["type"] == "explicit-reversal" for item in loops)
    headline = str(context.get("summary") or "").strip()
    if not headline:
        if explicit_reverts:
            headline = (
                "After a visible change in direction, the project moved from repeated refinement to a reviewable delivery."
                if language == "en"
                else "经历一次明确的方向调整后，项目从反复打磨走向了可以验证的交付。"
            )
        else:
            headline = COPY[language]["story_fallback"]

    highlights = []
    if explicit_reverts:
        highlights.append(
            f"{explicit_reverts} explicit direction {'change' if explicit_reverts == 1 else 'changes'}"
            if language == "en"
            else f"{explicit_reverts} 次关键方向调整"
        )
    review_loops = len([item for item in loops if item["confidence"] in {"high", "medium"}])
    highlights.append(
        f"{count_text(review_loops, 'loop', language)} worth reviewing"
        if language == "en"
        else f"{count_text(review_loops, 'loop', language)}需要复盘"
    )
    if attention:
        highlights.append(
            f"Most visible attention: {attention[0]['label']}"
            if language == "en"
            else f"注意力最集中：{attention[0]['label']}"
        )
    finish = []
    if signals["tests"]:
        finish.append("tests" if language == "en" else "测试")
    if signals["ci"]:
        finish.append("CI")
    if signals["tags"]:
        finish.append("a tagged release" if language == "en" else "版本发布")
    if finish:
        highlights.append(
            f"Finished with {', '.join(finish)}"
            if language == "en"
            else f"最终完成{'、'.join(finish)}"
        )
    confirmed_story_context = any(context.get(key) for key in ("role", "outcome", "key_decision", "summary"))
    return {"headline": headline, "highlights": highlights[:3], "context_confirmed": confirmed_story_context}


def build_career_material(
    project_name: str,
    story: dict[str, Any],
    context: dict[str, Any],
    turning_points: list[dict[str, Any]],
    language: str,
) -> dict[str, Any]:
    role = str(context.get("role") or "").strip()
    outcome = str(context.get("outcome") or "").strip()
    decision = str(context.get("key_decision") or "").strip()
    bullets = [str(item).strip() for item in context.get("resume_bullets", []) if str(item).strip()]
    confirmed = bool(role and outcome and decision)
    if not confirmed:
        return {
            "confirmed": False,
            "questions": [
                COPY[language]["context_role"],
                COPY[language]["context_outcome"],
                COPY[language]["context_decision"],
            ],
        }
    portfolio = " ".join(part for part in [story["headline"], decision, outcome] if part)
    if not bullets:
        bullets = [
            f"Led {role.rstrip('.')} for {project_name}; made the decision to {decision.rstrip('.')}, resulting in {outcome.rstrip('.')}."
            if language == "en"
            else f"负责{role.rstrip('。')}；通过{decision.rstrip('。')}，最终{outcome.rstrip('。')}。"
        ]
    first = turning_points[0]["subject"] if turning_points else project_name
    return {
        "confirmed": True,
        "portfolio_summary": portfolio,
        "resume_bullets": bullets,
        "star": {
            "situation": first,
            "task": role,
            "action": decision,
            "result": outcome,
        },
    }


def build_evidence(
    repo: Path,
    session_paths: list[Path],
    language: str,
    project_name: str | None,
    context: dict[str, Any] | None = None,
) -> dict[str, Any]:
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
    dimensions = score_dimensions(commits, files, signals, friction, loops, language)
    attention = directory_attention(file_stats, language)
    name = project_name or root.name
    localized_context = context_for_language(context or {}, language)
    localized_loops = []
    for item in loops:
        row = dict(item)
        row["original_title"] = item["title"]
        row["title"] = localized_dynamic_text(item["title"], localized_context, language)
        localized_loops.append(row)
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
            "subject": localized_dynamic_text(commit.subject, localized_context, language),
            "original_subject": commit.subject,
            "category": commit.category,
            "files": len(commit.files),
            "added": commit.additions,
            "deleted": commit.deletions,
        }
        for commit in commits
    ]
    turning_points = select_turning_points(timeline, language)
    turning_points = attach_dialogue_to_turning_points(
        turning_points, transcript_events, localized_context, language
    )
    story = build_story_summary(name, timeline, localized_loops, signals, attention, localized_context, language)
    career_material = build_career_material(name, story, localized_context, turning_points, language)
    source_list = ["git"] + (["transcripts"] if transcript_files else [])
    return {
        "schema_version": "1.2",
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
        "story": story,
        "turning_points": turning_points,
        "timeline": timeline,
        "friction_zones": friction,
        "loop_candidates": localized_loops[:15],
        "attention_areas": attention,
        "dimensions": dimensions,
        "signals": signals,
        "transcripts": transcript_analysis,
        "evidence_cards": evidence_cards(name, commits, files, signals, attention, language, localized_context),
        "career_material": career_material,
    }


def confidence_label(value: str, language: str) -> str:
    return COPY[language].get(value, value)


def label_value(label: str, value: str, language: str) -> str:
    return f"{label}：{value}" if language == "zh" else f"{label}: {value}"


def render_markdown(data: dict[str, Any]) -> str:
    language = data["language"]
    c = COPY[language]
    p = data["project"]
    m = data["metrics"]
    lines = [
        f"# BuildStory: {p['name']}",
        "",
        f"> **{data['story']['headline']}**",
        "",
    ]
    lines.extend(f"- {item}" for item in data["story"]["highlights"])
    lines.extend(
        [
            "",
            "<details>",
            f"<summary>{c['story_evidence']}</summary>",
            "",
            f"- {m['commits']} {c['commits']}",
            f"- {m['files']} {c['files']}",
            f"- {m['calendar_days']} {c['days']}",
            f"- {m['time_estimate']['hours']} {c['hours']} ({label_value(c['confidence'], confidence_label(m['time_estimate']['confidence'], language), language)})",
            "",
            "</details>",
            "",
            f"## {c['turning_points']}",
            "",
        ]
    )
    for event in data["turning_points"]:
        lines.append(
            f"- `{event['date']}` **{event['turning_point_reason']}** · {event['subject']} (`{event['short_hash']}`)"
        )
        dialogue = event.get("dialogue")
        if dialogue:
            lines.append(f"  - **{c['dialogue_user']}：** {dialogue['user']}" if language == "zh" else f"  - **{c['dialogue_user']}:** {dialogue['user']}")
            if dialogue.get("ai"):
                lines.append(f"  - **{c['dialogue_ai']}：** {dialogue['ai']}" if language == "zh" else f"  - **{c['dialogue_ai']}:** {dialogue['ai']}")
    lines.extend(
        [
            "",
            "<details>",
            f"<summary>{c['full_timeline']} · {count_text(len(data['timeline']), 'commit', language)}</summary>",
            "",
        ]
    )
    for event in data["timeline"]:
        label = CATEGORY_LABELS[language][event["category"]]
        lines.append(f"- `{event['date']}` **{label}** · {event['subject']} (`{event['short_hash']}`)")
    lines.extend(["", "</details>", "", f"## {c['friction']}", ""])
    if data["friction_zones"]:
        for item in data["friction_zones"]:
            if language == "en":
                detail = f"{count_text(item['commits'], 'commit', language)} · +{item['added']} / -{item['deleted']} · {item['rework_ratio']:.0%} bidirectional churn"
            else:
                detail = f"{count_text(item['commits'], 'commit', language)} · 新增 {item['added']} / 删除 {item['deleted']} · 双向变更信号 {item['rework_ratio']:.0%}"
            lines.append(f"- `{item['path']}` · {detail}")
    else:
        lines.append(f"- {c['none']}")
    lines.extend(["", f"### {c['loop_candidates']}", ""])
    if data["loop_candidates"]:
        for item in data["loop_candidates"]:
            lines.append(
                f"- **{item['title']}** · {item['detail']} ({label_value(c['confidence'], confidence_label(item['confidence'], language), language)})"
            )
    else:
        lines.append(f"- {c['none']}")
    lines.extend(["", f"## {c['attention']}", ""])
    for item in data["attention_areas"]:
        if language == "en":
            lines.append(f"- **{item['label']}** · {int(item['gross'])} lines changed · {int(item['commits'])} commit touches")
        else:
            lines.append(f"- **{item['label']}** · {int(item['gross'])} 行变更 · {int(item['commits'])} 次提交触达")
    lines.extend(["", f"## {c['profile']}", ""])
    for item in data["dimensions"]:
        lines.extend(
            [
                f"### {DIMENSION_LABELS[language][item['key']]} · {item['level']}",
                "",
                f"- **{c['reason']}：** {item['reason']}" if language == "zh" else f"- **{c['reason']}:** {item['reason']}",
                f"- **{c['recommendation']}：** {item['recommendation']}" if language == "zh" else f"- **{c['recommendation']}:** {item['recommendation']}",
                "",
                "<details>",
                f"<summary>{c['calculation']} · {item['score']}/100</summary>",
                "",
            ]
        )
        for evidence in item["evidence"]:
            lines.append(f"- {evidence}")
        lines.extend(["", "</details>", ""])
    lines.extend([f"## {c['proof']}", ""])
    for card in data["evidence_cards"]:
        lines.extend([f"### {card['title']}", "", card["evidence"], ""])
        if card.get("career"):
            lines.extend([f"> {card['career']}", ""])

    career = data["career_material"]
    lines.extend([f"## {c['career_material']}", ""])
    if career["confirmed"]:
        lines.extend([f"### {c['portfolio_summary']}", "", career["portfolio_summary"], "", f"### {c['resume_bullets']}", ""])
        lines.extend(f"- {item}" for item in career["resume_bullets"])
        lines.extend(["", f"### {c['star_story']}", ""])
        for key in ("situation", "task", "action", "result"):
            lines.append(f"- **{c[key]}：** {career['star'][key]}" if language == "zh" else f"- **{c[key]}:** {career['star'][key]}")
    else:
        lines.append(c["career_missing"])
        lines.append("")
        lines.extend(f"- {item}" for item in career["questions"])
    lines.extend(["", f"## {c['method']}", ""])
    for limitation in data["coverage"]["limitations"]:
        lines.append(f"- {limitation}")
    return "\n".join(lines).rstrip() + "\n"


def esc(value: Any) -> str:
    return html.escape(str(value), quote=True)


def render_html(data: dict[str, Any], language_links: dict[str, str] | None = None) -> str:
    language = data["language"]
    c = COPY[language]
    p = data["project"]
    m = data["metrics"]
    category_labels = CATEGORY_LABELS[language]

    filters = [f'<button class="filter is-active" data-filter="all">{esc(c["all"])}</button>'] + [
        f'<button class="filter" data-filter="{key}">{esc(category_labels[key])} <span>{count}</span></button>'
        for key, count in sorted(m["category_counts"].items())
    ]

    timeline_rows = []
    for event in data["timeline"][-160:]:
        file_text = count_text(event["files"], "file", language)
        timeline_rows.append(
            f'''<article class="event" data-category="{esc(event['category'])}">
  <div class="event-date">{esc(event['date'])}</div>
  <div class="event-mark" aria-hidden="true"></div>
  <div class="event-body">
    <div class="event-meta"><span>{esc(category_labels[event['category']])}</span><code>{esc(event['short_hash'])}</code></div>
    <h3>{esc(event['subject'])}</h3>
    <p>{esc(file_text)} · <strong>+{event['added']}</strong> / -{event['deleted']}</p>
  </div>
</article>'''
        )

    turning_rows = []
    for index, event in enumerate(data["turning_points"], start=1):
        file_text = count_text(event["files"], "file", language)
        dialogue = event.get("dialogue")
        dialogue_html = ""
        if dialogue:
            ai_line = f'<p><b>{esc(c["dialogue_ai"])}</b><span>{esc(dialogue["ai"])}</span></p>' if dialogue.get("ai") else ""
            dialogue_html = f'''\n    <div class="dialogue"><p><b>{esc(c['dialogue_user'])}</b><span>{esc(dialogue['user'])}</span></p>{ai_line}</div>'''
        turning_rows.append(
            f'''<article class="turn">
  <div class="turn-number">{index:02d}</div>
  <div class="turn-body">
    <div class="turn-meta"><span>{esc(event['turning_point_reason'])}</span><time>{esc(event['date'])}</time></div>
    <h3>{esc(event['subject'])}</h3>
    <p>{esc(category_labels[event['category']])} · {esc(file_text)} · <code>{esc(event['short_hash'])}</code></p>{dialogue_html}
  </div>
</article>'''
        )

    friction_rows = []
    for index, item in enumerate(data["friction_zones"][:8], start=1):
        commit_text = count_text(item["commits"], "commit", language)
        delta_text = f"+{item['added']} / -{item['deleted']}" if language == "en" else f"新增 {item['added']} / 删除 {item['deleted']}"
        friction_rows.append(
            f'''<div class="friction-row">
  <div class="rank">{index:02d}</div>
  <div><code>{esc(item['path'])}</code><p>{esc(commit_text)} · {esc(delta_text)}</p></div>
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
        metric = f"{int(item['gross'])} lines changed · {int(item['commits'])} commit touches" if language == "en" else f"{int(item['gross'])} 行变更 · {int(item['commits'])} 次提交触达"
        attention_rows.append(
            f'''<div class="attention-row">
  <strong>{esc(item['label'])}</strong>
  <div class="attention-dots" aria-label="{'relative attention' if language == 'en' else '相对注意力'} {relative:.0%}">{''.join('<i></i>' for _ in range(max(1, round(relative * 10))))}</div>
  <span>{esc(metric)}</span>
</div>'''
        )

    dimension_rows = []
    for item in data["dimensions"]:
        evidence = "".join(f"<li>{esc(line)}</li>" for line in item["evidence"])
        calculation_label = f"{c['calculation']} · {item['score']}/100"
        dimension_rows.append(
            f'''<article class="dimension">
  <div class="dimension-heading"><h3>{esc(DIMENSION_LABELS[language][item['key']])}</h3><strong>{esc(item['level'])}</strong></div>
  <div class="dimension-copy"><p><b>{esc(c['reason'])}</b>{'：' if language == 'zh' else ': '}{esc(item['reason'])}</p><p><b>{esc(c['recommendation'])}</b>{'：' if language == 'zh' else ': '}{esc(item['recommendation'])}</p></div>
  <details class="calculation"><summary>{esc(calculation_label)}</summary><div class="score-axis" aria-label="{item['score']} / 100"><span style="left:{item['score']}%"></span></div><span class="confidence {esc(item['confidence'])}">{esc(label_value(c['confidence'], confidence_label(item['confidence'], language), language))}</span><ul>{evidence}</ul></details>
</article>'''
        )

    card_rows = []
    for card in data["evidence_cards"]:
        career = f'<blockquote>{esc(card["career"])}</blockquote>' if card.get("career") else ""
        card_rows.append(f'''<article class="proof-card"><h3>{esc(card['title'])}</h3><p>{esc(card['evidence'])}</p>{career}</article>''')

    career = data["career_material"]
    if career["confirmed"]:
        resume_items = "".join(f"<li>{esc(item)}</li>" for item in career["resume_bullets"])
        star_items = "".join(
            f'<li><b>{esc(c[key])}</b><span>{esc(career["star"][key])}</span></li>'
            for key in ("situation", "task", "action", "result")
        )
        career_html = f'''<div class="career-grid">
  <article><span class="eyebrow">{esc(c['portfolio_summary'])}</span><p>{esc(career['portfolio_summary'])}</p></article>
  <article><span class="eyebrow">{esc(c['resume_bullets'])}</span><ul>{resume_items}</ul></article>
  <article><span class="eyebrow">{esc(c['star_story'])}</span><ol class="star-list">{star_items}</ol></article>
</div>'''
        career_intro = c["career_confirmed"]
    else:
        questions = "".join(f"<li>{esc(item)}</li>" for item in career["questions"])
        context_example = '{\n  "zh": {\n    "role": "...",\n    "outcome": "...",\n    "key_decision": "..."\n  }\n}' if language == "zh" else '{\n  "en": {\n    "role": "...",\n    "outcome": "...",\n    "key_decision": "..."\n  }\n}'
        career_html = f'''<div class="context-callout"><ol>{questions}</ol><div><code>--context context.json</code><pre>{esc(context_example)}</pre></div></div>'''
        career_intro = c["career_missing"]

    source_joiner = ", " if language == "en" else "、"
    sources = source_joiner.join(c["source_git"] if source == "git" else c["source_sessions"] for source in data["coverage"]["sources"])
    limitations = "".join(f"<li>{esc(item)}</li>" for item in data["coverage"]["limitations"])
    highlights = "".join(f"<li>{esc(item)}</li>" for item in data["story"]["highlights"])
    generated_date = data["generated_at"][:10]
    source_data = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    language_switch = ""
    if language_links:
        language_switch = f'''<div class="lang-switch" aria-label="Language">
  <a href="{esc(language_links['en'])}" class="{'is-current' if language == 'en' else ''}" lang="en">EN</a>
  <a href="{esc(language_links['zh'])}" class="{'is-current' if language == 'zh' else ''}" lang="zh-CN">中文</a>
</div>'''

    source_label = c["source_git"] if m["time_estimate"]["source"] == "git" else c["source_sessions"]
    date_connector = "to" if language == "en" else "至"
    html_lang = "en" if language == "en" else "zh-CN"
    kicker = "PROJECT RETROSPECTIVE" if language == "en" else "项目复盘"

    return f'''<!doctype html>
<html lang="{html_lang}">
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
code,pre {{ font-family:ui-monospace,SFMono-Regular,Menlo,monospace; overflow-wrap:anywhere; }}
.shell {{ width:min(1180px,calc(100% - 40px)); margin:0 auto; }}
.masthead {{ min-height:88dvh; padding:28px 0 44px; display:grid; grid-template-rows:auto 1fr; border-bottom:1px solid var(--line); }}
.nav {{ display:flex; align-items:center; justify-content:space-between; gap:20px; }}
.wordmark {{ font-weight:850; letter-spacing:-.04em; font-size:20px; }}
.wordmark i {{ color:var(--accent); font-style:normal; }}
.nav-right {{ display:flex; align-items:center; justify-content:flex-end; gap:16px; }}
.nav-meta {{ color:var(--muted); font-size:13px; }}
.lang-switch {{ display:flex; align-items:center; padding:3px; border:1px solid var(--line); border-radius:9px; background:rgb(255 255 255 / .45); }}
.lang-switch a {{ min-width:42px; padding:5px 8px; border-radius:6px; color:var(--muted); font:700 11px/1.2 ui-monospace,SFMono-Regular,Menlo,monospace; text-align:center; text-decoration:none; }}
.lang-switch a:hover {{ color:var(--ink); }}
.lang-switch a.is-current {{ color:white; background:var(--ink); }}
.hero {{ align-self:center; display:grid; grid-template-columns:minmax(0,1.35fr) minmax(280px,.65fr); gap:8vw; align-items:end; padding:68px 0 36px; }}
.kicker,.eyebrow {{ color:var(--accent); font:700 12px/1 ui-monospace,SFMono-Regular,Menlo,monospace; letter-spacing:.14em; text-transform:uppercase; }}
h1 {{ margin:18px 0 28px; max-width:12ch; font-size:clamp(54px,9vw,126px); line-height:.88; letter-spacing:-.075em; }}
.story-statement {{ margin:0; max-width:25ch; font-size:clamp(25px,3.2vw,45px); line-height:1.12; letter-spacing:-.035em; }}
.story-highlights {{ margin:30px 0 0; padding:0; display:flex; flex-wrap:wrap; gap:10px; list-style:none; }}
.story-highlights li {{ padding:8px 11px; border:1px solid var(--line); border-radius:999px; color:#444; font-size:13px; background:rgb(255 255 255 / .36); }}
.coverage {{ padding:20px 0 0 22px; border-left:3px solid var(--accent); }}
.coverage span {{ display:block; color:var(--muted); font-size:12px; text-transform:uppercase; letter-spacing:.1em; }}
.coverage strong {{ display:block; margin-top:8px; font-size:18px; }}
.coverage p {{ color:var(--muted); font-size:13px; }}
.hero-evidence {{ margin-top:24px; }}
.hero-evidence summary,.full-history>summary {{ cursor:pointer; width:max-content; list-style:none; padding-bottom:3px; border-bottom:1px solid var(--ink); font-size:13px; }}
.hero-evidence summary::-webkit-details-marker,.full-history>summary::-webkit-details-marker {{ display:none; }}
.stats {{ display:grid; grid-template-columns:1fr 1fr; gap:18px; margin-top:22px; }}
.stat {{ padding-top:14px; border-top:1px solid var(--line); }}
.stat strong {{ display:block; font-size:32px; letter-spacing:-.05em; }}
.stat span {{ color:var(--muted); font-size:12px; }}
main {{ background:var(--surface); }}
.section {{ padding:96px 0; border-bottom:1px solid var(--line); }}
.section-head {{ max-width:760px; margin-bottom:48px; }}
.section-head h2 {{ margin:0 0 12px; font-size:clamp(38px,6vw,72px); line-height:.95; letter-spacing:-.055em; }}
.section-head p {{ margin:0; color:var(--muted); font-size:18px; }}
.turns {{ max-width:960px; border-top:1px solid var(--line); }}
.turn {{ display:grid; grid-template-columns:84px 1fr; gap:24px; padding:30px 0; border-bottom:1px solid var(--line); }}
.turn-number {{ color:var(--accent); font:700 13px ui-monospace,SFMono-Regular,Menlo,monospace; }}
.turn-meta {{ display:flex; align-items:center; justify-content:space-between; gap:20px; color:var(--accent); font-size:12px; text-transform:uppercase; letter-spacing:.08em; }}
.turn-meta time {{ color:var(--muted); font:12px ui-monospace,SFMono-Regular,Menlo,monospace; text-transform:none; letter-spacing:0; }}
.turn h3 {{ margin:9px 0 8px; font-size:clamp(21px,3vw,30px); letter-spacing:-.03em; }}
.turn p {{ margin:0; color:var(--muted); font-size:13px; }}
.dialogue {{ margin-top:18px; padding:16px 18px; border-left:3px solid var(--accent); background:var(--paper); border-radius:0 10px 10px 0; }}
.dialogue p {{ display:grid; grid-template-columns:46px 1fr; gap:10px; margin:7px 0; color:#3f3f3f; font-size:14px; }}
.dialogue b {{ color:var(--accent); }}
.dialogue span {{ min-width:0; }}
.full-history {{ margin-top:42px; padding:22px; border-radius:var(--radius); background:var(--paper); }}
.full-history>p {{ max-width:680px; color:var(--muted); }}
.filters {{ display:flex; gap:8px; flex-wrap:wrap; margin:30px 0; }}
.filter {{ border:1px solid var(--line); background:transparent; color:var(--ink); padding:8px 12px; border-radius:9px; cursor:pointer; }}
.filter span {{ color:var(--muted); margin-left:4px; }}
.filter:hover,.filter.is-active {{ border-color:var(--ink); background:var(--ink); color:white; }}
.filter.is-active span {{ color:#c8c8c8; }}
.timeline {{ max-width:900px; }}
.event {{ display:grid; grid-template-columns:112px 18px 1fr; gap:18px; min-height:116px; }}
.event[hidden] {{ display:none; }}
.event-date {{ padding-top:2px; color:var(--muted); font:12px/1.4 ui-monospace,SFMono-Regular,Menlo,monospace; }}
.event-mark {{ position:relative; border-left:1px solid var(--line); }}
.event-mark::before {{ content:""; position:absolute; top:3px; left:-5px; width:9px; height:9px; border-radius:50%; background:var(--paper); border:2px solid var(--accent); }}
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
.dimension {{ padding:28px 0; border-top:1px solid var(--line); }}
.dimension-heading {{ display:flex; justify-content:space-between; align-items:baseline; gap:20px; }}
.dimension-heading h3 {{ margin:0; font-size:18px; }}
.dimension-heading strong {{ color:var(--accent); font-size:24px; letter-spacing:-.03em; }}
.dimension-copy {{ margin-top:18px; }}
.dimension-copy p {{ margin:10px 0; color:var(--muted); }}
.dimension-copy b {{ color:var(--ink); }}
.calculation {{ margin-top:18px; color:var(--muted); font-size:12px; }}
.calculation summary {{ cursor:pointer; width:max-content; }}
.calculation ul {{ max-width:520px; padding-left:18px; }}
.score-axis {{ position:relative; height:18px; margin:24px 5px 10px; border-top:1px solid var(--line); }}
.score-axis::before,.score-axis::after {{ content:""; position:absolute; top:-4px; height:7px; border-left:1px solid var(--line); }}
.score-axis::before {{ left:0; }} .score-axis::after {{ right:0; }}
.score-axis span {{ position:absolute; top:-7px; width:13px; height:13px; border:3px solid var(--surface); outline:2px solid var(--accent); border-radius:50%; background:var(--accent); transform:translateX(-50%); }}
.proof-list {{ display:grid; grid-template-columns:repeat(3,1fr); gap:28px; }}
.proof-card {{ padding-top:20px; border-top:3px solid var(--accent); }}
.proof-card h3 {{ margin:0 0 14px; font-size:24px; letter-spacing:-.03em; }}
.proof-card p {{ color:var(--muted); }}
.proof-card blockquote {{ margin:24px 0 0; padding:16px 0 0; border-top:1px solid var(--line); font-size:15px; }}
.career-grid {{ display:grid; grid-template-columns:repeat(3,1fr); gap:28px; }}
.career-grid article {{ padding:24px; background:var(--paper); border-radius:var(--radius); }}
.career-grid p,.career-grid li {{ color:#3f3f3f; }}
.career-grid ul {{ padding-left:20px; }}
.star-list {{ padding:0; list-style:none; }}
.star-list li {{ padding:12px 0; border-bottom:1px solid var(--line); }}
.star-list b,.star-list span {{ display:block; }}
.star-list b {{ margin-bottom:4px; color:var(--accent); font-size:12px; text-transform:uppercase; }}
.context-callout {{ display:grid; grid-template-columns:1fr 1fr; gap:50px; padding:30px; background:var(--paper); border-radius:var(--radius); }}
.context-callout li {{ margin:16px 0; font-size:18px; }}
.context-callout pre {{ margin:14px 0 0; padding:16px; overflow:auto; background:var(--ink); color:white; border-radius:10px; }}
.method {{ display:grid; grid-template-columns:1fr 1fr; gap:80px; }}
.method h3 {{ margin-top:0; }}
.method li {{ margin:10px 0; color:var(--muted); }}
.empty {{ color:var(--muted); }}
footer {{ padding:36px 0; background:var(--ink); color:white; }}
footer .shell {{ display:flex; justify-content:space-between; gap:30px; }}
footer span {{ color:#aaa; }}
@media (max-width:800px) {{
  .shell {{ width:min(100% - 28px,1180px); }} .nav {{ align-items:flex-start; }} .nav-right {{ flex-direction:column-reverse; align-items:flex-end; gap:8px; }} .nav-meta {{ max-width:230px; text-align:right; }}
  .masthead {{ min-height:auto; padding-bottom:32px; }} .hero,.friction-layout,.attention-grid,.method,.context-callout {{ grid-template-columns:1fr; gap:34px; }} .hero {{ padding:70px 0 34px; }} h1 {{ font-size:clamp(52px,17vw,86px); }} .coverage {{ max-width:440px; }} .section {{ padding:68px 0; }}
  .turn {{ grid-template-columns:44px 1fr; gap:14px; }} .turn-meta {{ align-items:flex-start; flex-direction:column; gap:5px; }} .event {{ grid-template-columns:84px 14px 1fr; gap:12px; }} .friction-row {{ grid-template-columns:34px 1fr; }} .ratio {{ grid-column:2; text-align:left; display:flex; align-items:baseline; gap:8px; }}
  .dimensions,.proof-list,.career-grid {{ grid-template-columns:1fr; }} .attention-row {{ grid-template-columns:100px 1fr; }} .attention-row span {{ grid-column:2; text-align:left; }}
}}
@media (max-width:420px) {{
  .shell {{ width:min(100% - 22px,1180px); }} .nav-meta {{ display:none; }} .story-statement {{ font-size:25px; }} .story-highlights {{ display:grid; }} .full-history {{ padding:16px; }}
  .event {{ grid-template-columns:1fr; min-height:auto; padding:16px 0; border-bottom:1px solid var(--line); }} .event-mark {{ display:none; }} .event-body {{ padding:0; }}
  .attention-row {{ grid-template-columns:1fr; gap:8px; }} .attention-row span {{ grid-column:1; }}
}}
@media (prefers-reduced-motion:reduce) {{ * {{ scroll-behavior:auto!important; transition:none!important; animation:none!important; }} }}
@media print {{ body,.section,main {{ background:white; }} .masthead {{ min-height:auto; }} .filters {{ display:none; }} .section {{ padding:36px 0; break-inside:avoid; }} .event {{ min-height:80px; }} footer {{ background:white; color:var(--ink); border-top:1px solid var(--line); }} details {{ display:block; }} details>summary {{ display:none; }} }}
</style>
</head>
<body>
<header class="masthead">
  <nav class="shell nav"><div class="wordmark">Build<i>Story</i></div><div class="nav-right"><div class="nav-meta">{esc(c['generated'])} · {generated_date}</div>{language_switch}</div></nav>
  <div class="shell hero">
    <div><div class="kicker">{esc(kicker)}</div><h1>{esc(p['name'])}</h1><p class="story-statement">{esc(data['story']['headline'])}</p><ul class="story-highlights">{highlights}</ul></div>
    <div><div class="coverage"><span>{esc(c['coverage'])}</span><strong>{esc(sources)}</strong><p>{esc(p['branch'])} · {esc(p['start'][:10])} {esc(date_connector)} {esc(p['end'][:10])}</p></div>
      <details class="hero-evidence"><summary>{esc(c['story_evidence'])}</summary><div class="stats"><div class="stat"><strong>{m['commits']}</strong><span>{esc(c['commits'])}</span></div><div class="stat"><strong>{m['files']}</strong><span>{esc(c['files'])}</span></div><div class="stat"><strong>{m['calendar_days']}</strong><span>{esc(c['days'])}</span></div><div class="stat"><strong>{m['time_estimate']['hours']}</strong><span>{esc(c['hours'])} · {esc(confidence_label(m['time_estimate']['confidence'], language))}</span></div></div></details>
    </div>
  </div>
</header>
<main>
  <section class="section"><div class="shell"><div class="section-head"><h2>{esc(c['turning_points'])}</h2><p>{esc(c['turning_points_intro'])}</p></div><div class="turns">{''.join(turning_rows)}</div><details class="full-history"><summary>{esc(c['full_timeline'])} · {esc(count_text(len(data['timeline']), 'commit', language))}</summary><p>{esc(c['full_timeline_intro'])}</p><div class="filters">{''.join(filters)}</div><div class="timeline">{''.join(timeline_rows)}</div></details></div></section>
  <section class="section"><div class="shell"><div class="section-head"><h2>{esc(c['friction'])}</h2><p>{esc(c['friction_intro'])}</p></div><div class="friction-layout"><div>{''.join(friction_rows)}</div><aside class="loops"><h3>{esc(c['loop_candidates'])}</h3>{''.join(loop_rows)}</aside></div></div></section>
  <section class="section"><div class="shell"><div class="section-head"><h2>{esc(c['attention'])}</h2><p>{esc(c['attention_intro'])}</p></div><div class="attention-grid"><div>{''.join(attention_rows)}</div><aside class="time-callout"><span class="confidence {esc(m['time_estimate']['confidence'])}">{esc(label_value(c['confidence'], confidence_label(m['time_estimate']['confidence'], language), language))}</span><strong>{m['time_estimate']['hours']}{'h' if language == 'en' else ' 小时'}</strong><p>{'Estimated from: ' if language == 'en' else '估算来源：'}{esc(source_label)}{'. ' if language == 'en' else '。'}{esc(c['git_limit'] if m['time_estimate']['source']=='git' else c['session_limit'])}</p></aside></div></div></section>
  <section class="section"><div class="shell"><div class="section-head"><h2>{esc(c['profile'])}</h2><p>{esc(c['profile_intro'])}</p></div><div class="dimensions">{''.join(dimension_rows)}</div></div></section>
  <section class="section"><div class="shell"><div class="section-head"><h2>{esc(c['proof'])}</h2><p>{esc(c['proof_intro'])}</p></div><div class="proof-list">{''.join(card_rows)}</div></div></section>
  <section class="section"><div class="shell"><div class="section-head"><h2>{esc(c['career_material'])}</h2><p>{esc(career_intro)}</p></div>{career_html}</div></section>
  <section class="section"><div class="shell method"><div><div class="section-head"><h2>{esc(c['method'])}</h2></div><p><strong>{esc(label_value(c['coverage'], sources, language))}</strong></p><ul>{limitations}</ul></div><div><h3>{esc(c['career_output_rule'])}</h3><p>{esc(c['career_confirmed_rule'] if career['confirmed'] else c['resume_prompt'])}</p><h3>{esc(c['local_first'])}</h3><p>{esc(c['local_first_detail'])}</p></div></div></section>
</main>
<footer><div class="shell"><strong>BuildStory</strong><span>{esc(c['footer'])}</span></div></footer>
<script type="application/json" id="buildstory-data">{source_data}</script>
<script>
document.querySelectorAll('.filter').forEach(function(button) {{ button.addEventListener('click', function() {{ document.querySelectorAll('.filter').forEach(function(item) {{ item.classList.remove('is-active'); }}); button.classList.add('is-active'); var selected = button.dataset.filter; document.querySelectorAll('.event').forEach(function(event) {{ event.hidden = selected !== 'all' && event.dataset.category !== selected; }}); }}); }});
</script>
</body>
</html>
'''

def write_outputs(
    data: dict[str, Any],
    output: Path,
    language_links: dict[str, str] | None = None,
    suffix: str = "",
) -> None:
    output.mkdir(parents=True, exist_ok=True)
    (output / f"evidence{suffix}.json").write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (output / f"report{suffix}.md").write_text(render_markdown(data), encoding="utf-8")
    (output / f"report{suffix}.html").write_text(render_html(data, language_links), encoding="utf-8")


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Turn a Git project history into an evidence-backed BuildStory report."
    )
    parser.add_argument("repo", nargs="?", default=".", help="Git repository to analyze. Defaults to the current directory.")
    parser.add_argument("--output", "-o", help="Output directory. Defaults to <repo>/build-story-report.")
    parser.add_argument("--session", action="append", default=[], help="Authorized session file or directory. Repeatable.")
    parser.add_argument("--context", help="Optional JSON file with user-confirmed role, outcome, decision, summary, and resume bullets.")
    parser.add_argument(
        "--language",
        choices=("en", "zh"),
        default="zh",
        help="Default language opened by report.html. Both English and Chinese reports are generated.",
    )
    parser.add_argument("--project-name", help="Override the project name shown in the report.")
    parser.add_argument("--version", action="version", version=f"BuildStory {VERSION}")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    repo = Path(args.repo).expanduser().resolve()
    output = Path(args.output).expanduser().resolve() if args.output else repo / "build-story-report"
    sessions = [Path(item).expanduser().resolve() for item in args.session]
    context_path = Path(args.context).expanduser().resolve() if args.context else None
    try:
        context = load_context(context_path)
        datasets = {
            language: build_evidence(repo, sessions, language, args.project_name, context)
            for language in ("en", "zh")
        }
        shared_links = {"en": "report.en.html", "zh": "report.zh.html"}
        for language, data in datasets.items():
            write_outputs(data, output, shared_links, suffix=f".{language}")
        primary_links = {
            "en": "report.html" if args.language == "en" else "report.en.html",
            "zh": "report.html" if args.language == "zh" else "report.zh.html",
        }
        write_outputs(datasets[args.language], output, primary_links)
    except (RuntimeError, OSError) as error:
        print(f"BuildStory error: {error}", file=sys.stderr)
        return 1
    print(f"BuildStory report created: {output}")
    print(f"  HTML: {output / 'report.html'}")
    print(f"  English HTML: {output / 'report.en.html'}")
    print(f"  Chinese HTML: {output / 'report.zh.html'}")
    print(f"  Markdown: {output / 'report.md'}")
    print(f"  Evidence: {output / 'evidence.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
