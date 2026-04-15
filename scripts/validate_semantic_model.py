from __future__ import annotations

import re
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
MODEL_DIR = REPO_ROOT / "VideoGameSales.SemanticModel"
DEFINITION_DIR = MODEL_DIR / "definition"
TABLES_DIR = DEFINITION_DIR / "tables"


def print_findings(errors: list[str], warnings: list[str]) -> None:
    for error in errors:
        print(f"ERROR: {error}")
    for warning in warnings:
        print(f"WARNING: {warning}")


def fail(errors: list[str], warnings: list[str]) -> None:
    print_findings(errors, warnings)
    raise SystemExit(1)


def extract_name(line: str, keyword: str) -> str | None:
    stripped = line.strip()
    prefix = f"{keyword} "
    if not stripped.startswith(prefix):
        return None

    remainder = stripped[len(prefix) :].strip()
    if remainder.startswith("'"):
        end_quote = remainder.find("'", 1)
        if end_quote == -1:
            return None
        return remainder[1:end_quote]

    match = re.match(r"([^\s=]+)", remainder)
    return match.group(1) if match else None


def load_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def parse_table_file(path: Path) -> dict[str, object]:
    table_name: str | None = None
    columns: set[str] = set()
    measures: set[str] = set()
    partitions: set[str] = set()
    visible_columns_without_descriptions: list[str] = []
    visible_measures_without_descriptions: list[str] = []
    columns_without_data_types: list[str] = []
    current_object: dict[str, object] | None = None
    lines = load_text(path).splitlines()

    def finalize_current_object() -> None:
        nonlocal current_object
        if current_object is None:
            return

        kind = str(current_object["kind"])
        name = str(current_object["name"])
        has_description = bool(current_object["has_description"])
        is_hidden = bool(current_object.get("is_hidden", False))
        has_data_type = bool(current_object.get("has_data_type", True))

        if kind == "column":
            if not has_data_type:
                columns_without_data_types.append(name)
            if not is_hidden and not has_description:
                visible_columns_without_descriptions.append(name)
        elif kind == "measure" and not has_description:
            visible_measures_without_descriptions.append(name)

        current_object = None

    for index, line in enumerate(lines):
        if line.startswith(" "):
            raise ValueError(f"{path.name}:{index + 1} uses leading spaces for indentation; use tabs in TMDL files.")

        table_name = table_name or extract_name(line, "table")

        column_name = extract_name(line, "column")
        if column_name:
            finalize_current_object()
            columns.add(column_name)
            current_object = {
                "kind": "column",
                "name": column_name,
                "has_description": index > 0 and lines[index - 1].strip().startswith("///"),
                "is_hidden": False,
                "has_data_type": False,
            }
            continue

        measure_name = extract_name(line, "measure")
        if measure_name:
            finalize_current_object()
            measures.add(measure_name)
            current_object = {
                "kind": "measure",
                "name": measure_name,
                "has_description": index > 0 and lines[index - 1].strip().startswith("///"),
            }
            continue

        partition_name = extract_name(line, "partition")
        if partition_name:
            finalize_current_object()
            partitions.add(partition_name)
            current_object = {
                "kind": "partition",
                "name": partition_name,
                "has_description": index > 0 and lines[index - 1].strip().startswith("///"),
            }
            continue

        if current_object is None:
            continue

        stripped = line.strip()
        if str(current_object["kind"]) == "column":
            if stripped.startswith("dataType:"):
                current_object["has_data_type"] = True
            elif stripped == "isHidden" or stripped == "isHidden: true":
                current_object["is_hidden"] = True

    finalize_current_object()

    if not table_name:
        raise ValueError(f"Unable to find table declaration in {path}")

    return {
        "table_name": table_name,
        "columns": columns,
        "measures": measures,
        "partitions": partitions,
        "visible_columns_without_descriptions": visible_columns_without_descriptions,
        "visible_measures_without_descriptions": visible_measures_without_descriptions,
        "columns_without_data_types": columns_without_data_types,
    }


