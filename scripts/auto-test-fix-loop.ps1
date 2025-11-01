Param(
    [Parameter(Mandatory=$true, Position=0)] [string]$Query,
    [int]$MaxIterations = 5,
    [switch]$Headless
)

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Automatic Test-Fix-Rerun Loop" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Query: '$Query'" -ForegroundColor Gray
Write-Host "Max Iterations: $MaxIterations" -ForegroundColor Gray
Write-Host ""

$projectRoot = Split-Path -Parent $PSScriptRoot
$testScript = Join-Path $projectRoot "scripts\test-script.ps1"
$logsPath = Join-Path $projectRoot "logs"
$fixLogPath = Join-Path $logsPath "auto-fix.log"

if (-not (Test-Path $logsPath)) { New-Item -ItemType Directory -Path $logsPath | Out-Null }
Set-Content -Path $fixLogPath -Value "" -Encoding UTF8

function Write-FixLog {
    param([string]$Message)
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $logLine = "[$timestamp] $Message"
    Write-Host $logLine -ForegroundColor Yellow
    Add-Content -Path $fixLogPath -Value $logLine -Encoding UTF8
}

for ($iteration = 1; $iteration -le $MaxIterations; $iteration++) {
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Magenta
    Write-Host "ITERATION $iteration of $MaxIterations" -ForegroundColor Magenta
    Write-Host "========================================" -ForegroundColor Magenta
    Write-Host ""
    
    Write-FixLog "Starting iteration $iteration"
    
    # Run the test
    $headlessArg = if ($Headless) { "-Headless" } else { "" }
    $testCmd = "powershell -NoProfile -ExecutionPolicy Bypass -File '$testScript' '$Query' $headlessArg"
    
    Write-Host "Running test script..." -ForegroundColor Cyan
    $output = & powershell -NoProfile -ExecutionPolicy Bypass -File $testScript $Query $(if ($Headless) { "-Headless" } else { "" }) 2>&1
    $exitCode = $LASTEXITCODE
    
    Write-Host "Test completed with exit code: $exitCode" -ForegroundColor $(if ($exitCode -eq 0) { 'Green' } else { 'Yellow' })
    
    if ($exitCode -eq 0) {
        Write-Host ""
        Write-Host "========================================" -ForegroundColor Green
        Write-Host "SUCCESS! Test passed on iteration $iteration" -ForegroundColor Green
        Write-Host "========================================" -ForegroundColor Green
        Write-FixLog "Test PASSED on iteration $iteration"
        exit 0
    }
    
    # Analyze failures
    Write-Host ""
    Write-Host "Analyzing failures..." -ForegroundColor Yellow
    Write-FixLog "Test FAILED. Analyzing logs..."
    
    $e2eErr = Join-Path $logsPath "e2e.err.log"
    $e2eOut = Join-Path $logsPath "e2e.out.log"
    $backendLog = Join-Path $logsPath "backend.log"
    
    $issues = @()
    
    # Check Playwright errors
    if (Test-Path $e2eErr) {
        $e2eErrors = Get-Content $e2eErr -Raw
        if ($e2eErrors -match "No search results found") {
            $issues += "Playwright: No search results found - UI selectors may be wrong"
            Write-FixLog "Detected: No search results found"
        }
        if ($e2eErrors -match "Search input not found") {
            $issues += "Playwright: Search input not found - input selector needs adjustment"
            Write-FixLog "Detected: Search input not found"
        }
        if ($e2eErrors -match "Timeout") {
            $issues += "Playwright: Timeout - page may be loading slowly"
            Write-FixLog "Detected: Timeout error"
        }
    }
    
    # Check backend errors (ignore PowerShell noise)
    if (Test-Path $backendLog) {
        $realErrors = Get-Content $backendLog | Where-Object { 
            $_ -match "ERROR" -and 
            $_ -notmatch "NativeCommandError" -and
            $_ -notmatch "FullyQualifiedErrorId"
        }
        if ($realErrors) {
            $issues += "Backend: Real errors detected in backend.log"
            Write-FixLog "Detected: Backend errors"
        }
    }
    
    if ($issues.Count -eq 0) {
        $issues += "Unknown failure - check logs manually"
    }
    
    Write-Host ""
    Write-Host "Issues detected:" -ForegroundColor Red
    $issues | ForEach-Object { Write-Host "  - $_" -ForegroundColor Red }
    Write-Host ""
    
    # Prompt for human intervention (you can automate fixes here)
    Write-Host "========================================" -ForegroundColor Yellow
    Write-Host "ACTION REQUIRED" -ForegroundColor Yellow
    Write-Host "========================================" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "The AI assistant should now:" -ForegroundColor Cyan
    Write-Host "1. Analyze the issues above" -ForegroundColor Cyan
    Write-Host "2. Fix the code (test-flow.js, selectors, etc.)" -ForegroundColor Cyan
    Write-Host "3. This script will automatically rerun" -ForegroundColor Cyan
    Write-Host ""
    
    if ($iteration -lt $MaxIterations) {
        Write-Host "Press Enter to continue to next iteration after fixes are applied..." -ForegroundColor Yellow
        Write-Host "(Or Ctrl+C to stop)" -ForegroundColor Gray
        Read-Host
    }
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Red
Write-Host "Max iterations ($MaxIterations) reached without success" -ForegroundColor Red
Write-Host "========================================" -ForegroundColor Red
Write-Host ""
Write-FixLog "FAILED: Max iterations reached"
exit 1

