@echo off
SETLOCAL
REM counts
powershell -NoProfile -Command "(Get-Content '..\exports\index_pages.json'    -Raw | ConvertFrom-Json).Count"
powershell -NoProfile -Command "(Get-Content '..\exports\index_posts.json'    -Raw | ConvertFrom-Json).Count"
powershell -NoProfile -Command "(Get-Content '..\exports\index_products.json' -Raw | ConvertFrom-Json).Count"
powershell -NoProfile -Command "(Get-Content '..\exports\embeddings.jsonl').Count"
REM archive
for /f %%t in ('powershell -NoProfile -Command "Get-Date -Format yyyy-MM-dd_HHmm"') do set "STAMP=%%t"
powershell -NoProfile -Command "Compress-Archive -Path '..\exports\index_*.json','..\exports\embeddings.jsonl' -DestinationPath '..\exports\backup_%STAMP%.zip' -Force"
echo Created ..\exports\backup_%STAMP%.zip
ENDLOCAL & pause
