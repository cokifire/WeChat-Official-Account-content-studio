# 编辑工作流与可追溯产物

本规则用于公众号写作、审稿和发布前内容判断。先建立任务书与证据，再写初稿；只有审稿通过后
才生成 `article.md`。机械分数只提示风险，不能替代事实核对与编辑判断。

## 目录

1. [文章任务书](#文章任务书)
2. [主张与来源](#主张与来源)
3. [个人材料边界](#个人材料边界)
4. [编辑判断](#编辑判断)
5. [报告与元数据](#报告与元数据)

## 文章任务书

在写正文前填写 `{article_dir}/brief.yaml`：

```yaml
version: 1
title: "工作标题"
audience:
  who: "具体读者"
  context: "读者在什么情境下阅读"
  question: "读者真正要解决的问题"
goal:
  takeaway: "读完能复述的一个结论"
  action: "读完可采取的行动；纯观点文可写判断方法"
thesis:
  statement: "全文核心判断"
  novelty: "相较常见说法新增了什么"
  boundary: "结论在什么条件下成立"
  counterpoint: "最强反方或替代解释"
personal_materials:
  available: false
  items: []
framework: "观点"
sections:
  - purpose: "本节推进什么"
    claim_ids: [C1]
constraints:
  desired_length: "1200-2500 字"
  must_include: []
  must_avoid: []
```

`novelty` 不等于强行反主流。找不到可靠新角度时，缩小问题、补充适用条件，或给出更好用的
判断框架。每一节都要服务一个读者问题和至少一个主张；无法对应的段落默认删除。

## 主张与来源

把准备写进文章的主张记录到 `{article_dir}/claims.yaml`：

```yaml
version: 1
claims:
  - id: C1
    text: "正文准备表达的主张"
    type: fact
    source_ids: [S1]
    status: supported
    boundary: "适用范围或不确定性"
```

允许的 `type`：

- `fact`：可被外部证据核验的具体事实。
- `inference`：由事实推导出的解释，正文必须明确是推断。
- `opinion`：作者判断，不伪装成共识。
- `user_experience`：用户在当前任务明确提供的经历或观察。

允许的 `status`：

- `supported`：有直接证据支持。
- `bounded`：有依据，但必须保留适用范围或不确定性。
- `unsupported`：暂不进入初稿。

把来源记录到 `{article_dir}/sources.yaml`：

```yaml
version: 1
sources:
  - id: S1
    url: "https://example.com/original-page"
    title: "原页面标题"
    publisher: "发布方"
    published_at: "YYYY-MM-DD"
    accessed_at: "YYYY-MM-DD"
    claim_ids: [C1]
    status: verified
    note: "该页面具体支持什么，不要只写泛泛摘要"
```

来源状态只使用：

- `verified`：已打开原页面，内容直接支持对应主张。
- `user_provided`：来自用户本轮提供的材料。
- `lead_only`：搜索摘要、社交帖线索或尚未打开核对的页面；不能支持 `fact`。
- `rejected`：来源不可靠、过期或不支持主张。

优先原始报告、官方文档、当事方资料和高可信媒体。来源聚合页、搜索摘要、模型记忆和范文不
得标为 `verified`。引用必须能在原页面逐字核对；做不到时改为转述，并明确归属。

## 个人材料边界

只有用户在当前任务明确提供的经历、观察或原话，才可写成作者亲历并记录为
`user_experience`。`personal_materials.available=false` 时：

- 可以写“我的判断是”这类作者观点。
- 不得写作者经历过的事件、朋友同事、采访、现场对话、时间地点、动作和感官细节。
- 人格或框架要求故事开场时，改用观察、问题、公开案例或核心判断开场。
- 第三方范文只允许校准结构与节奏，不提供可复用的观点、人物、经历、细节或句子。

## 编辑判断

从五项各评 1–5 分：

1. **准确**：核心事实有直接来源；事实、推断、意见分得开；结论没有超出证据边界。
2. **观点**：核心判断明确，写出新增价值、适用范围和最强反方，不重复常识充数。
3. **有用**：真正回答目标读者的问题，给出行动、决策条件或可迁移的理解框架。
4. **合声**：符合账号语气但不被人格模板绑架；个人经历只来自本轮用户材料。
5. **好读**：开头尽快进入问题，各节各有任务，论证连贯，标题准确，语言直接且无重复。

以下任一项出现都不能通过：

- 编造作者亲历、身份、朋友、采访、对话、场景或细节。
- 核心具体事实没有来源，或来源不支持正文说法。
- 核心结论与证据脱节，或把推断写成确定事实。
- 没有给目标读者明确的结论、行动或判断方法。

编辑决定只使用：

- `pass`：没有阻断项，五项平均分至少 4，单项不低于 3。
- `revise`：可在现有材料内修正；必须实际改稿并复审，不能只列建议。
- `needs_input`：仅在用户明确要求写其个人故事，但关键材料缺失且无法安全换框架时使用。

最多两轮。第二轮仍不通过时，删除不可靠内容、缩小承诺，交付能被证据支持的版本；不得把未
通过的文章标成 `publishable=true`。不为机械分数强行加入错句、情绪配额、随机离题或虚假细节。

## 报告与元数据

把审稿结果写入 `{article_dir}/generated/review-report.json`：

```json
{
  "schema_version": 1,
  "decision": "pass",
  "publishable": true,
  "pass_number": 1,
  "dimensions": {
    "accuracy": 4,
    "viewpoint": 4,
    "usefulness": 4,
    "voice": 4,
    "readability": 4
  },
  "blockers": [],
  "major_issues": [],
  "changes_made": [],
  "verified_source_count": 3,
  "unsupported_claim_count": 0
}
```

随后同步更新 `draft-metadata.json`：

```json
{
  "editorial": {
    "decision": "pass",
    "publishable": true,
    "pass_number": 1,
    "review_report": "generated/review-report.json"
  }
}
```

两个文件必须一致。`article.md` 只保存通过后的成稿；`draft.md` 保留原始初稿，便于学习人工
修改和观察编辑幅度。发布门禁必须同时读取元数据与审稿报告，任一缺失或不一致都阻断发布。
