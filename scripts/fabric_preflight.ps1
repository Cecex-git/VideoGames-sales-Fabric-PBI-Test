param(
    [string]$WorkspaceName
)

$ErrorActionPreference = "Stop"

Write-Host "Fabric CLI version:"
fab --version

Write-Host ""
Write-Host "Authenticating with Fabric..."
fab auth login

Write-Host ""
Write-Host "Available workspaces:"
fab dir

if ($WorkspaceName) {
    Write-Host ""
    Write-Host "Inspecting workspace '$WorkspaceName'..."
    fab get "$WorkspaceName.Workspace"
}

