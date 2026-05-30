param(
    [Parameter(Mandatory=$true)]
    [string]$Name
)

$Root = Split-Path -Parent $PSScriptRoot
$TemplateDir = Join-Path $Root "assets\templates"
$ProjectDir = Join-Path $Root "projects\$Name"

if (Test-Path $ProjectDir) {
    Write-Error "Project already exists: $ProjectDir"
    exit 1
}

New-Item -ItemType Directory -Path $ProjectDir -Force | Out-Null
Copy-Item -Path (Join-Path $TemplateDir "*") -Destination $ProjectDir -Recurse
Write-Host "Created project: $ProjectDir"
