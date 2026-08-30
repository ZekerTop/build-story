# BuildStory

**不只看你做出了什么，更看你是怎么做到的。**

BuildStory 是一个本地优先的 Agent Skill 和项目复盘报告生成器。它可以从 Git 历史和用户明确授权的 AI 编程会话中，提炼项目故事与关键转折点，发现可能的重复返工、回滚和注意力黑洞，生成基于证据的过程画像，并将真实证据转化为复盘、作品集、简历和面试材料。

[English](README.en.md)

![BuildStory 报告预览](examples/demo-report/preview.png)

> 把 Git 历史和已授权的 AI 会话，变成一条可核验的项目决策时间线。

## 60 秒体验

```bash
git clone https://github.com/ZekerTop/build-story.git
cd build-story
python3 scripts/build_story.py /你的/项目路径 --output ./build-story-report
open ./build-story-report/report.html
```

不需要 API Key，不需要注册账号，不会上传源代码。第一次运行先看中文 HTML 报告，再决定是否加入已授权的会话记录。

## 为什么需要 BuildStory

最终仓库只展示了保留下来的结果，通常不会告诉你：

- 哪个功能被重新做了三次；
- 哪个模块消耗了最多注意力；
- 哪个决定让整个系统突然变简单；
- 哪些实验最终被放弃；
- 一条简历描述背后到底有什么真实证据。

BuildStory 让这些看不见的过程重新变得可检查，同时不会假装 Git 能读懂开发者的全部想法。

## 它会生成什么

每次运行都会生成默认报告以及中英文版本。`--language` 用于选择打开 `report.html` 时默认显示的语言：

```text
build-story-report/
├── evidence.json       # 默认语言的结构化证据
├── evidence.en.json    # 英文证据
├── evidence.zh.json    # 中文证据
├── report.md           # 默认语言的 Markdown 报告
├── report.en.md        # 英文 Markdown 报告
├── report.zh.md        # 中文 Markdown 报告
├── report.html         # 带 EN / 中文切换的默认报告
├── report.en.html      # 英文可视化报告
└── report.zh.html      # 中文可视化报告
```

报告包含：

1. 第一屏先讲清楚项目发生了什么变化；
2. 默认只展示 5～7 个真正改变方向、风险或交付状态的转折点；
3. 把高频变更组织成“失败循环、必要探索、方向转变”三类待确认的经历解释；
4. 为每个解释展示尝试路径、判断依据和一个需要用户确认的问题；
5. 项目跨度、活跃开发日、最长连续推进和变更最密集日；
6. 项目范围内的活动脉搏，可以查看某一天实际发生了什么；
7. 注意力区域和活跃时间估算；
8. 交付、验证、可追溯性、迭代控制和经验沉淀的证据等级与行动建议；
9. 可用于作品集、简历、成就记录和 STAR 面试故事的证据卡片。

活动脉搏描述可观察到的 Git 和会话证据，不把提交次数解释为勤奋程度或生产力。

完整提交记录和数字计算方法仍然保留，但默认折叠为支撑证据。BuildStory **不会**给项目计算一个虚假的总分。

## 快速开始

环境要求：

- Python 3.10+
- Git
- 至少包含一次提交的 Git 仓库

同时生成中英文版本，并默认打开中文：

```bash
python3 scripts/build_story.py /你的/项目路径 \
  --output /你的/项目路径/build-story-report \
  --language zh
```

未指定 `--language` 时，默认使用中文。

同时生成中英文版本，并默认打开英文：

```bash
python3 scripts/build_story.py /path/to/project \
  --output /path/to/project/build-story-report \
  --language en
```

生成完成后，用浏览器打开 `build-story-report/report.html`，可以在顶部使用 **EN / 中文** 切换语言，也可以直接打开或分享对应的语言文件。

### 加入已授权的 AI 编程会话

当用户明确提供路径时，BuildStory 可以读取本地 `.jsonl`、`.json`、`.txt` 和 `.md` 会话文件：

```bash
python3 scripts/build_story.py /你的/项目路径 \
  --session /已授权/会话/session.jsonl \
  --output /你的/项目路径/build-story-report \
  --language zh
```

可以重复使用 `--session` 添加多个已授权文件或目录。

BuildStory 不会自动搜索私有会话目录。

当前解析器支持通用的 `.jsonl`、`.json`、`.txt` 和 `.md` 输入。不同 Agent 的字段命名可能不同；无法识别时间或角色时，会保留 Git 报告并降低相关结论的置信度，不会把缺失内容编造成事实。

### 先确认经历，再补充三项真实语境

Git 可以证明发生了什么，却不能证明你的真实职责、最终结果和决策动机。需要生成简历、作品集或 STAR 面试故事时，只补充三项信息：

1. 你在项目中的真实职责是什么？
2. 最终给用户或自己带来了什么结果？
3. 哪个决定最能代表你的能力？

创建 `context.json`：

```json
{
  "zh": {
    "role": "产品方向判断、核心实现与发布验证",
    "outcome": "发布 1.0，并让用户可以自主控制数据导出",
    "key_decision": "撤销持续复杂化的自动同步，改为显式导出",
    "summary": "从复杂的自动同步，回到用户可控的本地优先。",
    "resume_bullets": [
      "在自动同步持续引入队列与重试复杂度后，主动回滚并改为显式导出。"
    ],
    "insight_confirmations": {
      "path:src/sync.py": {
        "classification": "direction-change",
        "reason": "自动同步违背了面向小白的简单性。",
        "lesson": "功能持续引入恢复机制时，应先重新判断它是否值得存在。"
      }
    }
  }
}
```

重新生成报告：

