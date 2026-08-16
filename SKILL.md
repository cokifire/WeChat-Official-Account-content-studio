---
name: wewrite
description: |
  微信公众号内容工作室：完成选题、素材核验、文章任务书、写作、编辑审稿、本地预览，
  并在用户明确要求时追加封面/配图、微信排版或草稿箱发布。也处理公众号文章润色、
  Markdown 转微信格式、主题切换、学习人工改稿、文章数据复盘和发布前检查。
  仅在公众号、微信文章、微信推文、草稿箱或微信排版语境中使用；通用文章、博客、
  邮件、PPT、短视频文案和网站 SEO 不触发。
---

# WeWrite — 微信公众号内容工作室

把判断交给 Agent，把可重复检查交给脚本。默认交付一篇有来源、经过编辑判断且可本地预览的
成稿；图片生成和草稿箱发布始终是独立动作。

`{skill_dir}` 指本 `SKILL.md` 所在目录，`{article_dir}` 指单篇文章目录。

## 运行边界

- 用户说“写一篇”时，完成选题、证据、初稿、审稿、成稿和本地预览；不调用付费生图服务，
  不上传图片，不创建微信草稿。
- 用户说“完整制作”时，在成稿后追加封面、必要配图和本地预览；仍不创建微信草稿。
- 只有用户在本轮明确说“推到草稿箱 / 发布”时，才执行发布。以前说过、配置里有密钥、
  或文章目录里已有 `media_id` 都不算本轮授权。
- 配图、排版和发布不得反向改写已审稿的 `article.md`。需要插图时生成
  `article-illustrated.md`，并用 `draft-metadata.json.render_source` 显式选择带图副本。
- 搜索失败时可以保留有边界的分析和意见；不得把模型记忆、搜索摘要或范文包装成已核实事实。
- 用户说“交互模式 / 我要自己选”时，只在选题、框架和视觉方向处暂停；其他步骤连续完成。

## 意图路由

| 用户意图 | 动作 |
|---|---|
| 写一篇 / 继续上篇 | 执行内容主链；已有唯一未完成目录时恢复，不重复新建 |
| 只要选题 | 读取 `references/topic-selection.md`，只交付选题 |
| 检查 / 优化文章 | 读取 `references/editorial-workflow.md`，审稿并按要求改稿 |
| 封面 / 配图 / 图片提示词 | 读取 `references/visual-prompts.md` |
| 排版 / 预览 / 主题 | 读取 `references/layout-playbook.md` 和 `references/template-workflow.md` |
| 推草稿箱 / 发布 | 读取 `references/template-workflow.md` 和 `references/wechat-constraints.md` |
| 重新设置风格 | 读取 `references/onboard.md` |
| 学习我的修改 | 读取 `references/learn-edits.md` |
| 看文章数据 | 读取 `references/effect-review.md` |
| X / Twitter 链接选题 | 读取 `references/x-link-workflow.md` |

## 文章产物契约

每篇文章使用 `{skill_dir}/output/<工作标题>/`，通过下面的命令创建：

```powershell
powershell -ExecutionPolicy Bypass -File {skill_dir}/scripts/new_wechat_article.ps1 -Title "<工作标题>" -Author "<作者>"
```

目录内各文件职责固定：

| 文件 | 职责 |
|---|---|
| `brief.yaml` | 目标读者、问题、核心判断、新增价值、反方、边界、个人材料可用性 |
| `claims.yaml` | 事实、推断、意见、用户经历及其证据状态 |
| `sources.yaml` | 原始页面、发布方、日期、支持的主张和核验状态 |
| `draft.md` | 未经编辑通过的初稿 |
| `article.md` | 通过编辑门槛后的唯一成稿源文件 |
| `generated/review-report.json` | 五项编辑判断、阻断项、修改轮次和 `publishable` |
| `draft-metadata.json` | 标题、摘要、主题、视觉、编辑与发布状态 |
| `assets/` | 封面和正文图片 |
| `generated/` | 提示词、布局计划、质量报告和发布结果 |

完整字段和写入规则见 `references/editorial-workflow.md`。不得把 `draft.md` 当成已审稿成稿，
不得为了排版省事把生成 HTML 当作正文源文件。

## 内容主链

### 1. 诊断与风格

优先使用项目虚拟环境；没有时再使用可导入依赖的 `python3`：

```bash
python3 {skill_dir}/scripts/diagnose.py --json
```

缺 `style.yaml` 时读取 `references/onboard.md`。缺微信配置只影响发布，缺图片配置只影响远程
生图；它们不能阻止写作和本地预览。诊断中的可选增强项只作信息，不得伪装成当前目标 blocker。

### 2. 选题与任务书

用户没有指定选题时：

```bash
python3 {skill_dir}/scripts/fetch_hotspots.py --limit 30
python3 {skill_dir}/scripts/seo_keywords.py --json "<候选关键词>"
```

读取 `references/topic-selection.md` 和 `references/frameworks.md`，结合账号主题、近期历史与
读者收益选题。不要虚构热度、阅读量或搜索量。

创建文章目录后，先完整读取 `references/editorial-workflow.md`，填写 `brief.yaml`。先定义目标
读者、真正问题、读后收获、核心判断、新增价值、适用边界和最强反方，再写正文。

### 3. 主张与来源

围绕文章真正需要证明的 3–6 个主张搜索。优先原始报告、官方文档、当事方材料和高可信媒体；
打开原页面核对后再写入 `sources.yaml`。把事实、推断、意见和用户经历分别写入
`claims.yaml`：

