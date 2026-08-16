#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path, PurePosixPath

import yaml


REPO_ROOT = Path(__file__).resolve().parents[2]
WORKFLOW_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from layout_strategy import evaluate_layout_diversity  # noqa: E402


def configure_stdio() -> None:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            try:
                reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass


def utf8_len(text: str) -> int:
    return len(text.encode("utf-8"))


def normalize_image_src(src: str) -> str:
    normalized = src.replace("\\", "/").lstrip("./")
    if normalized.startswith(("http://", "https://")):
        return normalized
    if normalized.startswith("assets/"):
        return normalized
    pure = PurePosixPath(normalized)
    if len(pure.parts) == 1:
        return f"assets/{pure.name}"
    return normalized


def resolve_article_file(article_dir: Path, src: str) -> Path:
    normalized = src.replace("\\", "/").lstrip("./")
    candidate = article_dir.joinpath(*PurePosixPath(normalized).parts).resolve()
    try:
        candidate.relative_to(article_dir.resolve())
    except ValueError as exc:
        raise ValueError(f"article asset escapes article directory: {src}") from exc
    return candidate


def run_json_command(command: list[str]) -> tuple[object | None, str | None]:
    try:
        completed = subprocess.run(
            command,
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
    except Exception as exc:
        return None, str(exc)

    stdout = completed.stdout.strip()
    stderr = completed.stderr.strip()
    raw = stdout or stderr
    if stdout:
        try:
            return json.loads(stdout), None
        except Exception:
            pass

    if completed.returncode != 0:
        return None, raw or f"command failed: {' '.join(command)}"

    try:
        return json.loads(raw), None
    except Exception as exc:
        return None, f"invalid json output: {exc}; raw={raw[:500]}"


def resolve_powershell() -> str | None:
    return shutil.which("pwsh") or shutil.which("powershell")


def make_check(name: str, status: str, detail: str, *, data: object | None = None) -> dict:
    check = {"name": name, "status": status, "detail": detail}
    if data is not None:
        check["data"] = data
    return check


def add_check(checks: list[dict], name: str, status: str, detail: str, *, data: object | None = None) -> None:
    checks.append(make_check(name, status, detail, data=data))


def add_advisory(
    advisories: list[dict],
    name: str,
    detail: str,
    *,
    level: str = "info",
    data: object | None = None,
) -> None:
    item = {"name": name, "level": level, "detail": detail}
    if data is not None:
        item["data"] = data
    advisories.append(item)


def load_yaml_mapping(path: Path) -> dict:
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise ValueError(f"{path.name} must contain a YAML mapping")
    return data


def nested_text(data: dict, *keys: str) -> str:
    current: object = data
    for key in keys:
        if not isinstance(current, dict):
            return ""
        current = current.get(key)
    return str(current or "").strip()


def evaluate_content_contract(
    article_dir: Path,
    metadata: dict,
    target: str,
) -> tuple[list[dict], list[dict]]:
    checks: list[dict] = []
    advisories: list[dict] = []
    try:
        workflow_version = int(metadata.get("workflow_version") or 1)
    except (TypeError, ValueError):
        workflow_version = 1

    if workflow_version < 2:
        if target == "publish":
            add_check(
                checks,
                "content_contract",
                "fail",
                "legacy article has no v2 editorial dossier; migrate it before publishing",
            )
        else:
            add_advisory(
                advisories,
                "content_contract",
                "legacy article: editorial dossier is not required for preview",
            )
        return checks, advisories

    configured_paths = metadata.get("content_contract")
    if not isinstance(configured_paths, dict):
        configured_paths = {}
    contract_paths = {
        "brief": str(configured_paths.get("brief") or "brief.yaml"),
        "claims": str(configured_paths.get("claims") or "claims.yaml"),
        "sources": str(configured_paths.get("sources") or "sources.yaml"),
        "draft": str(configured_paths.get("draft") or "draft.md"),
        "article": str(configured_paths.get("article") or "article.md"),
    }

    resolved: dict[str, Path] = {}
    for name, relative in contract_paths.items():
        try:
            path = resolve_article_file(article_dir, relative)
        except ValueError as exc:
            add_check(checks, f"content_{name}", "fail", str(exc))
            continue
        resolved[name] = path
        add_check(
            checks,
            f"content_{name}",
            "pass" if path.exists() else "fail",
            f"{name} {'found' if path.exists() else 'missing'}: {path}",
        )

    review_relative = "generated/review-report.json"
    editorial = metadata.get("editorial")
    if isinstance(editorial, dict):
        review_relative = str(editorial.get("review_report") or review_relative)
    try:
        review_path = resolve_article_file(article_dir, review_relative)
    except ValueError as exc:
        add_check(checks, "content_review_report", "fail", str(exc))
        return checks, advisories
    add_check(
        checks,
        "content_review_report",
        "pass" if review_path.exists() else "fail",
        f"review report {'found' if review_path.exists() else 'missing'}: {review_path}",
    )

    if len(resolved) != len(contract_paths) or any(not path.exists() for path in resolved.values()) or not review_path.exists():
        return checks, advisories

    try:
        brief = load_yaml_mapping(resolved["brief"])
        claims_doc = load_yaml_mapping(resolved["claims"])
        sources_doc = load_yaml_mapping(resolved["sources"])
        review = json.loads(review_path.read_text(encoding="utf-8"))
        if not isinstance(review, dict):
            raise ValueError("review-report.json must contain a JSON object")
    except Exception as exc:
        add_check(checks, "content_contract_parse", "fail", f"content dossier is invalid: {exc}")
        return checks, advisories

    add_check(checks, "content_contract_parse", "pass", "content dossier files are valid YAML/JSON mappings")

    claims = claims_doc.get("claims") or []
    sources = sources_doc.get("sources") or []
    if not isinstance(claims, list) or not isinstance(sources, list):
        add_check(checks, "content_evidence_schema", "fail", "claims and sources must be lists")
        return checks, advisories

    source_by_id = {
        str(item.get("id")): item
        for item in sources
        if isinstance(item, dict) and str(item.get("id") or "").strip()
    }
    unsupported = [
        str(item.get("id") or "?")
        for item in claims
        if isinstance(item, dict) and str(item.get("status") or "").strip() == "unsupported"
    ]
    evidence_errors: list[str] = []
    for item in claims:
        if not isinstance(item, dict) or str(item.get("type") or "").strip() != "fact":
            continue
        claim_id = str(item.get("id") or "?")
        source_ids = item.get("source_ids") or []
        if not isinstance(source_ids, list):
            evidence_errors.append(f"fact {claim_id} source_ids must be a list")
            continue
        usable = []
        for source_id in source_ids:
            source = source_by_id.get(str(source_id))
            if source and str(source.get("status") or "") in {"verified", "user_provided"}:
                usable.append(source)
        if not usable:
            evidence_errors.append(f"fact {claim_id} has no verified source")

    if target == "publish":
        missing_brief = [
            field
            for field, value in [
                ("audience.question", nested_text(brief, "audience", "question")),
                ("goal.takeaway", nested_text(brief, "goal", "takeaway")),
                ("thesis.statement", nested_text(brief, "thesis", "statement")),
            ]
            if not value
        ]
        if not claims:
            missing_brief.append("claims")
        detail_parts = []
        if missing_brief:
            detail_parts.append("missing: " + ", ".join(missing_brief))
        if unsupported:
            detail_parts.append("unsupported claims: " + ", ".join(unsupported))
        if evidence_errors:
            detail_parts.extend(evidence_errors)
        add_check(
            checks,
            "content_evidence",
            "fail" if detail_parts else "pass",
            "; ".join(detail_parts) if detail_parts else f"claims={len(claims)} sources={len(sources)} evidence ok",
        )

        metadata_publishable = bool(isinstance(editorial, dict) and editorial.get("publishable"))
        report_publishable = bool(review.get("publishable")) and review.get("decision") == "pass"
        add_check(
            checks,
            "editorial_publishable",
            "pass" if metadata_publishable and report_publishable else "fail",
            f"metadata_publishable={metadata_publishable} report_publishable={report_publishable}",
            data={"metadata": editorial, "report": review},
        )
    else:
        add_advisory(
            advisories,
            "editorial_status",
            f"decision={review.get('decision')} publishable={bool(review.get('publishable'))}",
            level="ready" if review.get("publishable") else "pending",
            data=review,
        )

    return checks, advisories


def hex_to_rgb(value: str) -> tuple[int, int, int] | None:
    raw = value.strip()
    if not raw.startswith("#") or len(raw) not in {4, 7}:
        return None
    if len(raw) == 4:
        raw = "#" + "".join(item * 2 for item in raw[1:])
    try:
        return int(raw[1:3], 16), int(raw[3:5], 16), int(raw[5:7], 16)
    except ValueError:
        return None


def relative_luminance(rgb: tuple[int, int, int]) -> float:
    values = []
    for channel in rgb:
        value = channel / 255
        values.append(value / 12.92 if value <= 0.03928 else ((value + 0.055) / 1.055) ** 2.4)
    return 0.2126 * values[0] + 0.7152 * values[1] + 0.0722 * values[2]


def contrast_ratio(foreground: str, background: str) -> float | None:
    fg = hex_to_rgb(foreground)
    bg = hex_to_rgb(background)
    if fg is None or bg is None:
        return None
    fg_lum = relative_luminance(fg)
    bg_lum = relative_luminance(bg)
    lighter = max(fg_lum, bg_lum)
    darker = min(fg_lum, bg_lum)
    return (lighter + 0.05) / (darker + 0.05)


def html_readability_check(html: str) -> tuple[str, str, dict]:
    hex_pattern = r"#[0-9a-fA-F]{3}(?:[0-9a-fA-F]{3})?"
    backgrounds = re.findall(rf"background(?:-color)?\s*:\s*({hex_pattern})", html)
    card_background = backgrounds[1] if len(backgrounds) > 1 else (backgrounds[0] if backgrounds else "#ffffff")
    paragraph_colors = re.findall(rf"<p\b[^>]*style=\"[^\"]*color\s*:\s*({hex_pattern})", html)

    failures = []
    for color in sorted(set(paragraph_colors)):
        ratio = contrast_ratio(color, card_background)
        if ratio is not None and ratio < 4.5:
            failures.append({"color": color, "background": card_background, "contrast": round(ratio, 2)})

    if failures:
        return (
            "fail",
            "main paragraph text has insufficient contrast against template shell background",
            {"card_background": card_background, "failures": failures},
        )
    if not paragraph_colors:
        return "fail", "no styled paragraph text found for readability contrast check", {"card_background": card_background}
    return (
        "pass",
        f"paragraph contrast ok against template shell background {card_background}",
        {"card_background": card_background, "paragraph_colors": sorted(set(paragraph_colors))},
    )


def publish_payload_safety_check(html: str) -> tuple[str, str, dict]:
    issues = []
    if "\ufffd" in html:
        issues.append("replacement character")
    if "<!--" in html:
        issues.append("HTML comment")
    if re.search(r"\?{3,}", html):
        issues.append("suspicious question-mark run")

    consecutive = 0
    high_byte_count = 0
    for char in html:
        codepoint = ord(char)
        if 0x80 <= codepoint <= 0xFF:
            consecutive += 1
            high_byte_count += 1
            if consecutive >= 3 or high_byte_count >= 6:
                issues.append("suspicious mojibake")
                break
        else:
            consecutive = 0

    return (
        "fail" if issues else "pass",
        ", ".join(issues) if issues else "publish payload contains no blocked text or comments",
        {"issues": issues},
    )


def summarize(checks: list[dict]) -> dict:
    summary = {
        "pass": sum(1 for item in checks if item["status"] == "pass"),
        "warn": sum(1 for item in checks if item["status"] == "warn"),
        "fail": sum(1 for item in checks if item["status"] == "fail"),
        "skip": sum(1 for item in checks if item["status"] == "skip"),
    }
    summary["non_pass"] = summary["warn"] + summary["fail"] + summary["skip"]
    summary["passed"] = summary["warn"] == 0 and summary["fail"] == 0 and summary["skip"] == 0
    return summary


def main() -> int:
    configure_stdio()
    parser = argparse.ArgumentParser(description="Run mandatory WeWrite quality gates for a template article.")
    parser.add_argument("--article-dir", required=True)
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Compatibility flag. Quality gates are always zero-warning strict.",
    )
    parser.add_argument(
        "--target",
        choices=("preview", "publish"),
        default="preview",
        help="Evaluate only the readiness requirements for this action.",
    )
    args = parser.parse_args()
    target = args.target

    article_dir = Path(args.article_dir).resolve()
    if not article_dir.is_dir():
        print(
            json.dumps(
                {
                    "article_dir": str(article_dir),
                    "target": target,
                    "readiness": {
                        "target": target,
                        "status": "blocked",
                        "blockers": [
                            {
                                "check": "article_dir",
                                "status": "fail",
                                "detail": f"article dir not found: {article_dir}",
                            }
                        ],
                    },
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 1
    generated_dir = article_dir / "generated"
    generated_dir.mkdir(parents=True, exist_ok=True)

    report_path = generated_dir / "quality-gates.json"
    diagnose_path = generated_dir / "diagnose-report.json"
    doctor_path = generated_dir / "article-doctor-report.json"
    seo_path = generated_dir / "seo-report.json"

    checks: list[dict] = []
    advisories: list[dict] = []
    artifacts: dict[str, object] = {
        "diagnose_report": str(diagnose_path),
        "article_doctor_report": str(doctor_path),
        "seo_report": str(seo_path),
    }

    article_path = article_dir / "article.md"
    metadata_path = article_dir / "draft-metadata.json"
    html_path = article_dir / "article-body.template.html"
    preview_path = article_dir / "preview.html"
    humanness_path = generated_dir / "humanness-report.json"
    image_prompts_path = generated_dir / "image-prompts.md"

    metadata: dict[str, object] = {}
    article_markdown = ""
    html = ""

    add_check(checks, "article_dir", "pass", f"article dir found: {article_dir}")

    for path, name in [
        (article_path, "article_md"),
        (metadata_path, "draft_metadata"),
        (html_path, "html_template"),
        (preview_path, "preview_html"),
        (humanness_path, "humanness_report"),
    ]:
        status = "pass" if path.exists() else "fail"
        add_check(checks, name, status, f"{name} {'found' if path.exists() else 'missing'}: {path}")

    add_advisory(
        advisories,
        "image_prompts",
        f"image prompts {'found' if image_prompts_path.exists() else 'not requested'}: {image_prompts_path}",
        level="ready" if image_prompts_path.exists() else "info",
    )

    if metadata_path.exists():
        try:
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        except Exception as exc:
            add_check(checks, "draft_metadata_json", "fail", f"draft-metadata.json invalid: {exc}")

    render_source = str(metadata.get("render_source") or "article.md") if metadata else "article.md"
    try:
        render_source_path = resolve_article_file(article_dir, render_source)
    except ValueError as exc:
        render_source_path = article_dir / "__invalid_render_source__"
        add_check(checks, "render_source", "fail", str(exc))
    else:
        add_check(
            checks,
            "render_source",
            "pass" if render_source_path.exists() else "fail",
            f"render source {'found' if render_source_path.exists() else 'missing'}: {render_source_path}",
        )

    if render_source_path.exists():
        try:
            article_markdown = render_source_path.read_text(encoding="utf-8")
        except Exception as exc:
            add_check(checks, "article_md_utf8", "fail", f"render source unreadable as UTF-8: {exc}")
    if html_path.exists():
        try:
            html = html_path.read_text(encoding="utf-8")
        except Exception as exc:
            add_check(checks, "html_template_utf8", "fail", f"article-body.template.html unreadable as UTF-8: {exc}")

    if metadata:
        contract_checks, contract_advisories = evaluate_content_contract(article_dir, metadata, target)
        checks.extend(contract_checks)
        advisories.extend(contract_advisories)

    title = str(metadata.get("title") or "").strip()
    digest = str(metadata.get("digest") or "").strip()

    if title:
        title_bytes = utf8_len(title)
        title_status = "pass" if 5 <= title_bytes <= 64 else "fail"
        add_check(checks, "metadata_title_length", title_status, f"title bytes={title_bytes} (need 5-64)")
    else:
        add_check(checks, "metadata_title_length", "fail", "title is empty")

    if digest:
        digest_bytes = utf8_len(digest)
        digest_status = "pass" if digest_bytes <= 120 else "fail"
        add_check(checks, "metadata_digest_length", digest_status, f"digest bytes={digest_bytes} (need <=120)")
    else:
        add_check(checks, "metadata_digest_length", "fail", "digest is empty")

    if article_markdown:
        char_count = len(strip := re.sub(r"\s+", "", article_markdown))
        status = "pass" if char_count >= 200 else "fail"
        add_check(checks, "article_char_count", status, f"正文字符数={char_count} (need >=200)")

        image_refs = re.findall(r"!\[[^\]]*\]\(([^)]+)\)", article_markdown)
        local_images = [normalize_image_src(item) for item in image_refs if not item.startswith(("http://", "https://"))]
        image_count_status = "pass" if len(local_images) <= 10 else "fail"
        add_check(checks, "image_count", image_count_status, f"正文图片数={len(local_images)} (need 0-10)", data=local_images)

        missing_images = []
        for ref in local_images:
            try:
                candidate = resolve_article_file(article_dir, ref)
            except ValueError:
                missing_images.append(f"{ref} (outside article directory)")
            else:
                if not candidate.exists():
                    missing_images.append(ref)
        if missing_images:
            add_check(checks, "image_assets", "fail", f"缺少正文图片文件: {', '.join(missing_images[:10])}")
        else:
            add_check(checks, "image_assets", "pass", "正文图片文件均存在")
    else:
        add_check(checks, "article_char_count", "fail", "article.md is empty or unreadable")

    if article_markdown and metadata:
        layout_result = evaluate_layout_diversity(article_dir, metadata, article_markdown)
        layout_status = "pass" if layout_result.get("status") == "pass" else "warn"
        warnings = layout_result.get("warnings", [])
        detail = "layout diversity ok" if not warnings else "; ".join(str(item) for item in warnings)
        if target == "publish":
            add_check(checks, "layout_diversity", layout_status, detail, data=layout_result)
        else:
            add_advisory(
                advisories,
                "layout_diversity",
                detail,
                level="ready" if layout_status == "pass" else "risk",
                data=layout_result,
            )
    else:
        add_check(checks, "layout_diversity", "fail", "missing article or metadata, cannot check layout diversity")

    cover_image = str(metadata.get("cover_image") or "assets/cover-wide.jpg").strip() or "assets/cover-wide.jpg"
    try:
        cover_path = resolve_article_file(article_dir, cover_image)
        cover_error = ""
    except ValueError as exc:
        cover_path = article_dir / "__invalid_cover_path__"
        cover_error = str(exc)
    cover_square_path = article_dir / "assets" / "cover-square.jpg"
    if target == "publish":
        add_check(
            checks,
            "cover_image",
            "pass" if not cover_error and cover_path.exists() else "fail",
            cover_error or f"cover image: {cover_path}",
        )
        add_check(
            checks,
            "cover_square_image",
            "pass" if cover_square_path.exists() else "fail",
            f"square cover image: {cover_square_path}",
        )
    else:
        add_advisory(
            advisories,
            "cover_image",
            cover_error or f"cover image {'found' if cover_path.exists() else 'not required for preview'}: {cover_path}",
            level="risk" if cover_error else ("ready" if cover_path.exists() else "info"),
        )
        add_advisory(
            advisories,
            "cover_square_image",
            f"square cover {'found' if cover_square_path.exists() else 'not required for preview'}: {cover_square_path}",
            level="ready" if cover_square_path.exists() else "info",
        )

    if html:
        status, detail, data = html_readability_check(html)
        add_check(checks, "theme_shell_readability", status, detail, data=data)
        if target == "publish":
            status, detail, data = publish_payload_safety_check(html)
            add_check(checks, "publish_payload_safety", status, detail, data=data)
    else:
        add_check(checks, "theme_shell_readability", "fail", "article-body.template.html is empty or unreadable")

    if humanness_path.exists():
        try:
            humanness = json.loads(humanness_path.read_text(encoding="utf-8"))
            failed_checks = humanness.get("summary", {}).get("failed_checks", []) or []
            artifacts["humanness_summary"] = humanness.get("summary")
            add_advisory(
                advisories,
                "humanness_summary",
                f"humanness composite={humanness.get('composite_score')} failed_checks={failed_checks}",
                level="risk" if failed_checks else "ready",
                data=humanness.get("summary"),
            )
        except Exception as exc:
            add_advisory(advisories, "humanness_summary", f"humanness-report.json invalid: {exc}", level="risk")

    diagnose_result, diagnose_error = run_json_command([sys.executable, str(REPO_ROOT / "scripts" / "diagnose.py"), "--json"])
    if diagnose_result is None:
        add_check(checks, "diagnose", "fail", f"diagnose.py failed: {diagnose_error}")
    else:
        diagnose_path.write_text(json.dumps(diagnose_result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        diagnose_summary = diagnose_result.get("summary", {})
        required_diagnostics = {"python_packages"}
        if target == "publish":
            required_diagnostics.update({"config_file", "wechat_credentials"})
        relevant_non_pass = [
            item
            for item in diagnose_result.get("checks", [])
            if item.get("name") in required_diagnostics and item.get("status") != "pass"
        ]
        add_check(
            checks,
            "diagnose",
            "fail" if relevant_non_pass else "pass",
            f"target={target} relevant_non_pass={relevant_non_pass}",
            data={"required": sorted(required_diagnostics), "summary": diagnose_summary},
        )
        optional_non_pass = [
            item
            for item in diagnose_result.get("checks", [])
            if item.get("name") not in required_diagnostics and item.get("status") != "pass"
        ]
        if optional_non_pass:
            add_advisory(
                advisories,
                "optional_diagnostics",
                f"optional non-pass checks={len(optional_non_pass)}",
                level="risk",
                data=optional_non_pass,
            )

    powershell = resolve_powershell()
    if powershell is None:
        doctor_result = None
        doctor_error = "pwsh/powershell executable not found"
    else:
        doctor_result, doctor_error = run_json_command([
            powershell,
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(WORKFLOW_ROOT / "scripts" / "project-doctor.ps1"),
            "-ArticleDir",
            str(article_dir),
        ])

    if doctor_result is None:
        add_check(checks, "article_doctor", "fail", f"project-doctor failed: {doctor_error}")
    else:
        doctor_path.write_text(json.dumps(doctor_result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        doctor_articles = doctor_result.get("articles", [])
        doctor_errors = sum(len(item.get("errors", [])) for item in doctor_articles)
        doctor_warnings = sum(len(item.get("warnings", [])) for item in doctor_articles)
        if doctor_errors > 0:
            status = "fail"
        elif doctor_warnings > 0:
            status = "warn"
        else:
            status = "pass"
        add_check(
            checks,
            "article_doctor",
            status,
            f"project-doctor errors={doctor_errors} warnings={doctor_warnings}",
            data={"errors": doctor_errors, "warnings": doctor_warnings},
        )

    if title:
        seo_result, seo_error = run_json_command([sys.executable, str(REPO_ROOT / "scripts" / "seo_keywords.py"), "--json", title])
        if seo_result is None:
            add_advisory(advisories, "seo_keywords", f"seo_keywords.py failed: {seo_error}", level="risk")
        else:
            seo_path.write_text(json.dumps(seo_result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            primary = seo_result[0] if seo_result else {}
            seo_score = primary.get("seo_score", 0)
            add_advisory(
                advisories,
                "seo_keywords",
                f"title seo_score={seo_score}",
                level="ready" if seo_score >= 1 else "risk",
                data=primary,
            )
    else:
        add_check(checks, "seo_keywords", "fail", "title missing, cannot run seo_keywords.py")

    summary = summarize(checks)
    blockers = [
        {
            "check": item["name"],
            "status": item["status"],
            "detail": item["detail"],
        }
        for item in checks
        if item["status"] != "pass"
    ]
    report = {
        "article_dir": str(article_dir),
        "target": target,
        "strict": True,
        "requested_strict": bool(args.strict),
        "quality_policy": "target_scoped_zero_tolerance: checks pass only when fail=0, warn=0, skip=0",
        "checks": checks,
        "advisories": advisories,
        "summary": summary,
        "readiness": {
            "target": target,
            "status": "ready" if not blockers else "blocked",
            "blockers": blockers,
        },
        "artifacts": artifacts,
    }
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))

    if blockers:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
