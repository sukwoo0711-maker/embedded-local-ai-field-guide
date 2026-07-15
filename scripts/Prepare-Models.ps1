[CmdletBinding()]
param(
    [switch]$Apply
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot

$Operations = @(
    @{
        Display = "ollama pull qwen3.5:4b"
        Arguments = @("pull", "qwen3.5:4b")
    },
    @{
        Display = "ollama pull qwen3.5:9b"
        Arguments = @("pull", "qwen3.5:9b")
    },
    @{
        Display = "ollama create embedded-log-triage:4b -f models/Modelfile.triage"
        Arguments = @(
            "create",
            "embedded-log-triage:4b",
            "-f",
            (Join-Path $RepoRoot "models/Modelfile.triage")
        )
    },
    @{
        Display = "ollama create embedded-log-analysis:9b -f models/Modelfile.analysis"
        Arguments = @(
            "create",
            "embedded-log-analysis:9b",
            "-f",
            (Join-Path $RepoRoot "models/Modelfile.analysis")
        )
    }
)

if (-not $Apply) {
    Write-Output "Dry run. The following commands would execute:"
    foreach ($Operation in $Operations) {
        Write-Output "  $($Operation.Display)"
    }
    Write-Output "No changes made. Re-run with -Apply to pull and create models."
    exit 0
}
$Ollama = Get-Command ollama -ErrorAction Stop
foreach ($Operation in $Operations) {
    Write-Output "Running: $($Operation.Display)"
    & $Ollama.Source @($Operation.Arguments)
    if ($LASTEXITCODE -ne 0) {
        throw "Operation failed with exit code $LASTEXITCODE"
    }
}