- `fact` 必须有直接支持它的已核验来源。
- `inference` 必须列依据并明确是推断。
- `opinion` 不伪装成共识。
- `user_experience` 只能来自用户在当前任务明确提供的材料。
- `unsupported` 主张不得进入初稿；材料不足时缩小主张或换框架。

不得编造作者经历、朋友同事、采访、对话、时间地点、感官细节、数字或引语。范文只校准结构
和节奏，不能提供可挪用的观点、个人经历或句子。

### 4. 初稿

读取：

```text
references/writing-guide.md
references/layout-playbook.md
playbook.md（存在时）
personas/<style.yaml 的 writing_persona>.yaml
```

优先级为：事实与任务书 > 用户本轮要求 > 经确认的 playbook 规则 > persona > 通用写作指南。
把初稿写入 `draft.md`。开头尽快进入问题或判断，每一节服务一个 `claim_id`，并清楚表达证据
边界。排版模块按内容目标少量使用，不按固定数量堆卡片。

不要为“像人”强行制造错句、随机离题、情绪配额、破句数量或虚假具体细节。机械人味/SEO
分数用于定位风险，不替代编辑判断，也不作为作者身份检测结论。

### 5. 编辑、SEO 与成稿

按 `references/editorial-workflow.md` 从“准确、观点、有用、合声、好读”五项审稿。能修的问题
直接修改后复审，最多两轮；来源不支持的内容要补查、删除或缩小，不得用模型记忆补洞。

只有满足全部条件时，才把终稿写入 `article.md`：

- 没有编造个人材料或未支持的核心事实。
- 五项平均分不低于 4，单项不低于 3。
- `generated/review-report.json` 的 `decision=pass`、`publishable=true`。
- `draft-metadata.json` 的 `editorial.publishable=true` 与报告一致。

生成一个主标题、两个准确的备选标题、摘要和 3–5 个标签。标题不以虚构数字、身份或结果换
点击率。保留 `draft.md`，不要用成稿覆盖初稿。

### 6. 可选视觉

只有用户要求封面、配图或“完整制作”时读取 `references/visual-prompts.md`。先把可追溯提示词
写入 `generated/image-prompts.md`，再决定是只交付提示词、生成占位图还是调用图片服务。

- 远程生图前明确数量与费用上限；缺图片配置时只交付提示词，不产生费用。
- 不按固定数量凑内文图；只为确实需要解释、对比或缓冲阅读的段落配图。
- 逐张生成、逐张验收，只重试失败槽位；不得覆盖已经通过的图片。
- 封面使用 `assets/cover-wide.jpg` 和 `assets/cover-square.jpg`；正文图使用稳定槽位名。

### 7. 本地渲染与预览

读取 `references/template-workflow.md` 后执行：

```powershell
powershell -ExecutionPolicy Bypass -File {skill_dir}/scripts/render_wechat_article.ps1 -ArticleDir "{article_dir}"
powershell -ExecutionPolicy Bypass -File {skill_dir}/scripts/check_wechat_article.ps1 -ArticleDir "{article_dir}" -Target Preview
```

`Preview` readiness 只检查本地预览所需内容；缺微信密钥、远程生图配置或封面不能冒充预览
blocker。生成的 `preview.html` 必须来自本轮成功渲染，不能把旧文件当成成功结果。

### 8. 明确授权后发布

用户本轮明确要求草稿箱发布时，先做不产生外部副作用的检查：

```powershell
powershell -ExecutionPolicy Bypass -File {skill_dir}/scripts/check_wechat_article.ps1 -ArticleDir "{article_dir}" -Target Publish
powershell -ExecutionPolicy Bypass -File {skill_dir}/scripts/publish_wechat_article.ps1 -ArticleDir "{article_dir}" -DryRun
```

只有 `Publish` readiness 为 `ready`，且 `fail=0 / warn=0 / skip=0` 时，才执行不带 `-DryRun`
的发布命令。发布前必须有已审稿成稿、有效摘要、横版/方形封面、所有引用图片、可用微信配置、
通过的 HTML/编码/对比度检查。发布失败时保留本地预览和报告，不自动重复创建草稿。

## 完成协议

- `DONE`：用户请求的目标已完成，目标 readiness 为 `ready`，且对应门禁零非通过项。
- `DONE_WITH_CONCERNS`：已交付可查看产物，但用户接受了不影响当前目标的降级；不得称为已发布。
- `BLOCKED`：当前目标存在 blocker，或修复两轮后仍无法通过。
- `NEEDS_CONTEXT`：只有缺失信息会实质改变文章判断且无法安全缩小范围时使用。

结束时报告标题、文章目录、`brief/claims/sources` 数量、审稿决定、预览路径、视觉结果、
是否创建草稿及 `media_id`。提醒用户编辑后可以说“学习我的修改”，但不要用模板化话术掩盖
未完成项。

## 辅助命令

```bash
# 主题画廊
python3 {skill_dir}/toolkit/cli.py gallery

# 单独诊断
python3 {skill_dir}/scripts/diagnose.py --json

# 学习修改 / 数据复盘按对应 reference 执行
```

用户要求更新 WeWrite 时，先检查 Git 工作区；只有工作区干净且远端明确时才拉取更新。不得用
更新命令覆盖本地配置、文章、历史、playbook 或未提交修改。