def parse_model_references(path: Path) -> tuple[str | None, list[str]]:
    model_name: str | None = None
    references: list[str] = []

    for line in load_text(path).splitlines():
        model_name = model_name or extract_name(line, "model")
        ref_name = extract_name(line, "ref table")
        if ref_name:
            references.append(ref_name)

    return model_name, references


def parse_column_reference(value: str) -> tuple[str, str] | None:
    parts = value.strip().split(".", 1)
    if len(parts) != 2:
        return None
    return parts[0], parts[1]


def validate_relationships(relationships_path: Path, tables: dict[str, dict[str, object]]) -> list[str]:
    errors: list[str] = []
    relationships: list[dict[str, str | None]] = []
    current_relationship: dict[str, str | None] | None = None

    for line in load_text(relationships_path).splitlines():
        relationship_name = extract_name(line, "relationship")
        if relationship_name:
            if current_relationship is not None:
                relationships.append(current_relationship)
            current_relationship = {
                "name": relationship_name,
                "fromColumn": None,
                "toColumn": None,
                "joinOnDateBehavior": None,
            }
            continue

        if current_relationship is None:
            continue

        stripped = line.strip()
        if stripped.startswith("joinOnDateBehavior:"):
            current_relationship["joinOnDateBehavior"] = stripped.split(":", 1)[1].strip()
            continue

        for property_name in ("fromColumn", "toColumn"):
            prefix = f"{property_name}:"
            if not stripped.startswith(prefix):
                continue

            reference = parse_column_reference(stripped[len(prefix) :].strip())
            if reference is None:
                errors.append(
                    f"{relationships_path.name}: {current_relationship['name'] or '<unknown>'} has an invalid {property_name} reference."
                )
                continue

            table_name, column_name = reference
            current_relationship[property_name] = f"{table_name}.{column_name}"
            table = tables.get(table_name)
            if not table:
                errors.append(
                    f"{relationships_path.name}: {current_relationship['name'] or '<unknown>'} references missing table '{table_name}'."
                )
                continue

            if column_name not in table["columns"]:
                errors.append(
                    f"{relationships_path.name}: {current_relationship['name'] or '<unknown>'} references missing column '{table_name}.{column_name}'."
                )

    if current_relationship is not None:
        relationships.append(current_relationship)

    related_tables: set[str] = set()
    for relationship in relationships:
        name = relationship["name"] or "<unknown>"
        from_reference = relationship["fromColumn"]
        to_reference = relationship["toColumn"]
        if not from_reference or not to_reference:
            continue

        from_table_name, from_column_name = parse_column_reference(from_reference) or ("", "")
        to_table_name, to_column_name = parse_column_reference(to_reference) or ("", "")
        related_tables.update({from_table_name, to_table_name})

        if relationship["joinOnDateBehavior"]:
            continue

        from_table = tables.get(from_table_name)
        to_table = tables.get(to_table_name)
        if not from_table or not to_table:
            continue

        if from_column_name.endswith("Key") or to_column_name.endswith("Key"):
            continue

        from_key_candidate = f"{from_column_name}Key"
        to_key_candidate = f"{to_column_name}Key"
        if from_key_candidate in from_table["columns"] and to_key_candidate in to_table["columns"]:
            errors.append(
                f"{relationships_path.name}: {name} joins on '{from_column_name}'/'{to_column_name}' instead of normalized key columns."
            )

    if len(tables) > 1:
        orphaned_tables = sorted(table_name for table_name in tables if table_name not in related_tables)
        for table_name in orphaned_tables:
            errors.append(f"{relationships_path.name}: table '{table_name}' is not referenced by any relationship.")

    return errors


