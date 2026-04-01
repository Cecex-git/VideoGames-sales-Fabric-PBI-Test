from __future__ import annotations

import argparse
import os
import tempfile
from pathlib import Path

from azure.identity import AzureCliCredential, InteractiveBrowserCredential
from fabric_cicd import FabricWorkspace, publish_all_items


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Deploy the PBIP project to a Fabric workspace.")
    parser.add_argument("--workspace-name", required=True, help="Target Fabric workspace name.")
    parser.add_argument("--environment", default="dev", help="Deployment environment name.")
    parser.add_argument(
        "--repository-directory",
        default=str(Path(__file__).resolve().parent),
        help="PBIP repository root.",
    )
    parser.add_argument(
        "--spn-auth",
        action="store_true",
        help="Use AzureCliCredential for service-principal based CI/CD runs.",
    )
    parser.add_argument("--source-workspace-id", help="Source Fabric workspace ID for lakehouse-backed model binding.")
    parser.add_argument("--source-lakehouse-id", help="Source Fabric lakehouse ID for lakehouse-backed model binding.")
    parser.add_argument("--source-table-name", help="Source Fabric lakehouse table name for the semantic model.")
    parser.add_argument(
        "--semantic-model-connection-id",
        help="Fabric connection ID used to bind the deployed semantic model for refresh.",
    )
    return parser


def get_required_source_settings(args: argparse.Namespace) -> dict[str, str]:
    source_settings = {
        "workspace_id": args.source_workspace_id or os.getenv("FABRIC_SOURCE_WORKSPACE_ID"),
        "lakehouse_id": args.source_lakehouse_id or os.getenv("FABRIC_SOURCE_LAKEHOUSE_ID"),
        "table_name": args.source_table_name or os.getenv("FABRIC_SOURCE_TABLE_NAME"),
        "connection_id": args.semantic_model_connection_id or os.getenv("FABRIC_SEMANTIC_MODEL_CONNECTION_ID"),
    }
    missing = [name for name, value in source_settings.items() if not value]
    if missing:
        raise ValueError(
            "Missing required source settings: "
            + ", ".join(missing)
            + ". Provide them with CLI arguments or environment variables."
        )
    return source_settings


def build_runtime_parameter_file(repository_directory: str, source_settings: dict[str, str]) -> str:
    template_path = Path(repository_directory) / "parameter.yml"
    template = template_path.read_text(encoding="utf-8")
    rendered = (
        template.replace("__FABRIC_SOURCE_WORKSPACE_ID__", source_settings["workspace_id"])
        .replace("__FABRIC_SOURCE_LAKEHOUSE_ID__", source_settings["lakehouse_id"])
        .replace("__FABRIC_SOURCE_TABLE_NAME__", source_settings["table_name"])
        .replace("__FABRIC_SEMANTIC_MODEL_CONNECTION_ID__", source_settings["connection_id"])
    )

    temp_file = tempfile.NamedTemporaryFile(mode="w", suffix=".yml", delete=False, encoding="utf-8")
    try:
        temp_file.write(rendered)
        return temp_file.name
    finally:
        temp_file.close()


def main() -> None:
    args = build_parser().parse_args()
    credential = AzureCliCredential() if args.spn_auth else InteractiveBrowserCredential()
    source_settings = get_required_source_settings(args)
    parameter_file_path = build_runtime_parameter_file(args.repository_directory, source_settings)

    try:
        target_workspace = FabricWorkspace(
            workspace_name=args.workspace_name,
            environment=args.environment,
            repository_directory=args.repository_directory,
            parameter_file_path=parameter_file_path,
            item_type_in_scope=["SemanticModel", "Report"],
            token_credential=credential,
        )

        publish_all_items(target_workspace)
    finally:
        Path(parameter_file_path).unlink(missing_ok=True)


if __name__ == "__main__":
    main()

