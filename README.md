# Video Game Sales PBIP

This repository contains a Power BI Project (`.pbip`) scaffold for the video game sales dataset, ready for Git versioning and Microsoft Fabric deployment.

## What is included

- `VideoGameSales.pbip` as the project entry point
- `VideoGameSales.SemanticModel\definition\` with TMDL-exported semantic model files
- `VideoGameSales.Report\definition\` with a blank PBIR report shell
- `deploy.py` for PBIP deployment with `fabric-cicd`
- `.github\workflows\deploy-dev.yml` for GitHub-to-Fabric deployment
- `scripts\fabric_preflight.ps1` for local Fabric CLI checks

## Current model scaffold

The semantic model includes:

- `FactGames` imported from a Fabric Lakehouse table
- `DimConsole`
- `DimGenre`
- `DimPublisher`
- `DimDeveloper`
- `DimDate`

Measures currently included:

- `Titles`
- `Total Sales`
- `NA Sales`
- `JP Sales`
- `PAL Sales`
- `Other Sales`
- `Average Critic Score`
- `Average Sales per Title`
- `Titles with Critic Score`

## Local setup

1. Install Python dependencies:

   ```powershell
   pip install -r requirements.txt
   ```

2. Verify Fabric CLI access if needed:

   ```powershell
   .\scripts\fabric_preflight.ps1 -WorkspaceName "<Your Fabric Workspace>"
   ```

## Power BI Desktop authoring

Enable these preview features in Power BI Desktop before opening the project:

- `Power BI Project (.pbip) save option`
- `Store semantic model using TMDL format`
- `Store reports using enhanced metadata format (PBIR)`

Then open `VideoGameSales.pbip`.

The report now uses a **working PBIR shell** that opens in both Power BI Desktop and Fabric. You can still finish the visual layout in Power BI Desktop, but this repository already contains the report metadata shape needed for PBIR authoring outside Desktop.

## Creating the next report correctly

Do **not** start a new report from a hand-written minimal PBIR scaffold. We found that a report can deploy successfully while still failing to render in Desktop/Fabric if the report shell is too minimal.

For the next report, use the current `VideoGameSales.Report\` folder as the template and replace only the report-specific content:

1. Copy `VideoGameSales.Report\` to the new report folder name.
2. Update `.platform` metadata (`displayName`, description, logical ID as needed).
3. Update `definition.pbir` so `datasetReference.byPath.path` points to the target semantic model.
4. Keep the modern PBIR shell files and folders in place:
   - `definition\report.json`
   - `definition\version.json`
   - `definition\pages\`
   - `StaticResources\SharedResources\BaseThemes\CY26SU02.json`
5. Replace page names, page order, and visuals inside `definition\pages\`.

### Minimum report shell requirements

These files turned out to be important for a report to render correctly:

- `.platform` with the `fabric/gitIntegration/platformProperties/2.0.0` schema and `config.version: "2.0"`
- `definition.pbir` with a valid semantic model reference
- `definition\version.json` with `version: "2.0.0"`
- `definition\report.json` using the newer PBIR report schema (`report/3.2.0`) and including:
  - `themeCollection.baseTheme`
  - `resourcePackages`
  - report `objects`
  - report `settings`
- `StaticResources\SharedResources\BaseThemes\CY26SU02.json`
- `definition\pages\pages.json`
- one folder per page with a modern `page.json` (currently using `page/2.1.0`)
- one `visuals\<visualName>\visual.json` per visual

### What failed before

The original hand-authored report shell was too minimal. It deployed, but Desktop/Fabric failed during rendering with errors equivalent to missing page visual metadata (for example `visualContainers` access failures).

The practical rule for this repository is:

- **semantic model files can be scaffolded directly**
- **report files should start from this repository's existing working PBIR shell, not from a minimal blank JSON draft**

## Deployment

### Local deployment

Use interactive auth for a manual deployment:

```powershell
python .\deploy.py --workspace-name "<Your Fabric Workspace>" --environment dev
```

### GitHub Actions deployment

The workflow in `.github\workflows\deploy-dev.yml` deploys on pushes to the `main` branch after PR merges, and can also be run manually with `workflow_dispatch`.

The workflow in `.github\workflows\deploy-prod.yml` is a **manual promotion** workflow. It copies the `VideoGameSales` semantic model and report from the Fabric DEV workspace into the Fabric PROD workspace, so PROD promotion stays explicit and can be protected with the `prod` environment.

Configure:

- GitHub secret `AZURE_CLIENT_ID`
- GitHub secret `AZURE_CLIENT_SECRET`
- GitHub secret `AZURE_TENANT_ID`
- GitHub environment/repository variable `FABRIC_DEV_WORKSPACE`
- GitHub environment/repository variable `FABRIC_PROD_WORKSPACE`
- GitHub secret `FABRIC_DEV_SOURCE_WORKSPACE_ID`
- GitHub secret `FABRIC_DEV_SOURCE_LAKEHOUSE_ID`
- GitHub secret `FABRIC_DEV_SOURCE_TABLE_NAME`
- GitHub secret `FABRIC_DEV_CONNECTION_ID`

## Pull request validation checks

The repository now includes three separate PR validation workflows so you can require them individually in branch protection on `main`:

- `Validate semantic model` runs `.\\scripts\\validate_semantic_model.py`
- `Validate report PBIR` runs `.\\scripts\\validate_report_pbir.py`
- `Validate project bindings` runs `.\\scripts\\validate_project_bindings.py`

These workflows are repo-native, keep `workflow_dispatch`, and do not require Fabric secrets. They validate the semantic-model structure, the PBIR report shell and visual metadata, and the cross-file bindings between `.pbip`, `.platform`, `definition.pbir`, `parameter.yml`, and `deploy.py`.

The validators also enforce a small set of deterministic best-practice rules: TMDL table/partition naming consistency, tab-based TMDL indentation, non-empty PBIR pages, valid report-to-model field bindings, and required `.gitignore` entries for local `.pbi` artifacts. Description coverage on visible semantic-model objects is reported as warnings so it improves review quality without blocking normal report iteration.

## Source parameterization

The semantic model is parameterized to read from a Fabric Lakehouse table, not from a local file.

Parameters currently defined in `VideoGameSales.SemanticModel\definition\expressions.tmdl`:

- `FabricWorkspaceId`
- `FabricLakehouseId`
- `VideoGameSalesLakehouseTable`

The repository only contains safe placeholder values. During deployment, `deploy.py` renders a temporary `parameter.yml` with values from the caller and passes that file to `fabric-cicd`.

Recommended setup:

1. Upload the source data into a Fabric Lakehouse.
2. Materialize it as a table such as `VideoGameSalesRaw`.
3. Provide the real source workspace ID, lakehouse ID, table name, and semantic model connection ID through GitHub secrets or local environment variables.

This keeps the public repository free of machine-specific paths and makes the semantic model CI/CD friendly.

`deploy.py` reads these standard environment variable names:

- `FABRIC_SOURCE_WORKSPACE_ID`
- `FABRIC_SOURCE_LAKEHOUSE_ID`
- `FABRIC_SOURCE_TABLE_NAME`
- `FABRIC_SEMANTIC_MODEL_CONNECTION_ID`

It then creates a temporary parameter file for the deployment run, so the committed repository never contains your real Fabric source identifiers or connection IDs.

## Notes

- This repository now contains a renderable PBIR report shell plus starter visuals.
- For future reports, treat `VideoGameSales.Report\` as the baseline template unless you intentionally refresh the shell from a newer known-good PBIR export.
- See `PBIR_REPORT_AUTHORING_GUIDE.md` for a project-agnostic guide to creating PBIR reports without relying on Power BI Desktop to generate the initial files.
- That guide also captures the main delivery gotchas from this project: report shell completeness, `.platform` requirements, Fabric connection binding, explicit date parsing, normalized relationship keys, and M-query deployment quirks.
