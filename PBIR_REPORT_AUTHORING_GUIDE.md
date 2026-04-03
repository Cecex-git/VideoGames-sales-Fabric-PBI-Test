# PBIR Report Authoring Guide

This guide describes how to create a **renderable PBIR report** for Power BI / Fabric **without depending on Power BI Desktop to generate the initial files**.

It is intended to be reusable across projects.

## Goal

Create a report folder that:

- opens in Power BI Desktop
- opens in Fabric
- can be versioned in Git
- can be connected to either a local PBIP semantic model (`byPath`) or a deployed semantic model (`byConnection`)

## Important constraint

PBIR is strict JSON, but **valid JSON is not enough**. A report can:

- deploy successfully
- pass schema validation
- and still fail to render

if the report shell is too minimal.

So the goal is not just "schema-valid files", but a **known-good minimum shell**.

## Recommended approach

Maintain a **reusable PBIR starter template** in source control and create new reports by copying that template.

Do **not** start from a tiny handcrafted report with only:

- `.platform`
- `definition.pbir`
- `definition\report.json`
- `definition\pages\page.json`

That level of minimalism is not reliable enough for rendering.

## Minimum working folder structure

```text
<ReportName>.Report/
├── .platform
├── definition.pbir
├── definition/
│   ├── version.json
│   ├── report.json
│   └── pages/
│       ├── pages.json
│       └── <page-name>/
│           ├── page.json
│           └── visuals/
│               └── <visual-name>/
│                   └── visual.json
└── StaticResources/
    └── SharedResources/
        └── BaseThemes/
            └── CY26SU02.json
```

## Required files

### 1. `.platform`

```json
{
  "$schema": "https://developer.microsoft.com/json-schemas/fabric/gitIntegration/platformProperties/2.0.0/schema.json",
  "metadata": {
    "displayName": "MyReport",
    "type": "Report",
    "description": "PBIR report for my project."
  },
  "config": {
    "version": "2.0",
    "logicalId": "11111111-1111-1111-1111-111111111111"
  }
}
```

**Rules**

- `type` must be `Report`
- `config.version` must be `"2.0"`
- `logicalId` must be a GUID

### 2. `definition.pbir`

Use **one** of these connection patterns.

#### `byPath` example

```json
{
  "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definitionProperties/2.0.0/schema.json",
  "version": "4.0",
  "datasetReference": {
    "byPath": {
      "path": "../MyModel.SemanticModel"
    }
  }
}
```

#### `byConnection` example

```json
{
  "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definitionProperties/2.0.0/schema.json",
  "version": "4.0",
  "datasetReference": {
    "byConnection": {
      "connectionString": "semanticmodelid=22222222-2222-2222-2222-222222222222"
    }
  }
}
```

### 3. `definition\version.json`

```json
{
  "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/versionMetadata/1.0.0/schema.json",
  "version": "2.0.0"
}
```

### 4. `definition\report.json`

This file must be **richer than a minimal stub**.

```json
{
  "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/report/3.2.0/schema.json",
  "themeCollection": {
    "baseTheme": {
      "name": "CY26SU02",
      "reportVersionAtImport": {
        "visual": "2.6.0",
        "report": "3.1.0",
        "page": "2.3.0"
      },
      "type": "SharedResources"
    }
  },
  "objects": {
    "section": [
      {
        "properties": {
          "verticalAlignment": {
            "expr": {
              "Literal": {
                "Value": "'Top'"
              }
            }
          }
        }
      }
    ]
  },
  "resourcePackages": [
    {
      "name": "SharedResources",
      "type": "SharedResources",
      "items": [
        {
          "name": "CY26SU02",
          "path": "BaseThemes/CY26SU02.json",
          "type": "BaseTheme"
        }
      ]
    }
  ],
  "settings": {
    "useStylableVisualContainerHeader": true,
    "exportDataMode": "AllowSummarized",
    "defaultDrillFilterOtherVisuals": true,
    "allowChangeFilterTypes": true,
    "useEnhancedTooltips": true,
    "useDefaultAggregateDisplayName": true
  }
}
```

**Why this matters**

The report shell must include:

- `themeCollection.baseTheme`
- `resourcePackages`
- report-level `objects`
- report-level `settings`

A much smaller file may deploy but fail during rendering.

### 5. Base theme file

Place the base theme file here:

```text
StaticResources\SharedResources\BaseThemes\CY26SU02.json
```

This file must exist if `report.json` references it in `resourcePackages`.

You can:

- copy a known-good Microsoft base theme file
- keep the same base theme across projects
- later add your own `RegisteredResources` theme if needed

### 6. `definition\pages\pages.json`

```json
{
  "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/pagesMetadata/1.0.0/schema.json",
  "pageOrder": [
    "overview",
    "details"
  ],
  "activePageName": "overview"
}
```

### 7. `definition\pages\<page>\page.json`

```json
{
  "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/page/2.1.0/schema.json",
  "name": "overview",
  "displayName": "Overview",
  "displayOption": "FitToPage",
  "height": 720,
  "width": 1280
}
```

**Rules**

- one folder per page
- `name` should match the folder name
- use stable names like `overview`, `sales_trend`, `details`

