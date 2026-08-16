import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]


def read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def load_quality_module():
    module_path = ROOT / "skill2 paibanyouhua" / "scripts" / "run-quality-gates.py"
    spec = importlib.util.spec_from_file_location("wewrite_quality_gates", module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class SkillContractTests(unittest.TestCase):
    def test_skill_frontmatter_is_minimal_and_body_is_progressive(self):
        skill = read("SKILL.md")
        _, frontmatter, body = skill.split("---", 2)
        metadata = yaml.safe_load(frontmatter)
        self.assertEqual({"name", "description"}, set(metadata))
        self.assertLess(len(body.splitlines()), 500)
        self.assertIn("references/editorial-workflow.md", body)
        self.assertIn("-Target Preview", body)
        self.assertIn("-Target Publish", body)

    def test_default_writing_has_no_remote_side_effect(self):
        skill = read("SKILL.md")
        self.assertIn("不调用付费生图服务", skill)
        self.assertIn("不创建微信草稿", skill)
        self.assertIn("只有用户在本轮明确说", skill)

    def test_personas_share_personal_material_boundary(self):
        for persona_path in (ROOT / "personas").glob("*.yaml"):
            persona = yaml.safe_load(persona_path.read_text(encoding="utf-8"))
            self.assertEqual(
                "only_current_user_supplied",
                persona.get("personal_material_policy"),
                persona_path.name,
            )

    def test_article_templates_include_editorial_dossier(self):
        template_root = ROOT / "skill2 paibanyouhua" / "templates"
        for name in (
            "brief.yaml.template",
            "claims.yaml.template",
            "sources.yaml.template",
            "draft.md.template",
            "article.md.template",
            "review-report.json.template",
        ):
            self.assertTrue((template_root / name).is_file(), name)

        metadata = json.loads((template_root / "draft-metadata.json.template").read_text(encoding="utf-8"))
        self.assertEqual(2, metadata["workflow_version"])
        self.assertEqual("article.md", metadata["render_source"])
        self.assertFalse(metadata["editorial"]["publishable"])
        self.assertEqual("generated/review-report.json", metadata["editorial"]["review_report"])

    def test_wrappers_route_to_target_specific_checks(self):
        self.assertIn('"--target", "preview"', read("scripts/render_wechat_article.ps1"))
        self.assertIn("[ValidateSet('Preview', 'Publish')]", read("scripts/check_wechat_article.ps1"))
        self.assertIn('"publish"', read("skill2 paibanyouhua/scripts/publish-article.py"))

    def test_documented_commands_are_cross_platform_and_ordered(self):
        readme = read("README.md")
        skill = read("SKILL.md")
        documented = readme + skill

        self.assertNotIn("powershell -ExecutionPolicy", documented)
        self.assertIn("pwsh -NoProfile -ExecutionPolicy Bypass", readme)
        self.assertIn("pwsh -NoProfile -ExecutionPolicy Bypass", skill)
        self.assertIn("正文字符数至少 200", readme)
        self.assertIn("不少于 200 个正文", skill)
        self.assertLess(readme.index("只生成脚手架"), readme.index("渲染并检查本地预览"))


class ContentReadinessTests(unittest.TestCase):
    def setUp(self):
        self.quality = load_quality_module()
        self.temp_dir = tempfile.TemporaryDirectory()
        self.article_dir = Path(self.temp_dir.name)
        (self.article_dir / "generated").mkdir()
        (self.article_dir / "brief.yaml").write_text(
            """version: 1
audience:
  question: 读者问题
goal:
  takeaway: 读后结论
thesis:
  statement: 核心判断
""",
            encoding="utf-8",
        )
        (self.article_dir / "claims.yaml").write_text(
            """version: 1
claims:
  - id: C1
    text: 一个事实
    type: fact
    source_ids: [S1]
    status: supported
""",
            encoding="utf-8",
        )
        (self.article_dir / "sources.yaml").write_text("version: 1\nsources: []\n", encoding="utf-8")
        (self.article_dir / "draft.md").write_text("draft", encoding="utf-8")
        (self.article_dir / "article.md").write_text("article", encoding="utf-8")
        (self.article_dir / "generated" / "review-report.json").write_text(
            json.dumps({"decision": "needs_review", "publishable": False}),
            encoding="utf-8",
        )
        self.metadata = {
            "workflow_version": 2,
            "content_contract": {
                "brief": "brief.yaml",
                "claims": "claims.yaml",
                "sources": "sources.yaml",
                "draft": "draft.md",
                "article": "article.md",
            },
            "editorial": {
                "decision": "needs_review",
                "publishable": False,
                "review_report": "generated/review-report.json",
            },
        }

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_preview_does_not_require_publishable_editorial_state(self):
        checks, advisories = self.quality.evaluate_content_contract(
            self.article_dir,
            self.metadata,
            "preview",
        )
        self.assertTrue(all(item["status"] == "pass" for item in checks))
        editorial = next(item for item in advisories if item["name"] == "editorial_status")
        self.assertEqual("pending", editorial["level"])

    def test_publish_requires_review_and_verified_fact_source(self):
        checks, _ = self.quality.evaluate_content_contract(self.article_dir, self.metadata, "publish")
        by_name = {item["name"]: item for item in checks}
        self.assertEqual("fail", by_name["content_evidence"]["status"])
        self.assertEqual("fail", by_name["editorial_publishable"]["status"])

        (self.article_dir / "sources.yaml").write_text(
            """version: 1
sources:
  - id: S1
    url: https://example.com/source
    status: verified
""",
            encoding="utf-8",
        )
        (self.article_dir / "generated" / "review-report.json").write_text(
            json.dumps({"decision": "pass", "publishable": True}),
            encoding="utf-8",
        )
        self.metadata["editorial"].update({"decision": "pass", "publishable": True})

        checks, _ = self.quality.evaluate_content_contract(self.article_dir, self.metadata, "publish")
        by_name = {item["name"]: item for item in checks}
        self.assertEqual("pass", by_name["content_evidence"]["status"])
        self.assertEqual("pass", by_name["editorial_publishable"]["status"])

    def test_publish_payload_blocks_editor_comments(self):
        status, detail, data = self.quality.publish_payload_safety_check(
            "<section><!-- editor note --><p>正文</p></section>"
        )
        self.assertEqual("fail", status)
        self.assertIn("HTML comment", detail)
        self.assertIn("HTML comment", data["issues"])

    def test_legacy_article_can_preview_but_cannot_publish(self):
        preview_checks, preview_advisories = self.quality.evaluate_content_contract(
            self.article_dir,
            {},
            "preview",
        )
        self.assertEqual([], preview_checks)
        self.assertEqual("content_contract", preview_advisories[0]["name"])

        publish_checks, _ = self.quality.evaluate_content_contract(
            self.article_dir,
            {},
            "publish",
        )
        self.assertEqual("fail", publish_checks[0]["status"])


if __name__ == "__main__":
    unittest.main()
