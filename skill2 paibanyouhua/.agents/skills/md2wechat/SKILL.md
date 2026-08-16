---
name: md2wechat
description: |
  当前仓库内的微信公众号 Markdown 排版兼容入口。仅在宿主直接选择 md2wechat 时使用；
  实际渲染、目标就绪检查和草稿箱发布都转到仓库主 WeWrite 工作流。
---

# md2wechat 兼容桥

不要假设外部 `md2wechat` CLI 已安装，也不要从旧命令手册猜测主题、provider 或发布能力。
当前仓库使用自己的 Python converter、模板脚本和微信 API 发布器。

定位仓库根目录后，完整读取根目录 `SKILL.md`，并按用户意图执行：

```powershell
# 本地渲染与 Preview readiness
powershell -ExecutionPolicy Bypass -File scripts/render_wechat_article.ps1 -ArticleDir "<文章目录>"
powershell -ExecutionPolicy Bypass -File scripts/check_wechat_article.ps1 -ArticleDir "<文章目录>" -Target Preview

# Publish readiness；不会创建草稿
powershell -ExecutionPolicy Bypass -File scripts/check_wechat_article.ps1 -ArticleDir "<文章目录>" -Target Publish
powershell -ExecutionPolicy Bypass -File scripts/publish_wechat_article.ps1 -ArticleDir "<文章目录>" -DryRun
```

只有用户本轮明确要求发布，且 Publish readiness 与 DryRun 都通过时，才执行不带 `-DryRun`
的发布命令。排版、预览和检查不得上传图片或创建微信草稿。

若用户明确要求使用外部 `md2wechat` 产品的当前 CLI、主题或布局目录，本兼容桥不提供这些
能力；应单独安装并遵守该项目当前许可证，不能把其受限代码或资源复制进本仓库。