## Adding visuals

Each visual lives in:

```text
definition\pages\<page-name>\visuals\<visual-name>\visual.json
```

### Minimal card visual example

```json
{
  "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/visualContainer/2.6.0/schema.json",
  "name": "total_sales_card",
  "position": {
    "x": 24,
    "y": 24,
    "z": 0,
    "height": 120,
    "width": 220,
    "tabOrder": 0
  },
  "visual": {
    "visualType": "card",
    "query": {
      "queryState": {
        "Values": {
          "projections": [
            {
              "field": {
                "Measure": {
                  "Expression": {
                    "SourceRef": {
                      "Entity": "FactSales"
                    }
                  },
                  "Property": "Total Sales"
                }
              },
              "queryRef": "FactSales.Total Sales",
              "nativeQueryRef": "Total Sales"
            }
          ]
        }
      },
      "sortDefinition": {
        "sort": [
          {
            "field": {
              "Measure": {
                "Expression": {
                  "SourceRef": {
                    "Entity": "FactSales"
                  }
                },
                "Property": "Total Sales"
              }
            },
            "direction": "Descending"
          }
        ],
        "isDefaultSort": true
      }
    },
    "drillFilterOtherVisuals": true
  }
}
```

## Known-good visual type names

Use PBIR visual type names such as:

- `card`
- `lineChart`
- `columnChart`
- `barChart`
- `donutChart`
- `tableEx`
- `textbox`

## Recommended page layout rule

Stay under **7 visuals per page**.

A safe pattern is:

1. KPI cards at the top
2. trend/breakdown charts in the middle
3. detail table at the bottom or on a separate page

## Validation checklist

Before deployment, verify:

1. `.platform` uses the Git integration schema and `config.version: "2.0"`
2. `definition.pbir` points to the correct semantic model
3. `definition\version.json` uses `2.0.0`
4. `definition\report.json` includes:
   - `themeCollection.baseTheme`
   - `resourcePackages`
   - `objects`
   - `settings`
5. the base theme file exists at the path referenced in `report.json`
6. every page listed in `pages.json` has a matching folder and `page.json`
7. every visual folder contains `visual.json`
8. all field references in visuals match real tables/measures in the semantic model
9. `.pbi\localSettings.json` and `.pbi\cache.abf` are ignored by Git

## Git ignore

Recommended entries:

```gitignore
**/.pbi/localSettings.json
**/.pbi/cache.abf
```

## What failed in practice

The main failure pattern was:

- report deployed successfully
- semantic model was healthy
- report failed to open/render in Desktop or Fabric

Root cause:

- the handcrafted PBIR shell was too minimal
- page/report metadata was valid enough for deployment
- but not complete enough for rendering

Symptoms included rendering errors related to missing page visual metadata.

## Safe authoring rule

If you do not want to generate report files with Power BI Desktop, then your best process is:

1. maintain a reusable **PBIR starter template**
2. keep its schema versions aligned
3. keep the base theme/resource wiring intact
4. create new reports by copying that template
5. change only:
   - report name / `.platform`
   - semantic model binding in `definition.pbir`
   - page list
   - page files
   - visual files

## Related project lessons worth carrying forward

These are not all PBIR-specific, but they mattered in real PBIP/Fabric delivery and are worth remembering for future projects.

### Semantic model and data-shaping

- Prefer **M/import partitions** for sourced dimensions instead of DAX calculated tables when the dimensions come from the same upstream source. This kept refresh and deployment behavior more predictable.
- Make **date parsing explicit** in M. Locale-sensitive conversion broke on values such as `17-09-2013`; explicit `dd-MM-yyyy` parsing was safer.
- Use **normalized hidden relationship keys** for text dimensions instead of raw labels. Case-insensitive collisions like `5TH Cell` vs `5th Cell` can break one-to-many relationships.
- Shared M helper functions that are reused across tables should be **top-level shared expressions**, not local functions inside one query.
- Use `Table.AddColumn`; `Table.AddColumns` is not a valid M function and caused deployment/import failures.
- When reading a Lakehouse table in Desktop/Fabric, table lookup should not rely only on `Id`. Matching by `Id`, `Name`, or `DisplayName` is more robust.

### Fabric deployment and CI/CD

- `fabric-cicd` discovers deployable items only in folders that contain a valid `.platform` file.
- `.platform` must match the Git integration schema exactly, including the `fabric/gitIntegration/platformProperties/2.0.0` `$schema` and `config.version: "2.0"`.
- On Windows, direct environment-variable replacement in `parameter.yml` was unreliable; generating a temporary runtime `parameter.yml` in the deployment script was safer.
- Deploying a semantic model is not enough by itself; it also needs **Fabric connection binding**. The required ID is the **Fabric connection object ID**, not the workspace ID or lakehouse ID.
- Fabric `getDefinition` is a **long-running operation**. An empty initial response can still be correct; poll the `Location` endpoint and then read `/result`.

## Final recommendation

For non-Desktop authoring, treat PBIR report creation as **template-based engineering**, not as fully free-form JSON authoring.

That is the most reliable way to make PBIR reports open correctly across both:

- Power BI Desktop
- Microsoft Fabric
