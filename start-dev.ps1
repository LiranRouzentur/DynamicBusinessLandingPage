# Start both servers in separate windows
Write-Host "Starting Backend and Frontend servers..." -ForegroundColor Cyan
Write-Host ""

# Start backend in a new window with visible output
$backendArgs = @(
    "-NoExit",
    "-Command",
    "cd '$PSScriptRoot\backend'; .\.venv\Scripts\Activate.ps1; Write-Host 'Backend starting on http://localhost:8000' -ForegroundColor Green; python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000"
)
Start-Process powershell -ArgumentList $backendArgs

# Wait a moment
Start-Sleep -Seconds 2

# Start frontend in a new window with visible output  
$frontendArgs = @(
    "-NoExit",
    "-Command",
    "cd '$PSScriptRoot\client'; Write-Host 'Frontend starting on http://localhost:5173' -ForegroundColor Cyan; npm run dev"
)
Start-Process powershell -ArgumentList $frontendArgs

Write-Host "Servers started in separate windows!" -ForegroundColor Green
Write-Host ""
Write-Host "Backend:  http://localhost:8000" -ForegroundColor Cyan
Write-Host "Frontend: http://localhost:5173" -ForegroundColor Cyan
Write-Host ""
Write-Host "Check the new PowerShell windows for output" -ForegroundColor Yellow
Write-Host "Open your browser to: http://localhost:5173" -ForegroundColor Yellow

