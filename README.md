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

The report is intentionally scaffolded as a blank PBIR report page so you can finish the visual layout in Power BI Desktop while keeping the project source-control friendly.

## Deployment

### Local deployment

Use interactive auth for a manual deployment:

```powershell
python .\deploy.py --workspace-name "<Your Fabric Workspace>" --environment dev
```

### GitHub Actions deployment

The workflow in `.github\workflows\deploy-dev.yml` deploys on pushes to the `dev` branch.

Configure:

- GitHub secret `AZURE_CREDENTIALS`
- GitHub environment/repository variable `FABRIC_DEV_WORKSPACE`
- GitHub secret `FABRIC_DEV_SOURCE_WORKSPACE_ID`
- GitHub secret `FABRIC_DEV_SOURCE_LAKEHOUSE_ID`
- GitHub secret `FABRIC_DEV_SOURCE_TABLE_NAME`

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
3. Provide the real source workspace ID, lakehouse ID, and table name through GitHub secrets or local environment variables.

This keeps the public repository free of machine-specific paths and makes the semantic model CI/CD friendly.

`deploy.py` reads these standard environment variable names:

- `FABRIC_SOURCE_WORKSPACE_ID`
- `FABRIC_SOURCE_LAKEHOUSE_ID`
- `FABRIC_SOURCE_TABLE_NAME`

It then creates a temporary parameter file for the deployment run, so the committed repository never contains your real Fabric source identifiers.

## Notes

- The blank PBIR report shell is valid as a scaffold, but the planned report pages and visuals still need to be authored in Power BI Desktop.