def main() -> None:
    errors: list[str] = []
    warnings: list[str] = []

    required_paths = [
        MODEL_DIR / ".platform",
        DEFINITION_DIR / "model.tmdl",
        DEFINITION_DIR / "expressions.tmdl",
        DEFINITION_DIR / "relationships.tmdl",
        TABLES_DIR,
    ]
    for path in required_paths:
        if not path.exists():
            errors.append(f"Required semantic model path is missing: {path.relative_to(REPO_ROOT)}")

    if errors:
        fail(errors, warnings)

    table_files = sorted(TABLES_DIR.glob("*.tmdl"))
    if not table_files:
        fail(["No TMDL table files were found in VideoGameSales.SemanticModel\\definition\\tables."], warnings)

    model_name, model_references = parse_model_references(DEFINITION_DIR / "model.tmdl")
    if model_name != "VideoGameSales":
        errors.append("definition\\model.tmdl must declare model VideoGameSales.")

    tables: dict[str, dict[str, object]] = {}
    for table_file in table_files:
        table = parse_table_file(table_file)
        table_name = str(table["table_name"])
        if table_name in tables:
            errors.append(f"Duplicate table declaration found for '{table_name}'.")
            continue
        tables[table_name] = table

        if table_file.stem != table_name:
            errors.append(f"{table_file.name} must match its table name declaration '{table_name}'.")
        if not table["columns"]:
            errors.append(f"{table_file.name} does not declare any columns.")
        if not table["partitions"]:
            errors.append(f"{table_file.name} does not declare any partitions.")
        if table_name not in table["partitions"]:
            errors.append(f"{table_file.name} must declare a partition named '{table_name}'.")
        for column_name in table["columns_without_data_types"]:
            errors.append(f"{table_file.name} column '{column_name}' is missing a dataType.")
        for measure_name in table["visible_measures_without_descriptions"]:
            warnings.append(f"{table_file.name} visible measure '{measure_name}' is missing a /// description.")
        for column_name in table["visible_columns_without_descriptions"]:
            warnings.append(f"{table_file.name} visible column '{column_name}' is missing a /// description.")

    table_names = set(tables)
    reference_names = set(model_references)

    missing_table_files = sorted(reference_names - table_names)
    if missing_table_files:
        errors.append(
            "definition\\model.tmdl references tables without matching files: " + ", ".join(missing_table_files)
        )

    unreferenced_table_files = sorted(table_names - reference_names)
    if unreferenced_table_files:
        errors.append(
            "Table files exist without matching ref table entries in definition\\model.tmdl: "
            + ", ".join(unreferenced_table_files)
        )

    expressions_text = load_text(DEFINITION_DIR / "expressions.tmdl")
    required_expressions = {
        "FabricWorkspaceId",
        "FabricLakehouseId",
        "VideoGameSalesLakehouseTable",
        "NormalizeCategoryLabel",
        "NormalizeCategoryKey",
        "VideoGameSalesTypedSource",
    }
    for expression_name in required_expressions:
        if f"expression {expression_name}" not in expressions_text:
            errors.append(f"definition\\expressions.tmdl is missing expression '{expression_name}'.")

    if "Table.AddColumns(" in expressions_text or any(
        "Table.AddColumns(" in load_text(table_file) for table_file in table_files
    ):
        errors.append("Invalid M pattern 'Table.AddColumns(' detected; use chained Table.AddColumn calls.")

    errors.extend(validate_relationships(DEFINITION_DIR / "relationships.tmdl", tables))

    if "FactGames" in tables:
        fact_measures = tables["FactGames"]["measures"]
        for measure_name in {
            "Titles",
            "Total Sales (M copies)",
            "NA Sales (M copies)",
            "JP Sales (M copies)",
            "PAL Sales (M copies)",
            "Other Sales (M copies)",
            "Average Sales per Title (M copies)",
            "Average Critic Score",
        }:
            if measure_name not in fact_measures:
                errors.append(f"FactGames is missing expected measure '{measure_name}'.")

    if errors:
        fail(errors, warnings)

    print_findings(errors, warnings)

    print(
        f"Semantic model validation passed: {len(tables)} tables, "
        f"{sum(len(table['columns']) for table in tables.values())} columns, "
        f"{sum(len(table['measures']) for table in tables.values())} measures, "
        f"{len(warnings)} warnings."
    )


if __name__ == "__main__":
    main()
