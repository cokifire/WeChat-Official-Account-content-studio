# WeChat Official Account Content Studio

> 面向微信公众号的可追溯内容工作室：先定义读者问题和证据边界，再写作、审稿、排版；只有
> 用户明确授权且发布目标通过零 warning 门禁时，才创建微信草稿。

![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=flat-square&logo=python&logoColor=white)
![WeChat](https://img.shields.io/badge/WeChat-Official%20Account-07C160?style=flat-square&logo=wechat&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-black?style=flat-square)

![WeChat Official Account Content Studio](assets/repo/hero.jpg)

它不是一个“把 Markdown 换皮”的脚本集合，也不是一条默认自动发布的黑盒流水线。核心思路是：

```text
读者问题 → 文章任务书 → 主张与来源 → 初稿 → 编辑复审 → 成稿
                                                   ├─ 可选封面 / 配图
                                                   ├─ 本地预览
                                                   └─ 明确授权后推草稿箱
```

## 这版解决了什么

- **先有内容契约再写稿**：每篇文章保存 `brief.yaml`、`claims.yaml`、`sources.yaml`、
  `draft.md`、`article.md` 和 `review-report.json`，能追溯文章为何这样写。
- **不编造作者经历**：用户没有提供个人材料时，可以写作者判断，不能虚构朋友、采访、对话、
  时间地点和感官场景。
- **编辑判断高于机械分数**：准确、观点、有用、合声、好读五项决定能否交付；“人味”、SEO
  和节奏分只作风险提示，不用于证明作者身份。
- **Preview / Publish 分目标检查**：本地预览不要求微信密钥、封面或图片 API；发布则必须满足
  审稿、封面、图片、配置、HTML、编码和平台约束。
- **外部副作用需本轮授权**：“写一篇”和“完整制作”都不会创建微信草稿；只有本轮明确说
  “推到草稿箱 / 发布”才执行上传和草稿操作。
- **保留本仓库的强项**：单篇独立目录、中文视觉提示词、稳定图片槽位、16 套主题、自动版式、
  暗黑模式、跨平台 PowerShell 入口和零 warning 发布门禁。

## 默认行为

| 你说 | 默认结果 | 不会做 |
|---|---|---|
| “写一篇公众号文章” | 审过的成稿 + 本地预览 | 不生图、不发布 |
| “完整制作一篇” | 成稿 + 封面/必要配图 + 本地预览 | 不发布 |
| “只做封面提示词” | 可追溯的提示词文件 | 不调用图片 API |
| “排版预览这篇 Markdown” | 本轮新生成的 `preview.html` | 不要求微信配置 |
| “检查能不能发布” | Publish readiness + DryRun | 不创建/更新草稿 |
| “推到草稿箱” | 通过全部门禁后创建或更新草稿 | 失败时不自动重试 |

## 单篇文章目录

```text
output/<工作标题>/
├── brief.yaml                    # 目标读者、问题、判断、反方、边界
├── claims.yaml                   # fact / inference / opinion / user_experience
├── sources.yaml                  # 原始来源与核验状态
├── draft.md                      # 未经编辑通过的初稿
├── article.md                    # 通过编辑门槛后的成稿
├── article-illustrated.md        # 可选带图副本，不覆盖成稿
├── draft-metadata.json           # 内容、排版、编辑与发布状态
├── article-body.template.html    # 可重建的发布 HTML
├── preview.html                  # 可重建的本地预览
├── assets/
│   ├── cover-wide.jpg
│   ├── cover-square.jpg
│   └── img-01.jpg
└── generated/
    ├── review-report.json
    ├── image-prompts.md
    ├── layout-plan.json
    ├── quality-gates.json
    └── publish-result.json
```

`draft.md` 与 `article.md` 分开：初稿经过修改后，只有审稿报告
`decision=pass / publishable=true` 才写入成稿。视觉和发布步骤不得覆盖已审稿正文。
带图副本完成后通过 `draft-metadata.json.render_source` 显式选择，避免误渲染陈旧副本。

## 五项编辑门槛

| 维度 | 判断问题 |
|---|---|
| 准确 | 核心事实有直接来源吗？事实、推断、意见分开了吗？ |
| 观点 | 有清晰判断、新增价值、适用边界和最强反方吗？ |
| 有用 | 真正回答了目标读者的问题，并给出行动或判断方法吗？ |
| 合声 | 符合账号语气，同时没有编造个人材料或挪用范文吗？ |
| 好读 | 开头进入问题，各节各有任务，论证连贯且适合手机阅读吗？ |

通过条件：平均分至少 4、单项不低于 3、没有阻断问题。能修的问题必须实际改稿并复审，不能
只列一份“优化建议”就把初稿称为成稿。

## 目标就绪检查

质量报告区分两类信息：

- `checks`：当前目标的硬门禁；任何 `warn / fail / skip` 都会令 readiness 变成 `blocked`。
- `advisories`：人味、SEO、可选增强和未请求能力的提示，不冒充当前目标 blocker。

因此，“零 warning”是**目标相关的零 warning**：本地预览不需要为了清零去配置微信密钥，
纯文字文章也不需要为了清零硬塞内文图；但发布必须通过审稿、摘要、双封面、引用图片、微信
配置、结构、编码、对比度和预检。

下面的入口脚本需要 PowerShell 7。macOS/Linux 使用 `pwsh`，Windows 使用 `pwsh.exe`；只有仍在
使用 Windows PowerShell 5.1 时才改用 `powershell.exe`。

```powershell
# 创建文章目录（只生成脚手架）
pwsh -NoProfile -ExecutionPolicy Bypass -File scripts/new_wechat_article.ps1 -Title "文章标题"

# 先填写 brief/claims/sources 和 draft，完成审稿后再写入 article.md
# article.md 正文字符数至少 200，不能直接渲染刚创建的占位内容

# 渲染并检查本地预览
pwsh -NoProfile -ExecutionPolicy Bypass -File scripts/render_wechat_article.ps1 -ArticleDir "文章标题"
pwsh -NoProfile -ExecutionPolicy Bypass -File scripts/check_wechat_article.ps1 -ArticleDir "文章标题" -Target Preview

# 只检查发布就绪状态
pwsh -NoProfile -ExecutionPolicy Bypass -File scripts/check_wechat_article.ps1 -ArticleDir "文章标题" -Target Publish

# 无外部副作用的发布干跑
pwsh -NoProfile -ExecutionPolicy Bypass -File scripts/publish_wechat_article.ps1 -ArticleDir "文章标题" -DryRun

# 用户明确授权后创建或更新草稿
pwsh -NoProfile -ExecutionPolicy Bypass -File scripts/publish_wechat_article.ps1 -ArticleDir "文章标题"
```

## 安装

### Codex

```bash
git clone --depth 1 https://github.com/wengzige/WeChat-Official-Account-content-studio.git ~/.codex/skills/wewrite
cd ~/.codex/skills/wewrite
python3 -m venv .venv
./.venv/bin/python -m pip install -r requirements.txt
```

仓库包含 `agents/openai.yaml`，安装到 Codex skills 目录后可直接触发。

### Claude Code / OpenClaw

把同一仓库克隆到对应 skills 目录：

```bash
# Claude Code
git clone --depth 1 https://github.com/wengzige/WeChat-Official-Account-content-studio.git ~/.claude/skills/wewrite

# OpenClaw
git clone --depth 1 https://github.com/wengzige/WeChat-Official-Account-content-studio.git ~/.openclaw/skills/wewrite
```

macOS/Linux 使用 `.venv/bin/python`；Windows 使用 `.venv\Scripts\python.exe`。项目脚本会按平台
解析虚拟环境；上述 `.ps1` 入口还需要 PowerShell 7 的 `pwsh` 命令。

## 配置

首次使用可直接让 skill 引导生成 `style.yaml`，也可以复制示例：

```bash
cp style.example.yaml style.yaml
cp config.example.yaml config.yaml
```

- `style.yaml`：账号、读者、主题、人格和禁用表达。
- `config.yaml`：微信 AppID/Secret 和可选图片服务。
- 缺 `config.yaml` 仍可写作与本地预览。
- 缺图片 API 仍可输出完整图片提示词。
- `config.yaml`、`style.yaml`、历史、语料、文章输出和 `.venv/` 默认不进入 Git。

## 视觉工作流

视觉是独立步骤，不按固定字数或固定数量凑图：

1. 先在 `generated/image-prompts.md` 记录槽位、用途、对应段落、alt、图例、正负提示词和验收点。
2. 用户只要提示词时到此结束，不调用图片服务。
3. 远程生图前明确数量和费用上限，按槽位逐张生成、逐张验收。
4. 封面固定使用 `cover-wide.jpg` 和 `cover-square.jpg`；正文图使用稳定文件名。
5. 不合格时只重做失败槽位，不批量盲跑，不覆盖已通过图片。

详细规范见 [`references/visual-prompts.md`](references/visual-prompts.md)。

## 排版引擎

仓库内置 16 套主题：

| 类别 | 主题 |
|---|---|
| 通用 | `professional-clean`、`minimal`、`newspaper` |
| 科技 | `tech-modern`、`bytedance`、`github` |
| 文艺 | `warm-editorial`、`sspai`、`ink`、`elegant-rose` |
| 商务 | `bold-navy`、`minimal-gold`、`bold-green` |
| 风格 | `bauhaus`、`focus-red`、`midnight` |

```bash
python3 toolkit/cli.py themes
python3 toolkit/cli.py gallery
```

主题支持内联样式、CJK/Latin 间距、外链脚注、列表转换、暗黑模式和常用容器语法。自动版式会
生成 `generated/layout-plan.json`，但模块数量始终服从文章目标：attention、readability、
memorability、conversion；不为“看起来丰富”堆卡片。

## 项目结构

```text
├── SKILL.md                       # 精简主入口与安全边界
├── agents/openai.yaml             # Codex UI 元数据
├── references/
│   ├── editorial-workflow.md      # 任务书、主张、来源与审稿契约
│   ├── writing-guide.md           # 表达与移动阅读规范
│   ├── template-workflow.md       # Preview/Publish readiness
│   ├── visual-prompts.md          # 中文视觉提示词与验收
│   └── ...
├── scripts/                        # 热点、SEO、学习、诊断与跨平台入口
├── skill2 paibanyouhua/
│   ├── templates/                  # 单篇文章模板
│   └── scripts/                    # 创建、渲染、门禁与发布
├── toolkit/                        # Markdown → 微信 HTML 与微信 API
├── personas/                       # 5 套表达人格，统一禁止虚构个人材料
└── evals/                          # skill 行为评测场景
```

## 上游参考与许可

本仓库持续参考：

- [`imraywang/wewrite`](https://github.com/imraywang/wewrite)：当前为 MIT，用于理解模块化内容流程、
  文章任务书、主张/来源账本和编辑复审思路。
- [`geekjourneyx/md2wechat-skill`](https://github.com/geekjourneyx/md2wechat-skill)：当前采用
  Source Available License。本仓库只参考其 discovery、目标 readiness 和副作用边界等通用
  工作流思想；不要把其最新代码、主题、布局模块或文档按 MIT 内容复制进本仓库。

具体来源、衍生范围和许可提醒见 [`NOTICE.md`](NOTICE.md)。

## 公开仓库安全

推送前运行：

```bash
python3 scripts/git_privacy_guard.py --commit HEAD
```

不要提交 `config.yaml`、`.env`、微信凭据、图片 API key、`style.yaml`、历史、playbook、语料、
文章输出、质量报告或虚拟环境。

## License

本仓库自行创作并明确标注为本项目内容的部分采用 MIT License。第三方内容仍受其各自许可
约束；使用或分发前请阅读 [`NOTICE.md`](NOTICE.md) 和对应上游许可证。
