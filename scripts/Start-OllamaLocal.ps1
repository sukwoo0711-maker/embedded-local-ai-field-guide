[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
$env:OLLAMA_HOST = "127.0.0.1:11434"
$env:OLLAMA_CONTEXT_LENGTH = "8192"
$env:OLLAMA_NUM_PARALLEL = "1"
$env:OLLAMA_MAX_LOADED_MODELS = "1"
$env:OLLAMA_FLASH_ATTENTION = "1"
$env:OLLAMA_KV_CACHE_TYPE = "q8_0"
$env:OLLAMA_NO_CLOUD = "1"

$Ollama = Get-Command ollama -ErrorAction Stop
Write-Output "Starting Ollama on loopback with one parallel request and one loaded model."
Write-Output "This command stays in the foreground. Press Ctrl+C to stop it."
& $Ollama.Source serve
exit $LASTEXITCODE
