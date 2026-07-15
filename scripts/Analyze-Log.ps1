[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$InputPath,

    [ValidateSet("deterministic", "triage", "analysis", "auto")]
    [string]$Stage = "auto",

    [string]$BaseUrl = "http://127.0.0.1:11434",
    [string]$TriageModel = "embedded-log-triage:4b",
    [string]$AnalysisModel = "embedded-log-analysis:9b",
    [string]$OutputPath
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
$SourceRoot = Join-Path $RepoRoot "src"
$PreviousPythonPath = $env:PYTHONPATH

try {
    if ([string]::IsNullOrWhiteSpace($PreviousPythonPath)) {
        $env:PYTHONPATH = $SourceRoot
    } else {
        $env:PYTHONPATH = "$SourceRoot$([IO.Path]::PathSeparator)$PreviousPythonPath"
    }

    if ($Stage -eq "deterministic") {
        $Arguments = @(
            "-m", "embedded_log_analyzer",
            "deterministic", $InputPath
        )
    } else {
        $Arguments = @(
            "-m", "embedded_log_analyzer",
            "analyze", $InputPath,
            "--stage", $Stage,
            "--base-url", $BaseUrl,
            "--triage-model", $TriageModel,
            "--analysis-model", $AnalysisModel
        )
    }

    if (-not [string]::IsNullOrWhiteSpace($OutputPath)) {
        $Arguments += @("--output", $OutputPath)
    }

    & python @Arguments
    exit $LASTEXITCODE
} finally {
    $env:PYTHONPATH = $PreviousPythonPath
}
