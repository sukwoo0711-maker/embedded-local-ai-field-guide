[CmdletBinding()]
param(
    [string]$BaseUrl = "http://127.0.0.1:11434",
    [string]$TriageModel = "embedded-log-triage:4b",
    [string]$AnalysisModel = "embedded-log-analysis:9b"
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
$SourceRoot = Join-Path $RepoRoot "src"

Write-Output "== GPU =="
$NvidiaSmi = Get-Command nvidia-smi -ErrorAction SilentlyContinue
if ($null -eq $NvidiaSmi) {
    Write-Output "nvidia-smi: not found"
} else {
    & $NvidiaSmi.Source --query-gpu=name,memory.total,driver_version,compute_cap --format=csv,noheader
}
Write-Output "== Ollama CLI =="
$Ollama = Get-Command ollama -ErrorAction SilentlyContinue
if ($null -eq $Ollama) {
    Write-Output "ollama: not found"
} else {
    & $Ollama.Source --version
    & $Ollama.Source list
}

Write-Output "== Bounded analyzer =="
$PreviousPythonPath = $env:PYTHONPATH
try {
    if ([string]::IsNullOrWhiteSpace($PreviousPythonPath)) {
        $env:PYTHONPATH = $SourceRoot
    } else {
        $env:PYTHONPATH = "$SourceRoot$([IO.Path]::PathSeparator)$PreviousPythonPath"
    }
    & python -m embedded_log_analyzer doctor --base-url $BaseUrl --triage-model $TriageModel --analysis-model $AnalysisModel
    exit $LASTEXITCODE
} finally {
    $env:PYTHONPATH = $PreviousPythonPath
}
