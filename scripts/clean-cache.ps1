# Clean Python cache and ensure clean imports
# This fixes issues where stale bytecode prevents proper logging/imports

Write-Host "Cleaning Python cache..." -ForegroundColor Yellow

# Remove __pycache__ directories
Get-ChildItem -Path . -Recurse -Directory -Filter "__pycache__" -ErrorAction SilentlyContinue | ForEach-Object {
    Write-Host "  Removing: $($_.FullName)" -ForegroundColor Gray
    Remove-Item -Path $_.FullName -Recurse -Force
}

# Remove .pyc files
Get-ChildItem -Path . -Recurse -File -Filter "*.pyc" -ErrorAction SilentlyContinue | ForEach-Object {
    Write-Host "  Removing: $($_.FullName)" -ForegroundColor Gray
    Remove-Item -Path $_.FullName -Force
}

# Remove .pyo files
Get-ChildItem -Path . -Recurse -File -Filter "*.pyo" -ErrorAction SilentlyContinue | ForEach-Object {
    Write-Host "  Removing: $($_.FullName)" -ForegroundColor Gray
    Remove-Item -Path $_.FullName -Force
}

Write-Host ""
Write-Host "Cache cleaned successfully!" -ForegroundColor Green
Write-Host ""
Write-Host "Note: Python will regenerate cache files on next run." -ForegroundColor Cyan
Write-Host "This ensures all modules use the current import paths." -ForegroundColor Cyan

