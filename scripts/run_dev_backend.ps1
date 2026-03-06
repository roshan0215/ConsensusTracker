$ErrorActionPreference = 'Stop'

Set-Location $PSScriptRoot\..

python -m pip install -r backend\requirements.txt
python -m scripts.init_db
python -m uvicorn backend.app:app --reload --port 8000
