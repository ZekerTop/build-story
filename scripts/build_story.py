#!/usr/bin/env python3
"""BuildStory: local, evidence-first project retrospective generator.

The script uses only the Python standard library and Git. It writes JSON,
Markdown, and self-contained HTML reports without modifying source files.
"""

from __future__ import annotations

import argparse
import collections
import datetime as dt
import hashlib
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


VERSION = "0.4.0"
MAX_TRANSCRIPT_BYTES = 20 * 1024 * 1024
MAX_TRANSCRIPT_EVENTS = 20_000
SESSION_GAP_HOURS = 2.0
TRANSCRIPT_ACTIVE_GAP_MINUTES = 30.0
CONVERSATION_SEGMENT_GAP_MINUTES = 15.0


COPY = {
    "en": {
        "tagline": "See how you built it, not just what you built.",
        "generated": "Generated locally from project evidence",
        "coverage": "Evidence coverage",
        "story_kicker": "The build story",
        "story_fallback": "A project moved from its first implementation through visible friction to a reviewable delivery.",
        "story_evidence": "View supporting evidence",
        "rhythm": "Project rhythm",
        "rhythm_intro": "A project-scoped activity pulse. It shows when observable work happened, not how hard someone worked.",
        "project_span": "Project span",
        "active_days": "Active development days",
        "longest_streak": "Longest continuous run",
        "busiest_day": "Most active day",
        "conversation_events": "conversation events",
        "lines_changed": "lines changed",
        "day_story": "What happened",
        "related_turns": "Related turning points",
        "no_related_turns": "No selected turning point on this day",
        "story_map": "Decision spine",
        "story_map_intro": "Follow the decisions, reversals, and evidence that changed the project's direction.",
        "chapter_navigation": "Report sections",
        "no_activity": "No observable Git or conversation activity",
        "turning_points": "The turns that changed the project",
        "turning_points_intro": "Only the moments that changed direction, risk, understanding, or delivery state.",
        "full_timeline": "View every commit",
        "full_timeline_intro": "The complete Git history remains available as evidence, but it is not the story itself.",
        "friction": "Where the project fought back",
        "friction_intro": "High-change areas and loop candidates. These are prompts for review, not verdicts.",
        "journey_insights": "The story behind the rework",
        "journey_insights_intro": "BuildStory groups related changes into a tentative explanation, shows the evidence, and asks you to confirm what Git cannot know.",
        "attempted_path": "Attempted path",
        "current_judgment": "Current judgment",
        "evidence_basis": "Evidence basis",
        "needs_confirmation": "Needs your confirmation",
        "confirmed_context": "Your confirmation",
        "captured_lesson": "Lesson captured",
        "raw_change_evidence": "View file-level evidence",
        "no_journey_insights": "No theme-level rework story met the evidence threshold.",
        "communication_review": "Communication review",
        "communication_review_intro": "See which details became clear only after AI had already acted. This reviews how the human and AI aligned; it never scores the user's communication ability.",
        "original_request": "What you said",
        "ai_interpretation": "How AI responded",
        "later_correction": "What you clarified later",
        "communication_analysis": "Where the gap appeared",
        "communication_impact": "Observed project evidence",
        "missing_information": "Information that was missing",
        "next_time_say": "A clearer way to say it next time",
        "reusable_pattern": "Reusable pattern",
        "attribution": "Primary attribution",
        "no_communication_insights": "No correction chain met the evidence threshold. Short prompts are not treated as unclear by default.",
        "not_user_rewrite": "This is not primarily a user-wording problem, so BuildStory does not ask the user to make the prompt longer.",
        "insufficient_rewrite": "The evidence is not strong enough to support user-side guidance, so no rewrite is offered.",
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
        "confirmed": "confirmed",
        "none": "No signal found",
        "all": "All",
        "source_git": "Git history",
        "source_sessions": "authorized session transcripts",
        "git_limit": "Git records saved changes, not all thinking, experiments, or uncommitted work.",
        "session_limit": "Transcript analysis keeps only short excerpts needed for review; it never copies the full conversation.",
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
        "rhythm": "项目节奏",
        "rhythm_intro": "只展示项目范围内可观察到的活动脉搏。它说明工作何时发生，不评价一个人有多勤快。",
        "project_span": "项目跨度",
        "active_days": "活跃开发日",
        "longest_streak": "最长连续推进",
        "busiest_day": "变更最密集日",
        "conversation_events": "条会话",
        "lines_changed": "行变更",
        "day_story": "当天发生了什么",
        "related_turns": "对应转折点",
        "no_related_turns": "这一天没有选中的转折点",
        "story_map": "决策脊柱",
        "story_map_intro": "沿着改变项目方向的决定、回头和证据，重新走一遍这段历程。",
        "chapter_navigation": "报告章节",
        "no_activity": "未观察到 Git 或会话活动",
        "turning_points": "真正改变项目的转折点",
        "turning_points_intro": "只保留改变方向、风险、理解或交付状态的关键时刻。",
        "full_timeline": "查看全部提交",
        "full_timeline_intro": "完整 Git 历史仍然保留为证据，但它本身不是故事。",
        "friction": "项目在哪里卡住了",
        "friction_intro": "高频变更区域与循环候选。它们用于复盘，不是对人的判决。",
        "journey_insights": "反复背后的故事",
        "journey_insights_intro": "BuildStory 会把相关变更组织成一个待确认的解释，展示证据，再把 Git 无法知道的原因交给你确认。",
        "attempted_path": "尝试路径",
        "current_judgment": "当前判断",
        "evidence_basis": "判断依据",
        "needs_confirmation": "需要你确认",
        "confirmed_context": "你的确认",
        "captured_lesson": "沉淀的经验",
        "raw_change_evidence": "查看文件级证据",
        "no_journey_insights": "没有达到证据门槛的主题级反复故事。",
        "communication_review": "沟通复盘",
        "communication_review_intro": "看看哪些信息是在 AI 已经行动后才变清楚的。这里复盘的是人与 AI 如何对齐，不评价用户的表达能力。",
        "original_request": "当时怎么说",
        "ai_interpretation": "AI 当时怎么回应",
        "later_correction": "后来怎样补充",
        "communication_analysis": "偏差出现在哪里",
        "communication_impact": "观察到的项目证据",
        "missing_information": "当时缺少的信息",
        "next_time_say": "下次可以这样说",
        "reusable_pattern": "可以复用的表达方式",
        "attribution": "主要归因",
        "no_communication_insights": "没有达到证据门槛的沟通纠正链。BuildStory 不会因为一句话很短，就默认它表达不清。",
        "not_user_rewrite": "这不主要是用户表述问题，因此 BuildStory 不会要求用户把话说得更长。",
        "insufficient_rewrite": "现有证据不足以支持用户侧改写，因此这里不提供“下次怎么说”。",
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
        "confirmed": "已确认",
        "none": "未发现信号",
        "all": "全部",
        "source_git": "Git 历史",
        "source_sessions": "已授权的会话记录",
        "git_limit": "Git 只记录已保存的变更，无法覆盖全部思考、实验和未提交工作。",
        "session_limit": "会话分析只保留复盘所需的短摘录，不复制完整对话。",
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


JOURNEY_CLASSIFICATION_LABELS = {
    "en": {
        "blocked-loop": "Blocked loop",
        "necessary-exploration": "Necessary exploration",
        "direction-change": "Direction change",
    },
    "zh": {
        "blocked-loop": "失败循环",
        "necessary-exploration": "必要探索",
        "direction-change": "方向转变",
    },
}


COMMUNICATION_ATTRIBUTION_LABELS = {
    "en": {
        "user-expression-insufficient": "Information became clear later",
        "ai-ignored-explicit-requirement": "AI missed an explicit requirement",
        "term-meaning-mismatch": "The same term meant different things",
        "requirement-evolution": "The requirement evolved after seeing the result",
        "insufficient-evidence": "Not enough evidence to attribute",
    },
    "zh": {
        "user-expression-insufficient": "信息后来才补全",
        "ai-ignored-explicit-requirement": "AI 忽略了明确要求",
        "term-meaning-mismatch": "双方对同一个词理解不同",
        "requirement-evolution": "需求在看到结果后演化",
        "insufficient-evidence": "证据不足，无法归因",
    },
}


COMMUNICATION_GAP_LABELS = {
    "en": {
        "ambiguous-reference": "Ambiguous reference",
        "vague-goal": "Abstract goal",
        "missing-scope": "Scope clarified later",
        "missing-constraint": "Constraint clarified later",
        "missing-acceptance": "Acceptance criteria clarified later",
        "term-definition": "Term meaning clarified later",
        "ai-execution-miss": "Explicit requirement was missed",
        "requirement-evolution": "Requirement evolved after feedback",
        "insufficient-evidence": "Evidence is insufficient to attribute",
    },
    "zh": {
        "ambiguous-reference": "指代不够明确",
        "vague-goal": "目标比较抽象",
        "missing-scope": "范围在后续才明确",
        "missing-constraint": "约束在后续才明确",
        "missing-acceptance": "验收标准在后续才明确",
        "term-definition": "术语含义在后续才明确",
        "ai-execution-miss": "明确要求在执行中被遗漏",
        "requirement-evolution": "需求在看到结果后演化",
        "insufficient-evidence": "证据不足，暂不归因",
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
    allowed = {
        "role",
        "outcome",
        "key_decision",
        "summary",
        "resume_bullets",
        "translations",
        "insight_confirmations",
        "communication_confirmations",
    }
    result = {key: value[key] for key in allowed if key in value}
    if "resume_bullets" in result and not isinstance(result["resume_bullets"], list):
        result["resume_bullets"] = []
    if "translations" in result and not isinstance(result["translations"], dict):
        result["translations"] = {}
    if "insight_confirmations" in result and not isinstance(result["insight_confirmations"], dict):
        result["insight_confirmations"] = {}
    if "communication_confirmations" in result and not isinstance(result["communication_confirmations"], dict):
        result["communication_confirmations"] = {}
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


def redact_local_paths(text: str) -> str:
    text = re.sub(r"file:///(?:Users|home)/[^/\s<>\"']+", "~", text, flags=re.I)
    text = re.sub(r"(?<![\w])/(?:Users|home)/[^/\s<>\"']+", "~", text)
    text = re.sub(r"\b[A-Za-z]:\\Users\\[^\\\s<>\"']+", "~", text, flags=re.I)
    text = re.sub(
        r"(?<![\w])/(?:private/var|var/folders|tmp)/[^\s<>\"']+",
        "<local-path>",
        text,
    )
    return text


def sanitize_report_value(value: Any) -> Any:
    if isinstance(value, str):
        return redact_local_paths(value)
    if isinstance(value, list):
        return [sanitize_report_value(item) for item in value]
    if isinstance(value, dict):
        return {key: sanitize_report_value(item) for key, item in value.items()}
    return value


def is_injected_transcript_text(text: str) -> bool:
    return bool(
        re.search(
            r"<system-reminder>|<environment_context>|<in-app-browser-context>|<app-context>|"
            r"<skills_instructions>|<permissions instructions>|<collaboration_mode>|"
            r"^# AGENTS\.md instructions(?:\s+for\s+[^\n]+)?",
            text.strip(),
            re.I,
        )
    )


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


def build_journey_insights(
    commits: list[Commit],
    friction: list[dict[str, Any]],
    context: dict[str, Any],
    language: str,
) -> list[dict[str, Any]]:
    confirmations = context.get("insight_confirmations", {})
    if not isinstance(confirmations, dict):
        confirmations = {}
    results = []
    reversal_pattern = re.compile(r"\b(revert|rollback|back out|backout)\b|回滚|撤销", re.I)
    direction_pattern = re.compile(
        r"\b(replace|switch|remove|drop|abandon|simplify|migrate|deprecat(?:e|ed))\b|替代|替换|改为|移除|放弃|简化|迁移",
        re.I,
    )

    for zone in friction:
        path = zone["path"]
        related = [
            commit
            for commit in commits
            if any(item["path"] == path for item in commit.files)
        ]
        if len(related) < 3:
            continue

        explicit_reversals = [commit for commit in related if reversal_pattern.search(commit.subject)]
        direction_changes = [
            commit
            for commit in related
            if not reversal_pattern.search(commit.subject) and direction_pattern.search(commit.subject)
        ]
        repair_count = sum(
            commit.category in {"fix", "refactor"} and not reversal_pattern.search(commit.subject)
            for commit in related
        )
        validation_count = sum(commit.category == "validation" for commit in related)

        if explicit_reversals or direction_changes:
            classification = "direction-change"
            confidence = "high" if explicit_reversals else "medium"
        elif repair_count >= 2 and not validation_count:
            classification = "blocked-loop"
            confidence = "high" if repair_count >= 3 else "medium"
        else:
            classification = "necessary-exploration"
            confidence = "medium" if validation_count else "low"

        topic_commit = next(
            (commit for commit in related if commit.category == "feature"),
            next(
                (
                    commit
                    for commit in related
                    if commit.category not in {"foundation", "documentation", "delivery", "validation"}
                ),
                related[0],
            ),
        )
        topic = localized_dynamic_text(topic_commit.subject, context, language)
        alternative = direction_changes[-1] if direction_changes else None
        alternative_subject = (
            localized_dynamic_text(alternative.subject, context, language) if alternative else ""
        )

        if language == "zh":
            evidence_basis = (
                f"{len(related)} 次相关提交、{repair_count} 次修复或重构、"
                f"{len(explicit_reversals)} 次明确回滚、{len(direction_changes)} 个替代方向。"
            )
            if classification == "direction-change":
                hypothesis = "这更像一次方向转变，而不是失败循环。"
                if alternative_subject:
                    hypothesis += f"原方案在连续调整后被“{alternative_subject}”接替。"
                elif explicit_reversals:
                    hypothesis += "原方案在连续调整后被明确回滚。"
                question = f"你最终放弃或改变“{topic}”，主要是技术实现困难，还是产品判断？"
            elif classification == "blocked-loop":
                hypothesis = "这更像一个尚未收敛的失败循环：同一路径反复修复，但没有看到明确换向或验证闭环。"
                question = "这些反复修改的根因是什么？最后是否已经通过测试或真实使用得到验证？"
            else:
                hypothesis = "这更像必要探索：现有证据不足以把高频修改判定为浪费。"
                if validation_count:
                    hypothesis += " 相关尝试最终出现了验证收口。"
                question = "这些修改是在验证不同方案，还是被同一个问题反复卡住？最终哪条证据让你停止探索？"
        else:
            reversal_noun = "reversal" if len(explicit_reversals) == 1 else "reversals"
            direction_noun = "replacement direction" if len(direction_changes) == 1 else "replacement directions"
            evidence_basis = (
                f"{len(related)} related commits, {repair_count} fixes or refactors, "
                f"{len(explicit_reversals)} explicit {reversal_noun}, and "
                f"{len(direction_changes)} {direction_noun}."
            )
            if classification == "direction-change":
                hypothesis = "This looks more like a direction change than a failed loop."
                if alternative_subject:
                    hypothesis += f" After repeated adjustment, the original approach was replaced by “{alternative_subject}.”"
                elif explicit_reversals:
                    hypothesis += " The original approach was explicitly reversed after repeated adjustment."
                question = f"Did you abandon or change “{topic}” mainly because the implementation failed, or because the product judgment changed?"
            elif classification == "blocked-loop":
                hypothesis = "This looks like an unresolved blocked loop: the same path kept receiving fixes without a visible direction change or validation closure."
                question = "What was the root cause of the repeated changes, and was the final result verified by tests or real use?"
            else:
                hypothesis = "This looks more like necessary exploration: the evidence is not strong enough to label frequent change as waste."
                if validation_count:
                    hypothesis += " The related attempts eventually reached validation."
                question = "Were these changes testing distinct approaches, or repeatedly hitting the same problem? What evidence ended the exploration?"

        insight_id = f"path:{path}"
        confirmation_entry = confirmations.get(insight_id, confirmations.get(path))
        confirmation = None
        lesson = None
        confirmed_classification = None
        if isinstance(confirmation_entry, str):
            confirmation = confirmation_entry.strip() or None
        elif isinstance(confirmation_entry, dict):
            confirmed_classification = confirmation_entry.get("classification")
            confirmation = str(
                confirmation_entry.get("reason") or confirmation_entry.get("confirmation") or ""
            ).strip() or None
            lesson = str(confirmation_entry.get("lesson") or "").strip() or None
            confirmed_topic = str(confirmation_entry.get("topic") or "").strip()
            if confirmed_topic:
                topic = confirmed_topic
        if confirmation:
            if confirmed_classification in JOURNEY_CLASSIFICATION_LABELS[language]:
                classification = confirmed_classification
            confidence = "confirmed"
            hypothesis = (
                f"用户已确认：这段经历属于{JOURNEY_CLASSIFICATION_LABELS[language][classification]}。"
                if language == "zh"
                else f"User confirmed the current classification: {JOURNEY_CLASSIFICATION_LABELS[language][classification]}."
            )

        results.append(
            {
                "id": insight_id,
                "topic": topic,
                "classification": classification,
                "classification_label": JOURNEY_CLASSIFICATION_LABELS[language][classification],
                "confidence": confidence,
                "evidence_chain": [
                    {
                        "date": commit.timestamp.date().isoformat(),
                        "subject": localized_dynamic_text(commit.subject, context, language),
                        "original_subject": commit.subject,
                        "hash": commit.commit_hash[:8],
                        "category": commit.category,
                    }
                    for commit in related[:10]
                ],
                "hypothesis": hypothesis,
                "evidence_basis": evidence_basis,
                "question": question,
                "confirmation": confirmation,
                "lesson": lesson,
                "supporting_path": path,
            }
        )
    return results[:5]


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
        for key in ("text", "content", "message", "payload", "data", "prompt", "input", "output"):
            if key in value:
                text = flatten_text(value[key], depth + 1)
                if text:
                    return text
    return ""


def transcript_session_id(value: Any) -> str | None:
    if not isinstance(value, dict):
        return None
    for container in (
        value,
        value.get("message"),
        value.get("payload"),
        value.get("data"),
    ):
        if not isinstance(container, dict):
            continue
        session_id = (
            container.get("session_id")
            or container.get("sessionId")
            or container.get("conversation_id")
            or container.get("conversationId")
            or container.get("thread_id")
            or container.get("threadId")
        )
        if session_id:
            return str(session_id)[:160]
    payload = value.get("payload")
    if str(value.get("type") or "").lower() == "session_meta" and isinstance(payload, dict) and payload.get("id"):
        return str(payload["id"])[:160]
    if value.get("id") and any(
        isinstance(value.get(key), list)
        for key in ("messages", "events", "conversation", "conversations", "chat_messages")
    ):
        return str(value["id"])[:160]
    return None


def expand_transcript_values(value: Any) -> list[Any]:
    if not isinstance(value, dict):
        return [value]
    for key in ("messages", "events", "items", "conversation", "conversations", "chat_messages"):
        nested = value.get(key)
        if not isinstance(nested, list):
            continue
        inherited_session = transcript_session_id(value)
        expanded = []
        for item in nested:
            if inherited_session and isinstance(item, dict) and not transcript_session_id(item):
                item = {**item, "session_id": inherited_session}
            expanded.extend(expand_transcript_values(item))
        return expanded
    return [value]


def event_from_object(
    value: Any,
    source: str,
    source_key: str | None = None,
    default_session_id: str | None = None,
) -> dict[str, Any] | None:
    if not isinstance(value, dict):
        return None
    timestamp = None
    for key in ("timestamp", "created_at", "createdAt", "time", "ts", "date"):
        if key in value:
            timestamp = parse_datetime(value[key])
            if timestamp:
                break
    nested_role = None
    for key in ("message", "payload", "data"):
        nested = value.get(key)
        if isinstance(nested, dict) and nested.get("role"):
            nested_role = nested["role"]
            break
    role = str(value.get("role") or nested_role or value.get("type") or value.get("kind") or "unknown")
    lower_role = role.lower()
    if any(token in lower_role for token in ("assistant", "agent", "ai")):
        canonical_role = "assistant"
    elif any(token in lower_role for token in ("user", "human", "prompt")):
        canonical_role = "user"
    elif "system" in lower_role:
        canonical_role = "system"
    else:
        canonical_role = "other"
    text = redact_local_paths(re.sub(r"\s+", " ", flatten_text(value)).strip())
    if not timestamp and not text:
        return None
    session_id = transcript_session_id(value) or default_session_id or source
    result = {
        "timestamp": timestamp,
        "role": lower_role,
        "canonical_role": canonical_role,
        "text": text[:2000],
        "source": source,
        "source_key": source_key or source,
        "session_id": session_id,
    }
    return result


def read_transcript_events(paths: list[Path]) -> tuple[list[dict[str, Any]], list[str]]:
    events: list[dict[str, Any]] = []
    files: list[str] = []
    for path in iter_transcript_files(paths):
        files.append(path.name)
        source_key = hashlib.sha256(str(path).encode("utf-8")).hexdigest()[:16]
        source_event_index = 0
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
        expanded_values = []
        for value in values:
            expanded_values.extend(expand_transcript_values(value))
        values = expanded_values
        explicit_session_ids = {
            session_id
            for value in values
            if (session_id := transcript_session_id(value))
        }
        only_session_id = next(iter(explicit_session_ids)) if len(explicit_session_ids) == 1 else None
        orphan_run = 0
        inside_orphan_run = False
        for value in values:
            explicit_session_id = transcript_session_id(value)
            if explicit_session_id:
                default_session_id = explicit_session_id
                inside_orphan_run = False
            elif only_session_id:
                default_session_id = only_session_id
            elif len(explicit_session_ids) > 1:
                if not inside_orphan_run:
                    orphan_run += 1
                    inside_orphan_run = True
                default_session_id = f"{path.name}:orphan:{orphan_run}"
            else:
                default_session_id = path.name
            event = event_from_object(value, path.name, source_key, default_session_id)
            if event:
                event["event_index"] = source_event_index
                source_event_index += 1
                events.append(event)
                if len(events) >= MAX_TRANSCRIPT_EVENTS:
                    return events, files
    return events, files


def text_signature(text: str) -> set[str]:
    words = re.findall(r"[a-z0-9_]+|[\u4e00-\u9fff]{2,}", text.lower())
    return {word for word in words if word not in STOPWORDS and len(word) > 1}


def analyze_transcripts(events: list[dict[str, Any]], files: list[str], language: str) -> dict[str, Any]:
    conversation_events = [
        event
        for event in events
        if event.get("canonical_role") in {"user", "assistant"}
        and not is_injected_transcript_text(event.get("text", ""))
    ]
    timestamped = sorted(
        (event for event in conversation_events if event["timestamp"]),
        key=lambda event: event["timestamp"],
    )
    active_seconds = 0.0
    for previous, current in zip(timestamped, timestamped[1:]):
        gap = max(0.0, (current["timestamp"] - previous["timestamp"]).total_seconds())
        active_seconds += min(gap, TRANSCRIPT_ACTIVE_GAP_MINUTES * 60)

    user_events = [
        event
        for event in conversation_events
        if event.get("canonical_role") == "user" and len(event["text"]) >= 24
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
        for event in conversation_events
        if re.search(r"\b(error|failed|failure|exception|denied|timeout)\b|错误|失败|异常|拒绝|超时", event["text"], re.I)
    )
    return {
        "files": files,
        "events": len(conversation_events),
        "timestamped_events": len(timestamped),
        "estimated_active_hours": round(active_seconds / 3600, 1),
        "confidence": "medium" if len(timestamped) >= 10 else "low",
        "repeated_prompts": repeats[:10],
        "error_signals": error_events,
    }


def communication_signature(text: str) -> set[str]:
    lower = text.lower()
    tokens = {
        token
        for token in re.findall(r"[a-z0-9_]+", lower)
        if token not in STOPWORDS and len(token) > 1
    }
    ignored_bigrams = {
        "这个",
        "这些",
        "那个",
        "一下",
        "可以",
        "还是",
        "就是",
        "我的",
        "的是",
        "已经",
        "需要",
        "应该",
    }
    for run in re.findall(r"[\u4e00-\u9fff]{2,}", lower):
        if len(run) <= 6:
            tokens.add(run)
        tokens.update(
            run[index : index + 2]
            for index in range(len(run) - 1)
            if run[index : index + 2] not in ignored_bigrams
        )
    return tokens


def conversation_segments(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    segments: list[dict[str, Any]] = []
    for event in sorted(events, key=lambda item: item.get("event_index", 0)):
        role = event["canonical_role"]
        previous_time = segments[-1].get("timestamp_end") if segments else None
        current_time = event.get("timestamp")
        gap_seconds = (
            (current_time - previous_time).total_seconds()
            if previous_time is not None and current_time is not None
            else None
        )
        same_turn = gap_seconds is None or 0 <= gap_seconds <= CONVERSATION_SEGMENT_GAP_MINUTES * 60
        if segments and segments[-1]["canonical_role"] == role and same_turn:
            segment = segments[-1]
            segment["text"] = f"{segment['text']}\n{event['text']}"[:6000]
            segment["texts"].append(event["text"])
            segment["timestamp_end"] = event.get("timestamp") or segment.get("timestamp_end")
            segment["event_index_end"] = event.get("event_index", segment["event_index_end"])
            continue
        segments.append(
            {
                **event,
                "texts": [event["text"]],
                "timestamp_end": event.get("timestamp"),
                "event_index_end": event.get("event_index"),
            }
        )
    return segments


def localized_conversation_segment(
    segment: dict[str, Any], context: dict[str, Any], language: str
) -> str:
    texts = segment.get("texts") or [segment.get("text", "")]
    return "\n".join(
        localized_dynamic_text(str(text), context, language)
        for text in texts
        if str(text).strip()
    )[:400]


def build_communication_insights(
    events: list[dict[str, Any]],
    timeline: list[dict[str, Any]],
    context: dict[str, Any],
    language: str,
) -> list[dict[str, Any]]:
    if not events:
        return []

    confirmations = context.get("communication_confirmations", {})
    if not isinstance(confirmations, dict):
        confirmations = {}

    correction_pattern = re.compile(
        r"\b(no|not what i meant|i mean|i meant|what i mean is|instead of|you missed|you ignored|still|again|as i said|also needs? to|should|don't|do not)\b|"
        r"不是|不对|我说的是|我的意思是|我指的是|而不是|不要|别|你漏了|你没改|还是|又|我已经说了|也要|应该",
        re.I,
    )
    strong_clarification_pattern = re.compile(
        r"\b(not what i meant|i mean|what i mean is|to be clear|specifically|you missed|you ignored|as i said|i already said)\b|"
        r"我说的是|我的意思是|我指的是|具体包括|更具体地说|也就是说|你漏了|你没改|我已经说了|之前说过",
        re.I,
    )
    blame_pattern = re.compile(
        r"\b(you missed|you ignored|still|again|as i said|i already said)\b|"
        r"你漏了|你没改|还是|又|我已经说了|之前说过",
        re.I,
    )
    explicit_blame_pattern = re.compile(
        r"\b(you missed|you ignored|as i said|i already said)\b|你漏了|你没改|我已经说了|之前说过",
        re.I,
    )
    evolution_pattern = re.compile(
        r"\b(after seeing|now i think|let's change|i'd rather|next|on top of that|also add)\b|"
        r"看了以后|看到.*后|现在我觉得|再加一个|接下来|在这个基础上|其实我更想|另外再|顺便",
        re.I,
    )
    definition_pattern = re.compile(
        r"\b(i mean|what i mean is|by .+ i mean|not .+ but|refers to)\b|我说的.+是|这里的.+指|不是.+而是",
        re.I,
    )
    vague_reference_pattern = re.compile(
        r"\b(this|that|it|these|those|here|above|same as above)\b|这个|这些|那个|那里|这里|上面|进去|它",
        re.I,
    )
    vague_goal_pattern = re.compile(
        r"\b(make it better|improve it|clean it up|make it nicer|make it cooler|optimize it|fix it)\b|"
        r"优化一下|好看一点|更好看|更炫酷|简单一点|处理一下|弄一下|改一下|还是不对|再改一下",
        re.I,
    )
    constraint_pattern = re.compile(
        r"\b(only|do not|don't|keep|must|without changing|leave .+ unchanged)\b|只|不要|别|保留|必须|仅|不能|不要动",
        re.I,
    )
    scope_pattern = re.compile(
        r"\b(both|including|all|also|not only|every)\b|包括|以及|也要|全部|所有|不只是|同时|都要",
        re.I,
    )
    acceptance_pattern = re.compile(
        r"\b(expected|verify|test|must pass|after clicking|at \d+px)\b|完成后|验收|测试|点击后|不能.*滚动|在\s*\d+\s*px",
        re.I,
    )
    clarification_pattern = re.compile(
        r"\b(which|do you mean|would you like|should i|can you clarify|could you clarify)\b|"
        r"你更想|请确认|是指|需要我|能否说明",
        re.I,
    )

    grouped: dict[tuple[str, str], list[dict[str, Any]]] = collections.defaultdict(list)
    for event in events:
        if event.get("canonical_role") not in {"user", "assistant"} or not event.get("text"):
            continue
        text = event["text"]
        if is_injected_transcript_text(text):
            continue
        grouped[
            (
                event.get("source_key", event.get("source", "session")),
                event.get("session_id", event.get("source_key", event.get("source", "session"))),
            )
        ].append(event)

    results: list[dict[str, Any]] = []
    for _group_key, group in grouped.items():
        segments = conversation_segments(group)
        for index in range(len(segments) - 2):
            original, response, correction = segments[index : index + 3]
            if [original["canonical_role"], response["canonical_role"], correction["canonical_role"]] != [
                "user",
                "assistant",
                "user",
            ]:
                continue
            if clarification_pattern.search(response["text"]) or response["text"].strip().endswith(("?", "？")):
                continue
            if original.get("timestamp") and correction.get("timestamp_end"):
                gap = (correction["timestamp_end"] - original["timestamp"]).total_seconds()
                if gap < 0 or gap > 24 * 3600:
                    continue

            original_raw = original["text"][:400]
            response_raw = response["text"][:400]
            correction_raw = correction["text"][:400]
            if not (correction_pattern.search(correction_raw) or evolution_pattern.search(correction_raw)):
                continue

            original_terms = communication_signature(original_raw)
            correction_terms = communication_signature(correction_raw)
            response_terms = communication_signature(response_raw)
            shared_terms = original_terms & correction_terms
            new_terms = correction_terms - original_terms
            new_information_ratio = len(new_terms) / max(1, len(correction_terms))
            repeat_ratio = len(shared_terms) / max(1, len(original_terms))
            if (
                not shared_terms
                and not definition_pattern.search(correction_raw)
                and not evolution_pattern.search(correction_raw)
            ):
                continue

            original_has_constraint = bool(constraint_pattern.search(original_raw))
            original_has_scope = bool(scope_pattern.search(original_raw))
            original_has_acceptance = bool(acceptance_pattern.search(original_raw))
            original_is_explicit = original_has_constraint or original_has_scope or original_has_acceptance
            vague_reference = bool(vague_reference_pattern.search(original_raw))
            vague_goal = bool(vague_goal_pattern.search(original_raw))
            cleaned_correction_raw = re.sub(
                r"^(no[,.:\- ]*|not what i meant[,.:\- ]*|i mean(?: that)?[,.:\- ]*|i meant(?: that)?[,.:\- ]*|what i mean is[,.:\- ]*|"
                r"不对[，,。 ]*|不是这个[，,。 ]*|我说的是[：:，, ]*|我的意思是[：:，, ]*|我指的是[：:，, ]*|等一下[，,。 ]*)",
                "",
                correction_raw,
                flags=re.I,
            ).strip()
            correction_has_constraint = bool(constraint_pattern.search(correction_raw))
            correction_has_scope = bool(scope_pattern.search(correction_raw))
            correction_has_acceptance = bool(acceptance_pattern.search(correction_raw))
            later_adds_dimension = (
                (correction_has_constraint and not original_has_constraint)
                or (correction_has_scope and not original_has_scope)
                or (correction_has_acceptance and not original_has_acceptance)
            )
            meaningful_length = 12 if re.search(r"[\u4e00-\u9fff]", cleaned_correction_raw) else 28
            later_adds_specificity = (
                len(cleaned_correction_raw) >= meaningful_length and len(new_terms) >= 3
            )

            classification = "insufficient-evidence"
            if evolution_pattern.search(correction_raw) and not explicit_blame_pattern.search(correction_raw):
                classification = "requirement-evolution"
            elif definition_pattern.search(correction_raw) and response_terms & correction_terms:
                classification = "term-meaning-mismatch"
            elif (
                original_is_explicit
                and blame_pattern.search(correction_raw)
                and repeat_ratio >= 0.35
                and new_information_ratio <= 0.45
            ):
                classification = "ai-ignored-explicit-requirement"
            elif (
                strong_clarification_pattern.search(correction_raw)
                and new_information_ratio >= 0.35
                and (
                    ((vague_reference or vague_goal) and (later_adds_dimension or later_adds_specificity))
                    or (not original_is_explicit and later_adds_dimension)
                )
            ):
                classification = "user-expression-insufficient"
            if classification == "insufficient-evidence":
                continue

            if vague_reference:
                inferred_gap_type = "ambiguous-reference"
            elif vague_goal:
                inferred_gap_type = "vague-goal"
            elif correction_has_constraint and not original_has_constraint:
                inferred_gap_type = "missing-constraint"
            elif correction_has_acceptance and not original_has_acceptance:
                inferred_gap_type = "missing-acceptance"
            else:
                inferred_gap_type = "missing-scope"

            if language == "zh":
                missing_by_type = {
                    "ambiguous-reference": ["具体对象", "修改范围"],
                    "vague-goal": ["可观察的目标", "优先级", "不需要改动的部分"],
                    "missing-scope": ["完整影响范围", "不在范围内的内容"],
                    "missing-constraint": ["必须保留的行为", "明确禁区"],
                    "missing-acceptance": ["完成标准", "验证方式"],
                    "term-definition": ["核心术语的具体含义", "不包含的解释"],
                    "ai-execution-miss": [],
                    "requirement-evolution": [],
                    "insufficient-evidence": [],
                }
                pattern_by_type = {
                    "ambiguous-reference": "请修改[具体对象]中的[具体部分]，目标是[预期结果]；不要改动[边界]。",
                    "vague-goal": "我的目标是[用户可见结果]。请优先调整[具体方面]，不要增加[不需要的内容]；完成标准是[可检查结果]。",
                    "missing-scope": "请把[明确范围]都改为[目标状态]；保留[不变部分]；范围外不要修改。",
                    "missing-constraint": "请完成[目标]，但不要修改[边界]；必须保留[已有行为]。",
                    "missing-acceptance": "请完成[目标]；完成后用[测试、尺寸或操作步骤]验证，并告诉我结果。",
                    "term-definition": "我说的[术语]是[具体含义]，不是[容易混淆的解释]；目标是[预期结果]。",
                    "ai-execution-miss": None,
                    "requirement-evolution": None,
                    "insufficient-evidence": None,
                }
                analysis_by_class = {
                    "user-expression-insufficient": "最初的说法给 AI 留出了多个合理解释，后续补充才把对象、范围或约束变得唯一。",
                    "ai-ignored-explicit-requirement": "最初要求已经包含明确边界，后续仍需重复。主要问题更像 AI 执行遗漏，而不是用户需要把话说得更长。",
                    "term-meaning-mismatch": "双方围绕同一个词继续对话，但这个词指向的对象并不相同。",
                    "requirement-evolution": "这是看到结果后形成的新判断，更像正常需求演化，不应倒推为最初表达失败。",
                    "insufficient-evidence": "现有链只能说明后来发生了澄清，无法公平判断是信息缺失、执行遗漏还是需求变化。",
                }
                question_by_class = {
                    "user-expression-insufficient": "这次是信息一开始没有说完整，还是你看到结果后才形成更具体的判断？",
                    "ai-ignored-explicit-requirement": "原始要求是否已经足够明确，只是 AI 执行时遗漏了它？",
                    "term-meaning-mismatch": "这里是否更像双方对同一个词的理解不同？",
                    "requirement-evolution": "这是看到结果后自然形成的新判断吗？",
                    "insufficient-evidence": "你能否确认这次更接近信息后补、AI 执行遗漏，还是需求自然变化？",
                }
            else:
                missing_by_type = {
                    "ambiguous-reference": ["the exact object", "the change boundary"],
                    "vague-goal": ["an observable goal", "the priority", "what should not change"],
                    "missing-scope": ["the complete scope", "what remains out of scope"],
                    "missing-constraint": ["behavior that must remain", "explicit non-goals"],
                    "missing-acceptance": ["the acceptance criteria", "the verification method"],
                    "term-definition": ["the exact meaning of the core term", "the interpretation to exclude"],
                    "ai-execution-miss": [],
                    "requirement-evolution": [],
                    "insufficient-evidence": [],
                }
                pattern_by_type = {
                    "ambiguous-reference": "Change [specific part] of [specific object] to achieve [expected result]; do not change [boundary].",
                    "vague-goal": "My goal is [user-visible result]. Prioritize [specific aspect], avoid [unwanted change], and verify [observable outcome].",
                    "missing-scope": "Apply [target state] to [complete scope]; preserve [unchanged part], and leave everything else untouched.",
                    "missing-constraint": "Complete [goal], but do not change [boundary]; preserve [existing behavior].",
                    "missing-acceptance": "Complete [goal], then verify it with [test, viewport, or reproduction steps] and report the result.",
                    "term-definition": "By [term], I mean [exact meaning], not [likely interpretation]; the expected result is [outcome].",
                    "ai-execution-miss": None,
                    "requirement-evolution": None,
                    "insufficient-evidence": None,
                }
                analysis_by_class = {
                    "user-expression-insufficient": "The initial wording allowed multiple reasonable interpretations. The later clarification made the object, scope, or constraint unique.",
                    "ai-ignored-explicit-requirement": "The initial request already contained a clear boundary, yet it had to be repeated. This looks more like an AI execution miss than a need for a longer prompt.",
                    "term-meaning-mismatch": "Both sides kept using the same term, but the term referred to different things.",
                    "requirement-evolution": "This judgment formed after seeing the result. It is normal requirement evolution, not evidence that the initial request was defective.",
                    "insufficient-evidence": "The visible chain shows that clarification happened, but it cannot fairly distinguish missing information, an AI execution miss, or normal requirement change.",
                }
                question_by_class = {
                    "user-expression-insufficient": "Was this information missing at the start, or did the more specific judgment form only after you saw the result?",
                    "ai-ignored-explicit-requirement": "Was the original request already clear enough, with AI simply missing the requirement during execution?",
                    "term-meaning-mismatch": "Was this mainly a case of both sides assigning different meanings to the same term?",
                    "requirement-evolution": "Did this judgment naturally form only after you saw the result?",
                    "insufficient-evidence": "Can you confirm whether this was information added later, an AI execution miss, or a normal requirement change?",
                }

            original_text = localized_conversation_segment(original, context, language)
            response_text = localized_conversation_segment(response, context, language)
            correction_text = localized_conversation_segment(correction, context, language)
            cleaned_correction = re.sub(
                r"^(no[,.:\- ]*|not what i meant[,.:\- ]*|i mean(?: that)?[,.:\- ]*|i meant(?: that)?[,.:\- ]*|what i mean is[,.:\- ]*|"
                r"不对[，,。 ]*|不是这个[，,。 ]*|我说的是[：:，, ]*|我的意思是[：:，, ]*|我指的是[：:，, ]*|等一下[，,。 ]*)",
                "",
                correction_text,
                flags=re.I,
            ).strip()
            default_rewrite = None
            if language == "zh" and len(cleaned_correction) >= 8:
                default_rewrite = (
                    f"请按这个完整要求执行：{cleaned_correction.rstrip('。！!')}。"
                    "开始前先复述你理解的目标、范围和不改动的部分。"
                )
            elif language == "en" and len(cleaned_correction) >= 12:
                default_rewrite = (
                    f"Please follow this complete requirement: {cleaned_correction.rstrip('.!')}. "
                    "Before changing anything, restate the goal, scope, and what must remain unchanged."
                )

            related_commits = []
            correction_time = correction.get("timestamp_end") or correction.get("timestamp")
            if correction_time:
                for commit in timeline:
                    commit_time = parse_datetime(commit.get("timestamp"))
                    if commit_time is None:
                        continue
                    seconds = (commit_time - correction_time).total_seconds()
                    commit_terms = communication_signature(
                        str(commit.get("original_subject") or commit.get("subject") or "")
                    )
                    if 0 <= seconds <= 24 * 3600 and commit_terms & (original_terms | correction_terms):
                        related_commits.append(
                            {
                                "date": commit["date"],
                                "subject": commit["subject"],
                                "hash": commit["short_hash"],
                            }
                        )
            if related_commits:
                impact = (
                    f"澄清后 24 小时内观察到 {len(related_commits)} 次主题相关提交；时间接近不等同于因果。"
                    if language == "zh"
                    else f"{len(related_commits)} topic-overlapping commit(s) appeared within 24 hours of the clarification; timing alone does not prove causation."
                )
            else:
                impact = (
                    "没有找到足够接近的 Git 提交，影响目前只由对话证据支持。"
                    if language == "zh"
                    else "No sufficiently close Git commit was found, so the impact is supported only by conversation evidence."
                )

            digest = hashlib.sha256(
                (
                    f"{original.get('source')}\0{original.get('session_id')}\0"
                    f"{original.get('event_index')}\0{original.get('timestamp')}\0"
                    f"{original['text']}\0{correction['text']}"
                ).encode("utf-8")
            ).hexdigest()[:12]
            insight_id = f"communication:{digest}"
            confirmation_entry = confirmations.get(insight_id)
            confirmation = None
            lesson = None
            confirmed_rewrite = None
            confirmed_topic = None
            confirmed_analysis = None
            if isinstance(confirmation_entry, dict):
                confirmed_attribution = confirmation_entry.get("attribution")
                if confirmed_attribution in COMMUNICATION_ATTRIBUTION_LABELS[language]:
                    classification = confirmed_attribution
                confirmation = str(
                    confirmation_entry.get("reason") or confirmation_entry.get("confirmation") or ""
                ).strip() or None
                confirmed_analysis = str(confirmation_entry.get("analysis") or "").strip() or None
                confirmed_rewrite = str(confirmation_entry.get("improved_request") or "").strip() or None
                lesson = str(confirmation_entry.get("lesson") or "").strip() or None
                confirmed_topic = str(confirmation_entry.get("topic") or "").strip() or None

            if classification == "term-meaning-mismatch":
                gap_type = "term-definition"
            elif classification == "ai-ignored-explicit-requirement":
                gap_type = "ai-execution-miss"
            elif classification == "requirement-evolution":
                gap_type = "requirement-evolution"
            elif classification == "insufficient-evidence":
                gap_type = "insufficient-evidence"
            else:
                gap_type = inferred_gap_type

            user_guidance_allowed = classification in {
                "user-expression-insufficient",
                "term-meaning-mismatch",
            }
            suggested_rewrite = None
            if user_guidance_allowed:
                suggested_rewrite = confirmed_rewrite or default_rewrite
            missing_information = missing_by_type[gap_type] if user_guidance_allowed else []
            reusable_pattern = pattern_by_type[gap_type] if user_guidance_allowed else None
            topic = confirmed_topic or COMMUNICATION_GAP_LABELS[language][gap_type]
            analysis = confirmed_analysis or analysis_by_class[classification]

            confidence = "confirmed" if confirmation else (
                "high" if classification in {"ai-ignored-explicit-requirement", "term-meaning-mismatch"} else "medium"
            )
            results.append(
                {
                    "id": insight_id,
                    "topic": topic,
                    "gap_type": gap_type,
                    "gap_label": COMMUNICATION_GAP_LABELS[language][gap_type],
                    "attribution": classification,
                    "attribution_label": COMMUNICATION_ATTRIBUTION_LABELS[language][classification],
                    "confidence": confidence,
                    "original_request": original_text,
                    "ai_response": response_text,
                    "later_clarification": correction_text,
                    "analysis": analysis,
                    "missing_information": missing_information,
                    "suggested_rewrite": suggested_rewrite,
                    "reusable_pattern": reusable_pattern,
                    "question": question_by_class[classification],
                    "observed_impact": impact,
                    "related_commits": related_commits[:3],
                    "source": original.get("source"),
                    "event_range": [original.get("event_index"), correction.get("event_index_end")],
                    "confirmation": confirmation,
                    "lesson": lesson,
                }
            )

    priority = {
        "ai-ignored-explicit-requirement": 0,
        "term-meaning-mismatch": 1,
        "requirement-evolution": 2,
        "user-expression-insufficient": 3,
        "insufficient-evidence": 4,
    }
    confidence_priority = {"confirmed": 0, "high": 1, "medium": 2, "low": 3}
    results.sort(
        key=lambda item: (
            confidence_priority.get(item["confidence"], 9),
            priority.get(item["attribution"], 9),
            item["source"] or "",
            item["event_range"][0] or 0,
        )
    )
    return results[:3]


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


def build_activity_history(
    commits: list[Commit],
    transcript_events: list[dict[str, Any]],
    context: dict[str, Any],
    language: str,
) -> dict[str, Any]:
    start = commits[0].timestamp.date()
    end = commits[-1].timestamp.date()
    rows: dict[str, dict[str, Any]] = collections.defaultdict(
        lambda: {
            "commits": 0,
            "transcript_events": 0,
            "lines_changed": 0,
            "subjects": [],
            "prompts": [],
        }
    )
    for commit in commits:
        day = commit.timestamp.date().isoformat()
        row = rows[day]
        row["commits"] += 1
        row["lines_changed"] += commit.additions + commit.deletions
        row["subjects"].append(localized_dynamic_text(commit.subject, context, language))

    for event in transcript_events:
        timestamp = event.get("timestamp")
        if (
            event.get("canonical_role") not in {"user", "assistant"}
            or is_injected_transcript_text(event.get("text", ""))
            or timestamp is None
            or timestamp.date() < start
            or timestamp.date() > end
        ):
            continue
        day = timestamp.date().isoformat()
        row = rows[day]
        row["transcript_events"] += 1
        if event.get("canonical_role") == "user" and event.get("text"):
            row["prompts"].append(localized_dynamic_text(event["text"][:180], context, language))

    total_days = (end - start).days + 1
    active_dates = sorted(
        dt.date.fromisoformat(day)
        for day, row in rows.items()
        if row["commits"] or row["transcript_events"]
    )
    longest_streak = 0
    current_streak = 0
    previous: dt.date | None = None
    for day in active_dates:
        current_streak = current_streak + 1 if previous and day == previous + dt.timedelta(days=1) else 1
        longest_streak = max(longest_streak, current_streak)
        previous = day

    maximum_events = max(
        (row["commits"] + row["transcript_events"] for row in rows.values()),
        default=1,
    )
    days = []
    for offset in range(total_days):
        date_value = start + dt.timedelta(days=offset)
        day = date_value.isoformat()
        source = rows[day]
        observed_events = source["commits"] + source["transcript_events"]
        level = 0 if observed_events == 0 else max(1, min(4, math.ceil(observed_events / maximum_events * 4)))
        summaries = source["subjects"] or source["prompts"]
        summary = ("；" if language == "zh" else "; ").join(summaries[:2]) if summaries else COPY[language]["no_activity"]
        days.append(
            {
                "date": day,
                "commits": source["commits"],
                "transcript_events": source["transcript_events"],
                "lines_changed": source["lines_changed"],
                "observed_events": observed_events,
                "level": level,
                "summary": summary,
            }
        )

    active_rows = [row for row in days if row["observed_events"]]
    busiest = max(
        active_rows,
        key=lambda row: (
            row["observed_events"],
            row["commits"],
            row["lines_changed"],
            -dt.date.fromisoformat(row["date"]).toordinal(),
        ),
    )
    return {
        "start": start.isoformat(),
        "end": end.isoformat(),
        "calendar_days": total_days,
        "active_days": len(active_dates),
        "longest_streak": longest_streak,
        "leading_empty_days": start.weekday(),
        "weeks": math.ceil((start.weekday() + total_days) / 7),
        "busiest_day": busiest,
        "days": days,
    }


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
        (
            event
            for event in transcript_events
            if event.get("timestamp")
            and event.get("text")
            and event.get("canonical_role") in {"user", "assistant"}
            and not is_injected_transcript_text(event.get("text", ""))
        ),
        key=lambda event: event["timestamp"],
    )
    users = [
        event
        for event in timestamped
        if event.get("canonical_role") == "user"
    ]
    assistants = [
        event
        for event in timestamped
        if event.get("canonical_role") == "assistant"
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
    journey_insights: list[dict[str, Any]],
    communication_insights: list[dict[str, Any]],
    signals: dict[str, Any],
    attention: list[dict[str, Any]],
    context: dict[str, Any],
    language: str,
) -> dict[str, Any]:
    explicit_reverts = sum(item["type"] == "explicit-reversal" for item in loops)
    confirmed_direction_changes = sum(
        item["classification"] == "direction-change" and bool(item.get("confirmation"))
        for item in journey_insights
    )
    pending_direction_changes = sum(
        item["classification"] == "direction-change" and not item.get("confirmation")
        for item in journey_insights
    )
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
    if pending_direction_changes:
        highlights.append(
            f"{pending_direction_changes} direction {'change' if pending_direction_changes == 1 else 'changes'} to confirm"
            if language == "en"
            else f"{pending_direction_changes} 次方向转变待确认"
        )
    elif confirmed_direction_changes:
        highlights.append(
            f"{confirmed_direction_changes} confirmed direction {'change' if confirmed_direction_changes == 1 else 'changes'}"
            if language == "en"
            else f"{confirmed_direction_changes} 次已确认的方向转变"
        )
    review_insights = sum(not item.get("confirmation") for item in journey_insights)
    if review_insights:
        highlights.append(
            f"{review_insights} evidence-backed {'question' if review_insights == 1 else 'questions'} for review"
            if language == "en"
            else f"{review_insights} 个有证据的问题需要复盘"
        )
    if communication_insights:
        confirmed_communication = sum(bool(item.get("confirmation")) for item in communication_insights)
        highlights.append(
            (
                f"{confirmed_communication} confirmed communication {'example' if confirmed_communication == 1 else 'examples'}"
                if confirmed_communication
                else f"{len(communication_insights)} communication {'example' if len(communication_insights) == 1 else 'examples'} to review"
            )
            if language == "en"
            else (
                f"{confirmed_communication} 个已确认的沟通案例"
                if confirmed_communication
                else f"{len(communication_insights)} 个沟通案例需要复盘"
            )
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
    confirmed_story_context = any(
        context.get(key)
        for key in (
            "role",
            "outcome",
            "key_decision",
            "summary",
            "insight_confirmations",
            "communication_confirmations",
        )
    )
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
    journey_insights = build_journey_insights(commits, friction, localized_context, language)
    localized_loops = []
    for item in loops:
        row = dict(item)
        row["original_title"] = item["title"]
        row["title"] = localized_dynamic_text(item["title"], localized_context, language)
        localized_loops.append(row)
    activity = build_activity_history(commits, transcript_events, localized_context, language)
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
    communication_insights = build_communication_insights(
        transcript_events, timeline, localized_context, language
    )
    if transcript_analysis is not None:
        transcript_analysis["communication_insights"] = len(communication_insights)
    turning_points = select_turning_points(timeline, language)
    turning_points = attach_dialogue_to_turning_points(
        turning_points, transcript_events, localized_context, language
    )
    story = build_story_summary(
        name,
        timeline,
        localized_loops,
        journey_insights,
        communication_insights,
        signals,
        attention,
        localized_context,
        language,
    )
    career_material = build_career_material(name, story, localized_context, turning_points, language)
    source_list = ["git"] + (["transcripts"] if transcript_files else [])
    result = {
        "schema_version": "1.5",
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
        "activity": activity,
        "turning_points": turning_points,
        "journey_insights": journey_insights,
        "communication_insights": communication_insights,
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
    return sanitize_report_value(result)


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
    lines.extend(["", "</details>", "", f"## {c['journey_insights']}", "", f"> {c['journey_insights_intro']}", ""])
    if data["journey_insights"]:
        for insight in data["journey_insights"]:
            lines.extend(
                [
                    f"### {insight['topic']} · {insight['classification_label']}",
                    "",
                    f"- **{c['current_judgment']}：** {insight['hypothesis']}" if language == "zh" else f"- **{c['current_judgment']}:** {insight['hypothesis']}",
                    f"- **{c['evidence_basis']}：** {insight['evidence_basis']}" if language == "zh" else f"- **{c['evidence_basis']}:** {insight['evidence_basis']}",
                    f"- **{c['attempted_path']}：**" if language == "zh" else f"- **{c['attempted_path']}:**",
                ]
            )
            for evidence in insight["evidence_chain"]:
                lines.append(f"  - `{evidence['date']}` {evidence['subject']} (`{evidence['hash']}`)")
            if insight.get("confirmation"):
                lines.append(
                    f"- **{c['confirmed_context']}：** {insight['confirmation']}"
                    if language == "zh"
                    else f"- **{c['confirmed_context']}:** {insight['confirmation']}"
                )
                if insight.get("lesson"):
                    lines.append(
                        f"- **{c['captured_lesson']}：** {insight['lesson']}"
                        if language == "zh"
                        else f"- **{c['captured_lesson']}:** {insight['lesson']}"
                    )
            else:
                lines.append(
                    f"- **{c['needs_confirmation']}：** {insight['question']}"
                    if language == "zh"
                    else f"- **{c['needs_confirmation']}:** {insight['question']}"
                )
            lines.append("")
    else:
        lines.extend([f"- {c['no_journey_insights']}", ""])

    lines.extend(["<details>", f"<summary>{c['raw_change_evidence']}</summary>", "", f"### {c['friction']}", ""])
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
    lines.extend(["", "</details>"])
    if "transcripts" in data["coverage"]["sources"]:
        lines.extend(["", f"## {c['communication_review']}", "", f"> {c['communication_review_intro']}", ""])
        if data["communication_insights"]:
            for insight in data["communication_insights"]:
                lines.extend(
                    [
                        f"### {insight['topic']} · {insight['attribution_label']}",
                        "",
                        f"- **{c['original_request']}：** {insight['original_request']}" if language == "zh" else f"- **{c['original_request']}:** {insight['original_request']}",
                        f"- **{c['later_correction']}：** {insight['later_clarification']}" if language == "zh" else f"- **{c['later_correction']}:** {insight['later_clarification']}",
                        f"- **{c['communication_analysis']}：** {insight['analysis']}" if language == "zh" else f"- **{c['communication_analysis']}:** {insight['analysis']}",
                        f"- **{c['communication_impact']}：** {insight['observed_impact']}" if language == "zh" else f"- **{c['communication_impact']}:** {insight['observed_impact']}",
                    ]
                )
                if insight.get("missing_information"):
                    lines.append(
                        f"- **{c['missing_information']}：** {'、'.join(insight['missing_information'])}"
                        if language == "zh"
                        else f"- **{c['missing_information']}:** {', '.join(insight['missing_information'])}"
                    )
                if insight.get("suggested_rewrite"):
                    lines.append(
                        f"- **{c['next_time_say']}：** {insight['suggested_rewrite']}"
                        if language == "zh"
                        else f"- **{c['next_time_say']}:** {insight['suggested_rewrite']}"
                    )
                else:
                    no_rewrite = (
                        c["insufficient_rewrite"]
                        if insight["attribution"] == "insufficient-evidence"
                        else c["not_user_rewrite"]
                    )
                    lines.append(f"- {no_rewrite}")
                if insight.get("reusable_pattern"):
                    lines.append(
                        f"- **{c['reusable_pattern']}：** {insight['reusable_pattern']}"
                        if language == "zh"
                        else f"- **{c['reusable_pattern']}:** {insight['reusable_pattern']}"
                    )
                if insight.get("confirmation"):
                    lines.append(
                        f"- **{c['confirmed_context']}：** {insight['confirmation']}"
                        if language == "zh"
                        else f"- **{c['confirmed_context']}:** {insight['confirmation']}"
                    )
                else:
                    lines.append(
                        f"- **{c['needs_confirmation']}：** {insight['question']}"
                        if language == "zh"
                        else f"- **{c['needs_confirmation']}:** {insight['question']}"
                    )
                lines.extend(
                    [
                        "",
                        "<details>",
                        f"<summary>{c['evidence']}</summary>",
                        "",
                        f"- **{c['ai_interpretation']}：** {insight['ai_response']}" if language == "zh" else f"- **{c['ai_interpretation']}:** {insight['ai_response']}",
                    ]
                )
                for commit in insight["related_commits"]:
                    lines.append(f"- `{commit['date']}` {commit['subject']} (`{commit['hash']}`)")
                lines.extend(["", "</details>", ""])
        else:
            lines.extend([f"- {c['no_communication_insights']}", ""])
    lines.extend(
        [
            "",
            f"## {c['rhythm']}",
            "",
            f"> {c['rhythm_intro']}",
            "",
            f"- **{c['project_span']}：** {data['activity']['calendar_days']} 天" if language == "zh" else f"- **{c['project_span']}:** {data['activity']['calendar_days']} calendar days",
            f"- **{c['active_days']}：** {data['activity']['active_days']} 天" if language == "zh" else f"- **{c['active_days']}:** {data['activity']['active_days']} days",
            f"- **{c['longest_streak']}：** {data['activity']['longest_streak']} 天" if language == "zh" else f"- **{c['longest_streak']}:** {data['activity']['longest_streak']} days",
            "",
            f"### {c['busiest_day']} · {data['activity']['busiest_day']['date']}",
            "",
            (
                f"{data['activity']['busiest_day']['commits']} 次提交 · {data['activity']['busiest_day']['transcript_events']} 条会话 · {data['activity']['busiest_day']['lines_changed']} 行变更"
                if language == "zh"
                else f"{count_text(data['activity']['busiest_day']['commits'], 'commit', language)} · {data['activity']['busiest_day']['transcript_events']} conversation events · {data['activity']['busiest_day']['lines_changed']} lines changed"
            ),
            "",
            data['activity']['busiest_day']['summary'],
            "",
            f"## {c['attention']}",
            "",
        ]
    )
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
            f'''<article class="turn" data-date="{esc(event['date'])}" data-turn-index="{index}">
  <div class="turn-number">{index:02d}</div>
  <div class="turn-body">
    <div class="turn-meta"><span>{esc(event['turning_point_reason'])}</span><button type="button" class="turn-date" data-focus-date="{esc(event['date'])}">{esc(event['date'])}</button></div>
    <h3>{esc(event['subject'])}</h3>
    <p>{esc(category_labels[event['category']])} · {esc(file_text)} · <code>{esc(event['short_hash'])}</code></p>{dialogue_html}
  </div>
</article>'''
        )

    insight_rows = []
    for insight in data["journey_insights"]:
        evidence_items = "".join(
            f'''<li><time>{esc(item['date'])}</time><span>{esc(item['subject'])}</span><code>{esc(item['hash'])}</code></li>'''
            for item in insight["evidence_chain"]
        )
        if insight.get("confirmation"):
            lesson_html = (
                f'''<div class="insight-lesson"><b>{esc(c['captured_lesson'])}</b><p>{esc(insight['lesson'])}</p></div>'''
                if insight.get("lesson")
                else ""
            )
            review_html = f'''<div class="insight-confirmation"><b>{esc(c['confirmed_context'])}</b><p>{esc(insight['confirmation'])}</p></div>{lesson_html}'''
        else:
            review_html = f'''<div class="insight-question"><b>{esc(c['needs_confirmation'])}</b><p>{esc(insight['question'])}</p></div>'''
        insight_rows.append(
            f'''<article class="insight-card">
  <div class="insight-head"><div><span class="insight-kind {esc(insight['classification'])}">{esc(insight['classification_label'])}</span><h3>{esc(insight['topic'])}</h3></div><span class="confidence {esc(insight['confidence'])}">{esc(confidence_label(insight['confidence'], language))}</span></div>
  <div class="insight-grid"><div><h4>{esc(c['current_judgment'])}</h4><p class="insight-hypothesis">{esc(insight['hypothesis'])}</p><h4>{esc(c['evidence_basis'])}</h4><p>{esc(insight['evidence_basis'])}</p>{review_html}</div><div><h4>{esc(c['attempted_path'])}</h4><ol class="evidence-chain">{evidence_items}</ol><details class="supporting-path"><summary>{esc(c['raw_change_evidence'])}</summary><code>{esc(insight['supporting_path'])}</code></details></div></div>
</article>'''
        )
    if not insight_rows:
        insight_rows.append(f'<p class="empty">{esc(c["no_journey_insights"])}</p>')

    communication_rows = []
    for insight in data["communication_insights"]:
        missing_items = "".join(f"<li>{esc(item)}</li>" for item in insight["missing_information"])
        missing_html = (
            f'''<h4>{esc(c['missing_information'])}</h4><ul class="missing-list">{missing_items}</ul>'''
            if missing_items
            else ""
        )
        related_items = "".join(
            f"<li><time>{esc(item['date'])}</time><span>{esc(item['subject'])}</span><code>{esc(item['hash'])}</code></li>"
            for item in insight["related_commits"]
        )
        if insight.get("suggested_rewrite"):
            rewrite_html = f'''<div class="communication-rewrite"><b>{esc(c['next_time_say'])}</b><p>{esc(insight['suggested_rewrite'])}</p></div>'''
        else:
            no_rewrite = (
                c["insufficient_rewrite"]
                if insight["attribution"] == "insufficient-evidence"
                else c["not_user_rewrite"]
            )
            rewrite_html = f'''<div class="communication-not-user"><p>{esc(no_rewrite)}</p></div>'''
        pattern_html = (
            f'''<div class="communication-pattern"><b>{esc(c['reusable_pattern'])}</b><code>{esc(insight['reusable_pattern'])}</code></div>'''
            if insight.get("reusable_pattern")
            else ""
        )
        if insight.get("confirmation"):
            confirmation_html = f'''<div class="communication-confirmation"><b>{esc(c['confirmed_context'])}</b><p>{esc(insight['confirmation'])}</p></div>'''
        else:
            confirmation_html = f'''<div class="communication-question"><b>{esc(c['needs_confirmation'])}</b><p>{esc(insight['question'])}</p></div>'''
        evidence_commits = f'''<ol class="communication-commits">{related_items}</ol>''' if related_items else ""
        communication_rows.append(
            f'''<article class="communication-card">
  <div class="communication-head"><div><span class="communication-kind">{esc(insight['attribution_label'])}</span><h3>{esc(insight['topic'])}</h3></div><span class="confidence {esc(insight['confidence'])}">{esc(confidence_label(insight['confidence'], language))}</span></div>
  <div class="communication-dialogue"><div><h4>{esc(c['original_request'])}</h4><blockquote>{esc(insight['original_request'])}</blockquote></div><div><h4>{esc(c['later_correction'])}</h4><blockquote>{esc(insight['later_clarification'])}</blockquote></div></div>
  <div class="communication-grid"><div><h4>{esc(c['communication_analysis'])}</h4><p class="communication-analysis">{esc(insight['analysis'])}</p>{missing_html}{confirmation_html}</div><div>{rewrite_html}{pattern_html}<details class="communication-evidence"><summary>{esc(c['evidence'])}</summary><p><b>{esc(c['ai_interpretation'])}</b>{'：' if language == 'zh' else ': '}{esc(insight['ai_response'])}</p><p>{esc(insight['observed_impact'])}</p>{evidence_commits}</details></div></div>
</article>'''
        )
    if not communication_rows:
        communication_rows.append(f'<p class="empty">{esc(c["no_communication_insights"])}</p>')

    activity = data["activity"]
    busiest = activity["busiest_day"]
    activity_is_strip = activity["calendar_days"] <= 45
    activity_calendar_class = "activity-calendar is-strip" if activity_is_strip else "activity-calendar is-grid"
    leading_cells = "" if activity_is_strip else "".join('<span class="activity-empty" aria-hidden="true"></span>' for _ in range(activity["leading_empty_days"]))
    activity_cells = []
    for day in activity["days"]:
        detail = (
            f"{count_text(day['commits'], 'commit', language)} · {day['transcript_events']} conversation events · {day['lines_changed']} lines changed"
            if language == "en"
            else f"{day['commits']} 次提交 · {day['transcript_events']} 条会话 · {day['lines_changed']} 行变更"
        )
        label = f"{day['date']} · {detail} · {day['summary']}"
        selected = " is-selected" if day["date"] == busiest["date"] else ""
        activity_cells.append(
            f'''<button type="button" class="activity-cell level-{day['level']}{selected}" aria-pressed="{'true' if selected else 'false'}" aria-label="{esc(label)}" title="{esc(label)}" data-date="{esc(day['date'])}" data-detail="{esc(detail)}" data-summary="{esc(day['summary'])}"></button>'''
        )
    busiest_detail = (
        f"{count_text(busiest['commits'], 'commit', language)} · {busiest['transcript_events']} conversation events · {busiest['lines_changed']} lines changed"
        if language == "en"
        else f"{busiest['commits']} 次提交 · {busiest['transcript_events']} 条会话 · {busiest['lines_changed']} 行变更"
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
    has_transcripts = "transcripts" in data["coverage"]["sources"]
    section_total = 9 if has_transcripts else 8
    communication_nav = (
        f'<a href="#communication">{esc(c["communication_review"])}</a>' if has_transcripts else ""
    )
    communication_section = (
        f'''<section class="section" id="communication"><div class="shell"><div class="section-head"><span class="section-index">03 / {section_total:02d}</span><h2>{esc(c['communication_review'])}</h2><p>{esc(c['communication_review_intro'])}</p></div><div class="communication-list">{''.join(communication_rows)}</div></div></section>'''
        if has_transcripts
        else ""
    )
    rhythm_index = 4 if has_transcripts else 3
    section_navigation = f'''<nav class="section-nav" aria-label="{esc(c['chapter_navigation'])}">
  <a href="#story-map">{esc(c['story_map'])}</a>
  <a href="#insights">{esc(c['journey_insights'])}</a>
  {communication_nav}
  <a href="#rhythm">{esc(c['rhythm'])}</a>
  <a href="#career">{esc(c['career_material'])}</a>
</nav>'''

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
.masthead {{ min-height:76dvh; padding:28px 0 30px; display:grid; grid-template-rows:auto 1fr auto; border-bottom:1px solid var(--line); }}
.nav {{ display:flex; align-items:center; justify-content:space-between; gap:20px; }}
.wordmark {{ font-weight:850; letter-spacing:-.04em; font-size:20px; }}
.wordmark i {{ color:var(--accent); font-style:normal; }}
.nav-right {{ display:flex; align-items:center; justify-content:flex-end; gap:16px; }}
.nav-meta {{ color:var(--muted); font-size:13px; }}
.lang-switch {{ display:flex; align-items:center; padding:3px; border:1px solid var(--line); border-radius:9px; background:rgb(255 255 255 / .45); }}
.lang-switch a {{ min-width:42px; padding:5px 8px; border-radius:6px; color:var(--muted); font:700 11px/1.2 ui-monospace,SFMono-Regular,Menlo,monospace; text-align:center; text-decoration:none; }}
.lang-switch a:hover {{ color:var(--ink); }}
.lang-switch a.is-current {{ color:white; background:var(--ink); }}
.hero {{ align-self:center; display:grid; grid-template-columns:minmax(0,1.35fr) minmax(280px,.65fr); gap:8vw; align-items:end; padding:48px 0 26px; }}
.hero-foot {{ display:flex; align-items:center; justify-content:space-between; gap:24px; }}
.hero-scroll-note {{ color:var(--muted); font:11px ui-monospace,SFMono-Regular,Menlo,monospace; }}
.section-nav {{ display:flex; flex-wrap:wrap; gap:8px 18px; }}
.section-nav a {{ color:var(--muted); font-size:12px; text-decoration:none; }}
.section-nav a::before {{ content:'↘'; margin-right:6px; color:var(--accent); }}
.section-nav a:hover,.section-nav a:focus-visible {{ color:var(--ink); }}
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
.section {{ padding:88px 0; border-bottom:1px solid var(--line); scroll-margin-top:24px; }}
.section-head {{ max-width:760px; margin-bottom:48px; }}
.section-index {{ display:block; margin-bottom:12px; color:var(--accent); font:700 11px ui-monospace,SFMono-Regular,Menlo,monospace; letter-spacing:.12em; }}
.section-head h2 {{ margin:0 0 12px; font-size:clamp(38px,6vw,72px); line-height:.95; letter-spacing:-.055em; }}
.section-head p {{ margin:0; color:var(--muted); font-size:18px; }}
.rhythm-section {{ padding:72px 0; }}
.rhythm-layout {{ display:grid; grid-template-columns:minmax(280px,.7fr) minmax(0,1.3fr); gap:70px; align-items:start; }}
.rhythm-section .section-head {{ margin-bottom:34px; }}
.rhythm-section .section-head h2 {{ font-size:clamp(38px,5vw,62px); }}
.rhythm-stats {{ display:grid; grid-template-columns:repeat(3,1fr); gap:14px; }}
.rhythm-stat {{ padding-top:14px; border-top:1px solid var(--line); }}
.rhythm-stat strong {{ display:block; font-size:32px; letter-spacing:-.05em; }}
.rhythm-stat span {{ color:var(--muted); font-size:12px; }}
.activity-panel {{ padding:26px; background:var(--paper); border-radius:var(--radius); }}
.activity-range {{ display:flex; justify-content:space-between; gap:20px; margin-bottom:14px; color:var(--muted); font:11px ui-monospace,SFMono-Regular,Menlo,monospace; }}
.activity-scroll {{ overflow-x:auto; padding:3px; }}
.activity-calendar {{ gap:5px; }}
.activity-calendar.is-strip {{ display:grid; grid-template-columns:repeat(var(--days),minmax(13px,1fr)); min-width:max(100%,calc(var(--days) * 18px)); }}
.activity-calendar.is-grid {{ display:grid; grid-template-rows:repeat(7,13px); grid-auto-flow:column; grid-auto-columns:13px; min-width:max-content; }}
.activity-cell,.activity-empty {{ width:13px; height:13px; border-radius:3px; }}
.activity-calendar.is-strip .activity-cell {{ width:100%; height:18px; }}
.activity-cell {{ border:0; padding:0; cursor:pointer; background:#dedad1; }}
.activity-cell.level-1 {{ background:#f6cdbc; }}
.activity-cell.level-2 {{ background:#f2a17f; }}
.activity-cell.level-3 {{ background:#ee7445; }}
.activity-cell.level-4 {{ background:var(--accent); }}
.activity-cell:hover,.activity-cell:focus-visible {{ outline:2px solid var(--ink); outline-offset:2px; }}
.activity-cell.is-selected {{ outline:2px solid var(--ink); outline-offset:2px; }}
.activity-focus {{ display:grid; grid-template-columns:150px 1fr; gap:22px; margin-top:26px; padding-top:22px; border-top:1px solid var(--line); }}
.activity-focus time {{ display:block; margin-top:8px; font:700 18px ui-monospace,SFMono-Regular,Menlo,monospace; }}
.activity-focus h3 {{ margin:0 0 8px; font-size:20px; }}
.activity-focus p {{ margin:6px 0; color:var(--muted); }}
.activity-focus .activity-summary {{ color:var(--ink); font-size:16px; }}
.activity-related {{ margin-top:16px!important; color:var(--accent)!important; font-size:12px; }}
.story-map-layout {{ display:grid; grid-template-columns:220px minmax(0,960px); gap:56px; align-items:start; }}
.story-map-label {{ position:sticky; top:24px; color:var(--muted); }}
.story-map-label p {{ margin:14px 0 0; font-size:14px; line-height:1.6; }}
.story-map-line {{ width:1px; height:170px; margin:28px 0 0 4px; background:linear-gradient(to bottom,var(--accent),transparent); }}
.insight-list {{ display:grid; gap:26px; max-width:1040px; }}
.insight-card {{ padding:30px; border-radius:var(--radius); background:var(--paper); border-top:3px solid var(--accent); }}
.insight-head {{ display:flex; align-items:flex-start; justify-content:space-between; gap:24px; }}
.insight-head h3 {{ margin:10px 0 0; font-size:clamp(25px,4vw,40px); line-height:1; letter-spacing:-.045em; }}
.insight-kind {{ display:inline-block; color:var(--accent); font:700 11px ui-monospace,SFMono-Regular,Menlo,monospace; letter-spacing:.1em; text-transform:uppercase; }}
.insight-kind.blocked-loop {{ color:var(--ink); }}
.insight-kind.necessary-exploration {{ color:var(--muted); }}
.insight-grid {{ display:grid; grid-template-columns:minmax(0,1fr) minmax(320px,.9fr); gap:56px; margin-top:30px; }}
.insight-grid h4 {{ margin:22px 0 8px; color:var(--muted); font:700 11px ui-monospace,SFMono-Regular,Menlo,monospace; letter-spacing:.08em; text-transform:uppercase; }}
.insight-grid h4:first-child {{ margin-top:0; }}
.insight-grid p {{ margin:0; color:#3f3f3f; line-height:1.65; }}
.insight-hypothesis {{ color:var(--ink)!important; font-size:18px; }}
.evidence-chain {{ margin:0; padding:0; list-style:none; border-top:1px solid var(--line); }}
.evidence-chain li {{ display:grid; grid-template-columns:90px minmax(0,1fr) auto; gap:14px; padding:13px 0; border-bottom:1px solid var(--line); align-items:start; }}
.evidence-chain time,.evidence-chain code {{ color:var(--muted); font:11px ui-monospace,SFMono-Regular,Menlo,monospace; }}
.evidence-chain span {{ font-size:13px; }}
.insight-question,.insight-confirmation,.insight-lesson {{ margin-top:24px; padding:18px; border-left:3px solid var(--accent); background:var(--surface); }}
.insight-question b,.insight-confirmation b,.insight-lesson b {{ display:block; margin-bottom:7px; color:var(--accent); font-size:12px; }}
.supporting-path {{ margin-top:14px; color:var(--muted); font-size:12px; }}
.supporting-path summary {{ cursor:pointer; }}
.supporting-path code {{ display:block; margin-top:8px; color:var(--ink); }}
.raw-evidence {{ max-width:1040px; }}
.communication-list {{ display:grid; gap:26px; max-width:1040px; }}
.communication-card {{ padding:30px; border-radius:var(--radius); background:var(--paper); border-top:3px solid var(--ink); }}
.communication-head {{ display:flex; align-items:flex-start; justify-content:space-between; gap:24px; }}
.communication-head>div,.communication-dialogue>div,.communication-grid>div {{ min-width:0; }}
.communication-head h3 {{ margin:10px 0 0; font-size:clamp(25px,4vw,40px); line-height:1; letter-spacing:-.045em; }}
.communication-kind {{ color:var(--accent); font:700 11px ui-monospace,SFMono-Regular,Menlo,monospace; letter-spacing:.09em; text-transform:uppercase; overflow-wrap:anywhere; }}
.communication-dialogue {{ display:grid; grid-template-columns:1fr 1fr; gap:18px; margin-top:30px; }}
.communication-dialogue>div {{ padding:20px; border:1px solid var(--line); border-radius:12px; }}
.communication-card h4 {{ margin:0 0 9px; color:var(--muted); font:700 11px ui-monospace,SFMono-Regular,Menlo,monospace; letter-spacing:.08em; text-transform:uppercase; }}
.communication-dialogue blockquote {{ margin:0; font-size:16px; line-height:1.6; overflow-wrap:anywhere; }}
.communication-grid {{ display:grid; grid-template-columns:minmax(0,1fr) minmax(320px,.9fr); gap:56px; margin-top:30px; }}
.communication-grid h4:not(:first-child) {{ margin-top:24px; }}
.communication-analysis {{ margin:0; font-size:18px; line-height:1.65; }}
.missing-list {{ margin:0; padding-left:18px; color:var(--muted); }}
.missing-list li {{ margin:7px 0; }}
.communication-rewrite,.communication-question,.communication-confirmation,.communication-not-user {{ padding:20px; background:var(--surface); border-left:3px solid var(--accent); }}
.communication-rewrite b,.communication-question b,.communication-confirmation b {{ display:block; margin-bottom:8px; color:var(--accent); font-size:12px; }}
.communication-rewrite p,.communication-question p,.communication-confirmation p,.communication-not-user p {{ margin:0; line-height:1.65; }}
.communication-rewrite p {{ color:var(--ink); font-size:17px; }}
.communication-pattern {{ margin-top:18px; }}
.communication-pattern b {{ display:block; margin-bottom:8px; color:var(--muted); font-size:12px; }}
.communication-pattern code {{ display:block; padding:14px; border-radius:9px; background:var(--ink); color:white; line-height:1.55; overflow-wrap:anywhere; }}
.communication-evidence {{ margin-top:18px; color:var(--muted); font-size:12px; }}
.communication-evidence summary {{ cursor:pointer; }}
.communication-evidence p {{ line-height:1.6; }}
.communication-commits {{ margin:12px 0 0; padding:0; list-style:none; border-top:1px solid var(--line); }}
.communication-commits li {{ display:grid; grid-template-columns:90px 1fr auto; gap:12px; padding:10px 0; border-bottom:1px solid var(--line); }}
.turns {{ max-width:960px; border-top:1px solid var(--line); }}
.turn {{ position:relative; display:grid; grid-template-columns:84px 1fr; gap:24px; padding:30px 0 30px 14px; border-bottom:1px solid var(--line); transition:background .24s ease, padding-left .24s ease; }}
.turn::before {{ content:''; position:absolute; left:0; top:0; bottom:0; width:3px; background:transparent; }}
.turn.is-match {{ padding-left:22px; background:linear-gradient(90deg,var(--paper),transparent 72%); }}
.turn.is-match::before {{ background:var(--accent); }}
.turn-number {{ color:var(--accent); font:700 13px ui-monospace,SFMono-Regular,Menlo,monospace; }}
.turn-meta {{ display:flex; align-items:center; justify-content:space-between; gap:20px; color:var(--accent); font-size:12px; text-transform:uppercase; letter-spacing:.08em; }}
.turn-date {{ border:0; padding:0; color:var(--muted); background:transparent; font:12px ui-monospace,SFMono-Regular,Menlo,monospace; cursor:pointer; }}
.turn-date:hover,.turn-date:focus-visible {{ color:var(--ink); text-decoration:underline; text-underline-offset:3px; }}
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
.confidence.confirmed {{ color:white; border-color:var(--accent); background:var(--accent); }}
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
  .masthead {{ min-height:auto; padding-bottom:26px; }} .hero,.rhythm-layout,.friction-layout,.attention-grid,.method,.context-callout,.story-map-layout,.insight-grid,.communication-dialogue,.communication-grid {{ grid-template-columns:1fr; gap:34px; }} .hero {{ padding:64px 0 34px; }} .hero-foot {{ align-items:flex-start; flex-direction:column; gap:12px; }} .section-nav {{ gap:8px 14px; }} h1 {{ font-size:clamp(52px,17vw,86px); }} .coverage {{ max-width:440px; }} .section {{ padding:68px 0; }} .story-map-label {{ position:static; }} .story-map-line {{ height:56px; margin-top:18px; }}
  .turn {{ grid-template-columns:44px 1fr; gap:14px; }} .turn-meta {{ align-items:flex-start; flex-direction:column; gap:5px; }} .event {{ grid-template-columns:84px 14px 1fr; gap:12px; }} .friction-row {{ grid-template-columns:34px 1fr; }} .ratio {{ grid-column:2; text-align:left; display:flex; align-items:baseline; gap:8px; }}
  .dimensions,.proof-list,.career-grid {{ grid-template-columns:1fr; }} .attention-row {{ grid-template-columns:100px 1fr; }} .attention-row span {{ grid-column:2; text-align:left; }}
}}
@media (max-width:420px) {{
  .shell {{ width:min(100% - 22px,1180px); }} .nav-meta {{ display:none; }} .story-statement {{ font-size:25px; }} .story-highlights {{ display:grid; }} .full-history {{ padding:16px; }} .masthead {{ padding-bottom:10px; }} .rhythm-section {{ padding-top:26px; }}
  .rhythm-stats {{ gap:8px; }} .rhythm-stat strong {{ font-size:26px; }} .activity-panel {{ padding:18px; }} .activity-focus {{ grid-template-columns:1fr; gap:10px; }}
  .event {{ grid-template-columns:1fr; min-height:auto; padding:16px 0; border-bottom:1px solid var(--line); }} .event-mark {{ display:none; }} .event-body {{ padding:0; }} .turn {{ padding-left:10px; }} .turn.is-match {{ padding-left:16px; }} .insight-card,.communication-card {{ padding:22px 18px; }} .insight-head {{ gap:12px; }} .communication-head {{ flex-direction:column; gap:12px; }} .evidence-chain li,.communication-commits li {{ grid-template-columns:82px 1fr; }} .evidence-chain code,.communication-commits code {{ grid-column:2; }}
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
  <div class="shell hero-foot">{section_navigation}<span class="hero-scroll-note">{'Scroll to trace the build' if language == 'en' else '向下查看项目如何转向'}</span></div>
</header>
<main>
  <section class="section story-map-section" id="story-map"><div class="shell"><div class="section-head"><span class="section-index">01 / {section_total:02d}</span><h2>{esc(c['turning_points'])}</h2><p>{esc(c['story_map_intro'])}</p></div><div class="story-map-layout"><aside class="story-map-label"><span class="eyebrow">{esc(c['story_map'])}</span><p>{esc(c['turning_points_intro'])}</p><div class="story-map-line" aria-hidden="true"></div></aside><div class="turns">{''.join(turning_rows)}</div></div><details class="full-history"><summary>{esc(c['full_timeline'])} · {esc(count_text(len(data['timeline']), 'commit', language))}</summary><p>{esc(c['full_timeline_intro'])}</p><div class="filters">{''.join(filters)}</div><div class="timeline">{''.join(timeline_rows)}</div></details></div></section>
  <section class="section" id="insights"><div class="shell"><div class="section-head"><span class="section-index">02 / {section_total:02d}</span><h2>{esc(c['journey_insights'])}</h2><p>{esc(c['journey_insights_intro'])}</p></div><div class="insight-list">{''.join(insight_rows)}</div><details class="full-history raw-evidence"><summary>{esc(c['raw_change_evidence'])}</summary><p>{esc(c['friction_intro'])}</p><div class="friction-layout"><div>{''.join(friction_rows)}</div><aside class="loops"><h3>{esc(c['loop_candidates'])}</h3>{''.join(loop_rows)}</aside></div></details></div></section>
  {communication_section}
  <section class="section rhythm-section" id="rhythm"><div class="shell rhythm-layout">
    <div><div class="section-head"><span class="section-index">{rhythm_index:02d} / {section_total:02d}</span><h2>{esc(c['rhythm'])}</h2><p>{esc(c['rhythm_intro'])}</p></div><div class="rhythm-stats">
      <div class="rhythm-stat"><strong>{activity['calendar_days']}</strong><span>{esc(c['project_span'])}</span></div>
      <div class="rhythm-stat"><strong>{activity['active_days']}</strong><span>{esc(c['active_days'])}</span></div>
      <div class="rhythm-stat"><strong>{activity['longest_streak']}</strong><span>{esc(c['longest_streak'])}</span></div>
    </div></div>
    <div class="activity-panel"><div class="activity-range"><span>{esc(activity['start'])}</span><span>{esc(activity['end'])}</span></div><div class="activity-scroll"><div class="{activity_calendar_class}" style="--days:{activity['calendar_days']}">{leading_cells}{''.join(activity_cells)}</div></div>
      <article class="activity-focus" aria-live="polite"><div><span class="eyebrow">{esc(c['busiest_day'])}</span><time id="activity-date">{esc(busiest['date'])}</time></div><div><h3>{esc(c['day_story'])}</h3><p id="activity-detail">{esc(busiest_detail)}</p><p class="activity-summary" id="activity-summary">{esc(busiest['summary'])}</p><p class="activity-related" id="activity-related"></p></div></article>
    </div>
  </div></section>
  <section class="section"><div class="shell"><div class="section-head"><h2>{esc(c['attention'])}</h2><p>{esc(c['attention_intro'])}</p></div><div class="attention-grid"><div>{''.join(attention_rows)}</div><aside class="time-callout"><span class="confidence {esc(m['time_estimate']['confidence'])}">{esc(label_value(c['confidence'], confidence_label(m['time_estimate']['confidence'], language), language))}</span><strong>{m['time_estimate']['hours']}{'h' if language == 'en' else ' 小时'}</strong><p>{'Estimated from: ' if language == 'en' else '估算来源：'}{esc(source_label)}{'. ' if language == 'en' else '。'}{esc(c['git_limit'] if m['time_estimate']['source']=='git' else c['session_limit'])}</p></aside></div></div></section>
  <section class="section"><div class="shell"><div class="section-head"><h2>{esc(c['profile'])}</h2><p>{esc(c['profile_intro'])}</p></div><div class="dimensions">{''.join(dimension_rows)}</div></div></section>
  <section class="section"><div class="shell"><div class="section-head"><h2>{esc(c['proof'])}</h2><p>{esc(c['proof_intro'])}</p></div><div class="proof-list">{''.join(card_rows)}</div></div></section>
  <section class="section" id="career"><div class="shell"><div class="section-head"><h2>{esc(c['career_material'])}</h2><p>{esc(career_intro)}</p></div>{career_html}</div></section>
  <section class="section"><div class="shell method"><div><div class="section-head"><h2>{esc(c['method'])}</h2></div><p><strong>{esc(label_value(c['coverage'], sources, language))}</strong></p><ul>{limitations}</ul></div><div><h3>{esc(c['career_output_rule'])}</h3><p>{esc(c['career_confirmed_rule'] if career['confirmed'] else c['resume_prompt'])}</p><h3>{esc(c['local_first'])}</h3><p>{esc(c['local_first_detail'])}</p></div></div></section>
</main>
<footer><div class="shell"><strong>BuildStory</strong><span>{esc(c['footer'])}</span></div></footer>
<script type="application/json" id="buildstory-data">{source_data}</script>
<script>
(function() {{
  var cells = Array.prototype.slice.call(document.querySelectorAll('.activity-cell'));
  var turns = Array.prototype.slice.call(document.querySelectorAll('.turn[data-date]'));
  var related = document.getElementById('activity-related');
  var relatedLabel = {json.dumps(c['related_turns'], ensure_ascii=False)};
  var noRelatedLabel = {json.dumps(c['no_related_turns'], ensure_ascii=False)};

  function selectDay(cell, scrollToRhythm) {{
    cells.forEach(function(item) {{
      var active = item === cell;
      item.classList.toggle('is-selected', active);
      item.setAttribute('aria-pressed', active ? 'true' : 'false');
    }});
    document.getElementById('activity-date').textContent = cell.dataset.date;
    document.getElementById('activity-detail').textContent = cell.dataset.detail;
    document.getElementById('activity-summary').textContent = cell.dataset.summary;
    var matches = turns.filter(function(turn) {{ return turn.dataset.date === cell.dataset.date; }});
    turns.forEach(function(turn) {{ turn.classList.toggle('is-match', matches.indexOf(turn) !== -1); }});
    related.textContent = matches.length ? relatedLabel + ' · ' + matches.length : noRelatedLabel;
    if (scrollToRhythm) {{ document.getElementById('rhythm').scrollIntoView({{ behavior: 'smooth', block: 'center' }}); }}
  }}

  cells.forEach(function(cell) {{ cell.addEventListener('click', function() {{ selectDay(cell, false); }}); }});
  document.querySelectorAll('.turn-date').forEach(function(button) {{
    button.addEventListener('click', function() {{
      var cell = cells.find(function(item) {{ return item.dataset.date === button.dataset.focusDate; }});
      if (cell) selectDay(cell, true);
    }});
  }});
  document.querySelectorAll('.filter').forEach(function(button) {{ button.addEventListener('click', function() {{
    document.querySelectorAll('.filter').forEach(function(item) {{ item.classList.remove('is-active'); }});
    button.classList.add('is-active');
    var selected = button.dataset.filter;
    document.querySelectorAll('.event').forEach(function(event) {{ event.hidden = selected !== 'all' && event.dataset.category !== selected; }});
  }}); }});
  var initial = cells.find(function(cell) {{ return cell.classList.contains('is-selected'); }}) || cells[0];
  if (initial) selectDay(initial, false);
}})();
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
    parser.add_argument("--context", help="Optional JSON file with user-confirmed journey insights, role, outcome, decision, summary, and resume bullets.")
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
