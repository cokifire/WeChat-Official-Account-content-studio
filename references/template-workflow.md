# 模板草稿链与目标就绪检查

本规则定义 WeWrite 的单篇文章目录、渲染、预览与草稿箱发布边界。只要任务涉及公众号排版、
预览或发布，就完整读取本文件。

## 目录与源文件

- 新稿件使用 `{skill_dir}/output/<工作标题>/`。
- 通过 `scripts/new_wechat_article.ps1` 创建目录，不手工拼装模板文件。
- `brief.yaml`、`claims.yaml`、`sources.yaml`、`draft.md` 和
  `generated/review-report.json` 共同记录内容生产过程。
- `article.md` 是通过审稿后的唯一成稿源文件；视觉流程不得覆盖它。
- `article-illustrated.md` 是可选带图副本；只有 `draft-metadata.json.render_source` 明确
  指向它时才参与渲染。
- `article-body.template.html`、`preview.html`、`generated/output.html` 和
  `generated/draft.json` 都是可重建产物，不得反向覆盖正文。
- 详细内容契约见 `references/editorial-workflow.md`。

## 图片与提示词

- 图片统一放在 `assets/`；横版封面为 `assets/cover-wide.jpg`，方形封面为
  `assets/cover-square.jpg`，正文图使用 `assets/img-01.jpg` 这类稳定槽位。
- Markdown 可写 `![配图 1](img-01.jpg)`；渲染脚本会映射到 `assets/img-01.jpg`。
- 提示词统一写入 `generated/image-prompts.md`。
- 本地预览允许没有封面和正文图；正文一旦引用本地图，该文件必须存在。
- 草稿箱发布必须有两种封面和全部引用图片，但发布流程不得为了补图自动调用远程生图。

## 三个动作不能互换

| 动作 | 职责 | 外部副作用 |
|---|---|---|
| `render` | 从本轮元数据指定的 `render_source` 生成 HTML、预览和检查输入 | 无 |
| `check -Target Preview/Publish` | 输出目标相关 readiness 与 blockers | 无 |
| `publish` | 上传素材并创建或更新微信草稿 | 有，必须本轮明确授权 |

预览文件只在本轮渲染成功后有效。渲染失败时，即使目录里有旧 `preview.html`，也要把它视为
陈旧产物，不能报告为本次成功结果。

## Preview readiness

```powershell
powershell -ExecutionPolicy Bypass -File {skill_dir}/scripts/render_wechat_article.ps1 -ArticleDir "<文章目录>"
powershell -ExecutionPolicy Bypass -File {skill_dir}/scripts/check_wechat_article.ps1 -ArticleDir "<文章目录>" -Target Preview
```

`Preview` 只检查：正文与元数据可读、渲染产物来自本轮、引用图片存在、结构与编码可用、主题
文字可读。微信凭据、远程图片 API、未请求的封面和历史学习文件都不是预览 blocker。

## Publish readiness

```powershell
powershell -ExecutionPolicy Bypass -File {skill_dir}/scripts/check_wechat_article.ps1 -ArticleDir "<文章目录>" -Target Publish
powershell -ExecutionPolicy Bypass -File {skill_dir}/scripts/publish_wechat_article.ps1 -ArticleDir "<文章目录>" -DryRun
```

`Publish` 在预览检查之上必须确认：

- `draft-metadata.json` 和 `generated/review-report.json` 都为 `publishable=true`。
- `brief.yaml`、`claims.yaml`、`sources.yaml`、`draft.md`、`article.md` 完整存在。
- 标题、摘要、横版/方形封面和所有引用图片满足平台限制。
- 微信配置可用，HTML 无危险占位符、乱码、HTML 注释或未允许的原生列表。
- 质量报告的 `summary.fail / warn / skip` 全为 0，`readiness.status=ready`。

只有用户本轮明确授权，且上述检查全部通过时，才执行不带 `-DryRun` 的发布命令。发布失败
保留预览、检查报告和错误结果，不自动重试或切换另一条发布链。

## 质量报告语义

- `checks`：当前目标真正需要通过的门禁；任何 `warn/fail/skip` 都使目标 blocked。
- `advisories`：人味、SEO、可选增强等诊断信息；用于编辑判断，不伪装成 blocker。
- `readiness.blockers`：从当前目标的非通过 `checks` 生成，作为是否继续的唯一机器判断。

“零 warning”针对当前目标，不要求为了本地预览配置微信密钥，也不要求为了纯文字文章强行凑图。

## 路径与兼容

- macOS/Linux 优先 `.venv/bin/python`，Windows 优先 `.venv\Scripts\python.exe`。
- PowerShell 路径使用分段 `Join-Path`，不要混用 `/` 和 `\`。
- 指定发布配置时使用 `-Config "<config.yaml 路径>"`。
- 默认发布入口是 `scripts/publish_wechat_article.ps1`；`toolkit/cli.py publish` 只保留给旧流程。
