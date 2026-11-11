$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath (Split-Path -Parent $PSScriptRoot)
& .\.venv\Scripts\waitress-serve.exe --listen=127.0.0.1:8021 --threads=8 --call app:create_app
