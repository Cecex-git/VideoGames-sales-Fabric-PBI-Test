from __future__ import annotations

import json
import re
import uuid
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def fail(errors: list[str]) -> None:
    for error in errors:
        print(f"ERROR: {error}")
    raise SystemExit(1)


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def load_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def is_guid(value: str) -> bool:
    try:
        uuid.UUID(value)
        return True
    except ValueError:
        return False


def main() -> None:
    errors: list[str] = []

    pbip_path = REPO_ROOT / "VideoGameSales.pbip"
    report_platform_path = REPO_ROOT / "VideoGameSales.Report" / ".platform"
    semantic_platform_path = REPO_ROOT / "VideoGameSales.SemanticModel" / ".platform"
    definition_pbir_path = REPO_ROOT / "VideoGameSales.Report" / "definition.pbir"
    parameter_path = REPO_ROOT / "parameter.yml"
    deploy_path = REPO_ROOT / "deploy.py"
    expressions_path = REPO_ROOT / "VideoGameSales.SemanticModel" / "definition" / "expressions.tmdl"
    gitignore_path = REPO_ROOT / ".gitignore"
    report_dir = REPO_ROOT / "VideoGameSales.Report"
    semantic_model_dir = REPO_ROOT / "VideoGameSales.SemanticModel"

    required_paths = [
        pbip_path,
        report_platform_path,
        semantic_platform_path,
        definition_pbir_path,
        parameter_path,
        deploy_path,
        expressions_path,
        gitignore_path,
        report_dir,
        semantic_model_dir,
    ]
    for path in required_paths:
        if not path.exists():
            errors.append(f"Required project binding path is missing: {path.relative_to(REPO_ROOT)}")

    if errors:
        fail(errors)

    pbip_json = load_json(pbip_path)
    definition_pbir_json = load_json(definition_pbir_path)
    report_platform_json = load_json(report_platform_path)
    semantic_platform_json = load_json(semantic_platform_path)
    parameter_text = load_text(parameter_path)
    deploy_text = load_text(deploy_path)
    expressions_text = load_text(expressions_path)
    gitignore_text = load_text(gitignore_path)

    if pbip_json.get("$schema") != "https://developer.microsoft.com/json-schemas/fabric/pbip/pbipProperties/1.0.0/schema.json":
        errors.append("VideoGameSales.pbip must use the pbipProperties/1.0.0 schema.")

    artifacts = pbip_json.get("artifacts", [])
    if len(artifacts) != 1 or artifacts[0].get("report", {}).get("path") != "VideoGameSales.Report":
        errors.append("VideoGameSales.pbip must reference the VideoGameSales.Report artifact by path.")
    elif not (REPO_ROOT / artifacts[0]["report"]["path"]).is_dir():
        errors.append("VideoGameSales.pbip references a report path that does not exist in the repository.")

    if definition_pbir_json.get("$schema") != "https://developer.microsoft.com/json-schemas/fabric/item/report/definitionProperties/2.0.0/schema.json":
        errors.append("VideoGameSales.Report\\definition.pbir must use the definitionProperties/2.0.0 schema.")
    if definition_pbir_json.get("version") != "4.0":
        errors.append("VideoGameSales.Report\\definition.pbir must declare version 4.0.")

    dataset_reference = definition_pbir_json.get("datasetReference", {})
    if dataset_reference.get("byPath", {}).get("path") != "../VideoGameSales.SemanticModel":
        errors.append("VideoGameSales.Report\\definition.pbir must reference ../VideoGameSales.SemanticModel by path.")
    else:
        target_model_path = (report_dir / dataset_reference["byPath"]["path"]).resolve()
        if target_model_path != semantic_model_dir.resolve():
            errors.append("VideoGameSales.Report\\definition.pbir byPath target must resolve to VideoGameSales.SemanticModel.")
        if not target_model_path.is_dir():
            errors.append("VideoGameSales.Report\\definition.pbir references a semantic model path that does not exist.")

    for platform_name, platform_json, expected_type in (
        ("VideoGameSales.Report\\.platform", report_platform_json, "Report"),
        ("VideoGameSales.SemanticModel\\.platform", semantic_platform_json, "SemanticModel"),
    ):
        if platform_json.get("$schema") != "https://developer.microsoft.com/json-schemas/fabric/gitIntegration/platformProperties/2.0.0/schema.json":
            errors.append(f"{platform_name} must use the gitIntegration platformProperties/2.0.0 schema.")
        if platform_json.get("config", {}).get("version") != "2.0":
            errors.append(f"{platform_name} must set config.version to 2.0.")
        if platform_json.get("metadata", {}).get("displayName") != "VideoGameSales":
            errors.append(f"{platform_name} must keep metadata.displayName aligned to VideoGameSales.")
        if platform_json.get("metadata", {}).get("type") != expected_type:
            errors.append(f"{platform_name} must declare metadata.type '{expected_type}'.")
        logical_id = platform_json.get("config", {}).get("logicalId", "")
        if not is_guid(logical_id):
            errors.append(f"{platform_name} must contain a valid GUID config.logicalId.")

    if report_platform_json.get("config", {}).get("logicalId") == semantic_platform_json.get("config", {}).get("logicalId"):
        errors.append("Report and semantic model .platform files must not reuse the same logicalId.")

    expected_parameter_tokens = {
        "__FABRIC_SOURCE_WORKSPACE_ID__",
        "__FABRIC_SOURCE_LAKEHOUSE_ID__",
        "__FABRIC_SOURCE_TABLE_NAME__",
        "__FABRIC_SEMANTIC_MODEL_CONNECTION_ID__",
    }
    for token in expected_parameter_tokens:
        if token not in parameter_text:
            errors.append(f"parameter.yml is missing placeholder token {token}.")

    for literal in {
        'find_value: "00000000-0000-0000-0000-000000000000"',
        'find_value: "11111111-1111-1111-1111-111111111111"',
        'find_value: "VideoGameSalesRaw"',
        'semantic_model_name: "VideoGameSales"',
    }:
        if literal not in parameter_text:
            errors.append(f"parameter.yml is missing expected entry: {literal}")

    for expression_literal in {
        'expression FabricWorkspaceId = "00000000-0000-0000-0000-000000000000"',
        'expression FabricLakehouseId = "11111111-1111-1111-1111-111111111111"',
        'expression VideoGameSalesLakehouseTable = "VideoGameSalesRaw"',
    }:
        if expression_literal not in expressions_text:
            errors.append(f"definition\\expressions.tmdl is missing expected parameter default: {expression_literal}")

    for required_text in {
        "FABRIC_SOURCE_WORKSPACE_ID",
        "FABRIC_SOURCE_LAKEHOUSE_ID",
        "FABRIC_SOURCE_TABLE_NAME",
        "FABRIC_SEMANTIC_MODEL_CONNECTION_ID",
        "item_type_in_scope=[\"SemanticModel\", \"Report\"]",
        "build_runtime_parameter_file",
        "AzureCliCredential",
        "InteractiveBrowserCredential",
    }:
        if required_text not in deploy_text:
            errors.append(f"deploy.py is missing expected deployment contract text: {required_text}")

    for path_name, text in {
        "VideoGameSales.pbip": load_text(pbip_path),
        "VideoGameSales.Report\\definition.pbir": load_text(definition_pbir_path),
        "parameter.yml": parameter_text,
    }.items():
        if re.search(r"\b[A-Za-z]:\\", text):
            errors.append(f"{path_name} contains an absolute Windows path, which should not be committed.")

    for required_ignore in {"**/.pbi/localSettings.json", "**/.pbi/cache.abf"}:
        if required_ignore not in gitignore_text:
            errors.append(f".gitignore must include '{required_ignore}' to avoid committing local Power BI artifacts.")

    if errors:
        fail(errors)

    print("Project bindings validation passed: PBIP, .platform, definition.pbir, parameter.yml, and deploy.py are aligned.")


if __name__ == "__main__":
    main()
