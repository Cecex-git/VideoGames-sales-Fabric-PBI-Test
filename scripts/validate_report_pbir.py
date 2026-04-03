from __future__ import annotations

import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
REPORT_DIR = REPO_ROOT / "VideoGameSales.Report"
DEFINITION_DIR = REPORT_DIR / "definition"
PAGES_DIR = DEFINITION_DIR / "pages"
BASE_THEME_PATH = REPORT_DIR / "StaticResources" / "SharedResources" / "BaseThemes" / "CY26SU02.json"


def fail(errors: list[str]) -> None:
    for error in errors:
        print(f"ERROR: {error}")
    raise SystemExit(1)


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    errors: list[str] = []

    required_paths = [
        REPORT_DIR / ".platform",
        REPORT_DIR / "definition.pbir",
        DEFINITION_DIR / "report.json",
        DEFINITION_DIR / "version.json",
        PAGES_DIR / "pages.json",
        BASE_THEME_PATH,
    ]
    for path in required_paths:
        if not path.exists():
            errors.append(f"Required report path is missing: {path.relative_to(REPO_ROOT)}")

    if errors:
        fail(errors)

    report_json = load_json(DEFINITION_DIR / "report.json")
    version_json = load_json(DEFINITION_DIR / "version.json")
    pages_json = load_json(PAGES_DIR / "pages.json")
    load_json(BASE_THEME_PATH)

    if report_json.get("$schema") != "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/report/3.2.0/schema.json":
        errors.append("definition\\report.json must use the report/3.2.0 schema.")

    base_theme = report_json.get("themeCollection", {}).get("baseTheme", {})
    if base_theme.get("name") != "CY26SU02" or base_theme.get("type") != "SharedResources":
        errors.append("definition\\report.json must reference the SharedResources CY26SU02 base theme.")

    resource_packages = report_json.get("resourcePackages", [])
    shared_resources_package = next((item for item in resource_packages if item.get("name") == "SharedResources"), None)
    if not shared_resources_package:
        errors.append("definition\\report.json is missing the SharedResources resource package.")
    else:
        theme_item = next(
            (item for item in shared_resources_package.get("items", []) if item.get("name") == "CY26SU02"),
            None,
        )
        if theme_item != {"name": "CY26SU02", "path": "BaseThemes/CY26SU02.json", "type": "BaseTheme"}:
            errors.append("definition\\report.json must include the CY26SU02 BaseTheme resource package item.")

    if "settings" not in report_json or not isinstance(report_json["settings"], dict) or not report_json["settings"]:
        errors.append("definition\\report.json must include non-empty report settings.")

    if "objects" not in report_json or "section" not in report_json["objects"]:
        errors.append("definition\\report.json must include report objects.section metadata.")

    if version_json.get("version") != "2.0.0":
        errors.append("definition\\version.json must declare version 2.0.0.")

    if pages_json.get("$schema") != "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/pagesMetadata/1.0.0/schema.json":
        errors.append("definition\\pages\\pages.json must use the pagesMetadata/1.0.0 schema.")

    page_order = pages_json.get("pageOrder", [])
    active_page_name = pages_json.get("activePageName")
    if not page_order:
        errors.append("definition\\pages\\pages.json must define a non-empty pageOrder.")
    if len(set(page_order)) != len(page_order):
        errors.append("definition\\pages\\pages.json contains duplicate page names in pageOrder.")
    if active_page_name not in page_order:
        errors.append("definition\\pages\\pages.json must set activePageName to one of the ordered pages.")

    actual_page_dirs = sorted(path.name for path in PAGES_DIR.iterdir() if path.is_dir())
    if sorted(page_order) != actual_page_dirs:
        errors.append(
            "Page folders must match definition\\pages\\pages.json pageOrder. "
            f"Expected {sorted(page_order)}, found {actual_page_dirs}."
        )

    total_visuals = 0
    for page_name in page_order:
        page_dir = PAGES_DIR / page_name
        page_json_path = page_dir / "page.json"
        visuals_dir = page_dir / "visuals"

        if not page_json_path.exists():
            errors.append(f"Page '{page_name}' is missing page.json.")
            continue
        if not visuals_dir.exists():
            errors.append(f"Page '{page_name}' is missing its visuals folder.")
            continue

        page_json = load_json(page_json_path)
        if page_json.get("$schema") != "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/page/2.1.0/schema.json":
            errors.append(f"Page '{page_name}' must use the page/2.1.0 schema.")
        if page_json.get("name") != page_name:
            errors.append(f"Page '{page_name}' must keep page.json name aligned with the folder name.")

        visual_dirs = sorted(path for path in visuals_dir.iterdir() if path.is_dir())
        if len(visual_dirs) > 7:
            errors.append(f"Page '{page_name}' has {len(visual_dirs)} visuals; the limit is 7.")

        for visual_dir in visual_dirs:
            visual_json_path = visual_dir / "visual.json"
            if not visual_json_path.exists():
                errors.append(f"Visual folder '{visual_dir.relative_to(REPO_ROOT)}' is missing visual.json.")
                continue

            visual_json = load_json(visual_json_path)
            if visual_json.get("$schema") != "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/visualContainer/2.6.0/schema.json":
                errors.append(f"Visual '{visual_dir.name}' must use the visualContainer/2.6.0 schema.")
            if visual_json.get("name") != visual_dir.name:
                errors.append(f"Visual '{visual_dir.name}' must keep visual.json name aligned with the folder name.")

            position = visual_json.get("position", {})
            for field_name in ("x", "y", "z", "height", "width", "tabOrder"):
                if field_name not in position:
                    errors.append(f"Visual '{visual_dir.name}' is missing position.{field_name}.")

            visual_definition = visual_json.get("visual", {})
            if not visual_definition.get("visualType"):
                errors.append(f"Visual '{visual_dir.name}' is missing visual.visualType.")

        total_visuals += len(visual_dirs)

    if errors:
        fail(errors)

    print(
        f"Report PBIR validation passed: {len(page_order)} pages, {total_visuals} visuals, base theme wired correctly."
    )


if __name__ == "__main__":
    main()