```bash
python3 scripts/build_story.py /你的/项目路径 \
  --context /你的/项目路径/context.json \
  --output /你的/项目路径/build-story-report \
  --language zh
```

报告会据此生成作品集摘要、简历要点和 STAR 面试故事，不再用提交次数冒充成就。

如果 Git 提交或 AI 对话使用了英文，可以在 `zh.translations` 中提供“原文 → 中文”的精确映射。中文报告会显示翻译后的项目历程，同时在结构化证据中保留原文。有已授权会话时，关键转折点还会展示对应的“用户要求 / AI 响应”摘录。

## 作为 Agent Skill 安装

### Codex

```bash
git clone https://github.com/ZekerTop/build-story.git \
  "${CODEX_HOME:-$HOME/.codex}/skills/build-story"
```

调用示例：

```text
$build-story 复盘当前项目，重点找出我反复返工和改变方向的部分。
```

### 其他兼容 Agent Skills 的客户端

将完整的 `build-story` 文件夹克隆或复制到客户端的用户级或项目级 Skills 目录。请保留 `SKILL.md`、`scripts/`、`references/` 和 `agents/`。

更多示例：

```text
使用 $build-story 为当前仓库生成一次完整项目复盘。
```

```text
使用 $build-story 找出重复循环、可能的时间黑洞，以及这个项目最有证据支撑的成就。
```

```text
使用 $build-story 把当前项目整理成作品集案例和三条真实简历描述。仓库里无法验证的结果再问我，不要编造数字。
```

## 证据模型

BuildStory 会明确区分三种内容：

| 类型 | 含义 | 示例 |
|---|---|---|
| 观察事实 | 数据中直接存在 | 明确的 `Revert` 提交 |
| 分析推断 | 可重复观察但仍需解释 | 一个文件出现大量双向变更 |
| 用户确认 | 由用户补充的真实语境 | 为什么最终放弃某个方案 |

每个主题级经历解释和时间估算都会显示置信度。未经用户确认时，它只是有证据的假设，不会直接写成个人成就。

### 循环检测

分析器会检查：

- 包含 `revert`、`rollback`、回滚或撤销的提交；
- 重复出现的规范化提交主题；
- 多次发生新增和删除的高频变更文件；
- 已授权会话中高度相似的重复提示。

高频变更也可能意味着有价值的探索。因此 BuildStory 会结合回滚、替代方案、重复修复和验证信号，先给出“失败循环、必要探索、方向转变”三类待确认解释。文件路径、修改次数和双向变更比例只作为折叠证据保留，不直接等同于错误或浪费。

### 时间估算

Git 不记录思考时间。仅使用 Git 时，BuildStory 会将时间接近的提交划分为工作会话，这个估算会被标记为低置信度。

带时间戳的已授权会话可以改善覆盖范围，但仍然无法记录离线思考、会议、调研和未保存实验。

## 基于证据的过程画像

BuildStory 分别展示：

- **交付证据：** 发布、打包、文档和完成信号；
- **验证纪律：** 测试、CI、代码检查和验证相关变更；
- **变更可追溯性：** 提交描述质量和可审查的提交规模；
- **迭代控制：** 明确回滚和集中返工信号；
- **经验沉淀：** README、Changelog、ADR、文档和复盘记录。

报告首先展示“充分、较强、清晰、需要复盘、证据不足”等人能理解的等级，并为每个维度给出原因和下一次行动建议。原始数字只放在“查看计算方法”中。

这些等级描述仓库中可观察到的证据，不衡量一个人的智力、职级或价值。

## 示例效果

仓库内包含一个名为 PocketTasks 的虚构项目及其确定性示例报告：

- [英文 HTML 报告](examples/demo-report/en/report.html)
- [英文 Markdown 报告](examples/demo-report/en/report.md)
- [中文 HTML 报告](examples/demo-report/zh/report.html)
- [中文 Markdown 报告](examples/demo-report/zh/report.md)

重新生成：

```bash
python3 scripts/create_demo_report.py
```

## 隐私与安全

- 所有分析都在本地进行；
- 生成器不会发送网络请求；
- 不修改项目源文件；
- 只向用户指定的输出目录写入结果；
- 报告中不会包含本机绝对路径；
- 不会将完整会话复制进报告；
- 简历和作品集不得编造影响指标。

安全问题请参阅 [SECURITY.md](SECURITY.md)。

## 已知限制

- 仅使用 Git 时，无法看到未提交实验和不可见思考；
- 提交信息分类使用启发式规则；
- 高频变更并不自动等于浪费；
- 不同 AI 工具的会话格式差异很大，v0.1 使用保守的通用解析方式；
- 职业成果仍需要用户确认自己的职责和最终影响。

## 开发与验证

运行测试：

```bash
python3 -m unittest discover -s tests -v
```

验证 Skill 结构：

```bash
python3 /path/to/skill-creator/scripts/quick_validate.py .
```

示例报告和测试会覆盖 Git-only、已授权会话、中文动态文本、日期活动脉搏、坏 JSON 输入和移动端布局。

## 项目结构

```text
build-story/
├── SKILL.md
├── agents/openai.yaml
├── scripts/
│   ├── build_story.py
│   └── create_demo_report.py
├── references/
│   ├── methodology.md
│   └── narrative-guide.md
├── examples/demo-report/
├── tests/
└── docs/superpowers/specs/
```

## 路线图

- 更完整的 Codex、Claude Code、Cursor 和 OpenCode 会话适配器；
- 对比计划过程与实际开发过程；
- 不用于员工排名的项目间对比；
- 作品集和晋升材料导出模板。

## 参与贡献

欢迎提交 Issue 和范围清晰的 Pull Request。请阅读 [CONTRIBUTING.md](CONTRIBUTING.md)。

## 许可证

[MIT](LICENSE)
