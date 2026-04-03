from __future__ import annotations

import re
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
MODEL_DIR = REPO_ROOT / "VideoGameSales.SemanticModel"
DEFINITION_DIR = MODEL_DIR / "definition"
TABLES_DIR = DEFINITION_DIR / "tables"


def fail(errors: list[str]) -> None:
    for error in errors:
        print(f"ERROR: {error}")
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

    for line in load_text(path).splitlines():
        table_name = table_name or extract_name(line, "table")

        column_name = extract_name(line, "column")
        if column_name:
            columns.add(column_name)

        measure_name = extract_name(line, "measure")
        if measure_name:
            measures.add(measure_name)

        partition_name = extract_name(line, "partition")
        if partition_name:
            partitions.add(partition_name)

    if not table_name:
        raise ValueError(f"Unable to find table declaration in {path}")

    return {
        "table_name": table_name,
        "columns": columns,
        "measures": measures,
        "partitions": partitions,
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
    current_relationship: str | None = None

    for line in load_text(relationships_path).splitlines():
        relationship_name = extract_name(line, "relationship")
        if relationship_name:
            current_relationship = relationship_name
            continue

        stripped = line.strip()
        for property_name in ("fromColumn", "toColumn"):
            prefix = f"{property_name}:"
            if not stripped.startswith(prefix):
                continue

            reference = parse_column_reference(stripped[len(prefix) :].strip())
            if reference is None:
                errors.append(
                    f"{relationships_path.name}: {current_relationship or '<unknown>'} has an invalid {property_name} reference."
                )
                continue

            table_name, column_name = reference
            table = tables.get(table_name)
            if not table:
                errors.append(
                    f"{relationships_path.name}: {current_relationship or '<unknown>'} references missing table '{table_name}'."
                )
                continue

            if column_name not in table["columns"]:
                errors.append(
                    f"{relationships_path.name}: {current_relationship or '<unknown>'} references missing column '{table_name}.{column_name}'."
                )

    return errors


def main() -> None:
    errors: list[str] = []

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
        fail(errors)

    table_files = sorted(TABLES_DIR.glob("*.tmdl"))
    if not table_files:
        fail(["No TMDL table files were found in VideoGameSales.SemanticModel\\definition\\tables."])

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

        if not table["columns"]:
            errors.append(f"{table_file.name} does not declare any columns.")
        if not table["partitions"]:
            errors.append(f"{table_file.name} does not declare any partitions.")

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
            "Total Sales",
            "NA Sales",
            "JP Sales",
            "PAL Sales",
            "Other Sales",
            "Average Critic Score",
        }:
            if measure_name not in fact_measures:
                errors.append(f"FactGames is missing expected measure '{measure_name}'.")

    if errors:
        fail(errors)

    print(
        f"Semantic model validation passed: {len(tables)} tables, "
        f"{sum(len(table['columns']) for table in tables.values())} columns, "
        f"{sum(len(table['measures']) for table in tables.values())} measures."
    )


if __name__ == "__main__":
    main()
