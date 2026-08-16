# NOTICE

This repository is an independently maintained integration for WeChat Official Account content production. It
contains original project work and historically integrated ideas or materials from upstream projects. The root
MIT license does not replace or broaden any third-party license.

## Upstream references

### imraywang/wewrite

- Repository: <https://github.com/imraywang/wewrite>
- Revision reviewed for the 2026-08-16 update: `b998de801bf13cb251caa2a4c529f99cdfdd6537`
- License observed at that revision: MIT
- Ideas referenced in this project: article briefs, claim/source ledgers, draft/final separation, editorial review,
  optional visual/publish stages, and resumable task thinking.

The implementation in this repository is adapted to its existing article-directory, template-rendering and
PowerShell-wrapper architecture; it is not a mirror of the upstream package or its multi-skill CLI layout.

### geekjourneyx/md2wechat-skill

- Repository: <https://github.com/geekjourneyx/md2wechat-skill>
- Revision reviewed for the 2026-08-16 update: `d656438f1e9994fb7f4560c43d51eb7fd0a1ceb3`
- License observed at that revision: md2wechat Source Available License, with commercial-use restrictions and a
  stated future change license.
- General workflow ideas referenced in this update: discovery before capability selection, target-specific
  readiness, preview/publish separation, explicit authorization for side effects, and stale-preview handling.

No source code, themes, layout modules, prompt catalogs, assets, or documentation from that reviewed revision
were copied into this update. Do not import current md2wechat content into this MIT repository without checking
and complying with its license or obtaining the required permission.

The former `skill2 paibanyouhua/.agents/skills/md2wechat/` snapshot and its copied command references were
removed in this update. The remaining file at that path is a project-authored compatibility bridge that routes to
this repository's own scripts; it does not bundle the current upstream CLI, themes, layouts, prompts or docs.

### Historical WeWrite lineage

Earlier versions of this repository also cited `oaker-io/wewrite` as a source of the original公众号内容流程
思路. That historical attribution is preserved here even though the current update was compared against
`imraywang/wewrite` as requested.

## Project-specific direction

This repository's own direction is to combine:

- a traceable editorial dossier for each article;
- strict separation between draft, reviewed article and generated HTML;
- target-scoped zero-warning readiness checks;
- stable image slots and detailed Chinese visual prompts;
- cross-platform local rendering and explicit WeChat draft operations;
- private-by-default handling of credentials, style files, history, corpus and article output.

When reusing this repository, keep upstream notices and license terms with any third-party-derived material.
