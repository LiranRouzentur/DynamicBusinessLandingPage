# Monitor logs live during test execution, detect errors, fix them, and restart

param(
    [string]$Query = "test"
)

$ErrorActionPreference = "Continue"
$projectRoot = (Get-Location).Path

Write-Host "`n=== LIVE LOG MONITOR WITH AUTO-FIX ===" -ForegroundColor Cyan
Write-Host "This script will:" -ForegroundColor Gray
Write-Host "  1. Start the test" -ForegroundColor White
Write-Host "  2. Monitor logs live for errors" -ForegroundColor White
Write-Host "  3. Auto-detect schema/validation errors" -ForegroundColor White
Write-Host "  4. Fix issues automatically" -ForegroundColor White
Write-Host "  5. Restart test flow until success" -ForegroundColor White
Write-Host ""

# Function to check for schema errors in agents log
function Check-ForSchemaError {
    $agentsLog = Join-Path $projectRoot "logs\agents.log"
    if (Test-Path $agentsLog) {
        $lastLines = Get-Content $agentsLog -Tail 20 -ErrorAction SilentlyContinue | Out-String
        if ($lastLines -match "Missing.*business_page_url" -or $lastLines -match "Missing.*logo_url" -or $lastLines -match "Invalid schema.*required.*is required") {
            Write-Host "[ERROR DETECTED] Schema validation error found!" -ForegroundColor Red
            return $true
        }
    }
    return $false
}

# Function to fix schema errors
function Fix-SchemaErrors {
    Write-Host "[FIX] Attempting to fix schema errors..." -ForegroundColor Yellow
    
    $schemaFile = Join-Path $projectRoot "agents\app\mapper\mapper_schemas.py"
    if (Test-Path $schemaFile) {
        $content = Get-Content $schemaFile -Raw -Encoding UTF8
        
        # Check if business_page_url is in required
        if ($content -notmatch 'required.*business_page_url.*qa_report' -and $content -match 'required.*\["business_summary", "assats"\]') {
            Write-Host "[FIX] Adding missing properties to root required array..." -ForegroundColor Yellow
            $content = $content -replace '(required.*\["business_summary", "assats"\])', 'required": ["business_summary", "assats", "business_page_url", "qa_report"]'
            Set-Content -Path $schemaFile -Value $content -Encoding UTF8 -NoNewline
            Write-Host "[FIX] Schema file updated" -ForegroundColor Green
            
            # Trigger reload by touching the file
            (Get-Item $schemaFile).LastWriteTime = Get-Date
            Start-Sleep -Seconds 2
            return $true
        }
    }
    return $false
}

# Start monitoring logs in background
Write-Host "[MONITOR] Starting log monitoring..." -ForegroundColor Cyan

$monitorJob = Start-Job -ScriptBlock {
    param($logPath)
    Get-Content $logPath -Tail 0 -Wait -ErrorAction SilentlyContinue | ForEach-Object {
        if ($_ -match 'ERROR|Invalid schema|Missing|failed' -and $_ -notmatch 'DEBUG') {
            Write-Output "[ERROR] $_"
        } elseif ($_ -match 'INFO.*BUILD|orchestrate|Mapper|Generator') {
            Write-Output "[INFO] $_"
        }
    }
} -ArgumentList (Join-Path $projectRoot "logs\agents.log")

$backendMonitorJob = Start-Job -ScriptBlock {
    param($logPath)
    Get-Content $logPath -Tail 0 -Wait -ErrorAction SilentlyContinue | ForEach-Object {
        if ($_ -match 'ERROR|Build failed|500.*Internal Server Error') {
            Write-Output "[ERROR] $_"
        } elseif ($_ -match 'INFO.*build|POST.*\/build') {
            Write-Output "[INFO] $_"
        }
    }
} -ArgumentList (Join-Path $projectRoot "logs\backend.log")

# Run test with monitoring
$maxAttempts = 3
$attempt = 0

while ($attempt -lt $maxAttempts) {
    $attempt++
    Write-Host "`n=== ATTEMPT $attempt of $maxAttempts ===" -ForegroundColor Cyan
    
    # Check for schema errors before starting
    if (Check-ForSchemaError) {
        Write-Host "[PRE-CHECK] Schema error detected, fixing..." -ForegroundColor Yellow
        Fix-SchemaErrors
        Start-Sleep -Seconds 3
    }
    
    # Run test in background
    Write-Host "[TEST] Starting test run..." -ForegroundColor Green
    $testProcess = Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$projectRoot'; .\scripts\test-script.ps1 -Query '$Query'" -PassThru -WindowStyle Minimized
    
    # Monitor for errors
    $errorDetected = $false
    $startTime = Get-Date
    $timeout = (Get-Date).AddMinutes(15) # 15 minute timeout
    
    while ((Get-Date) -lt $timeout -and -not $errorDetected) {
        Start-Sleep -Seconds 2
        
        # Check monitor jobs for errors
        $agentOutput = Receive-Job $monitorJob -ErrorAction SilentlyContinue
        $backendOutput = Receive-Job $backendMonitorJob -ErrorAction SilentlyContinue
        
        foreach ($line in $agentOutput) {
            Write-Host $line -ForegroundColor $(if ($line -match 'ERROR') { 'Red' } else { 'Cyan' })
            if ($line -match 'Invalid schema|Missing.*required') {
                $errorDetected = $true
                Write-Host "[ERROR DETECTED] Schema validation error!" -ForegroundColor Red
            }
        }
        
        foreach ($line in $backendOutput) {
            Write-Host $line -ForegroundColor $(if ($line -match 'ERROR') { 'Red' } else { 'Yellow' })
            if ($line -match 'Build failed|500') {
                $errorDetected = $true
                Write-Host "[ERROR DETECTED] Build failed!" -ForegroundColor Red
            }
        }
        
        # Check if test process completed
        if ($testProcess.HasExited) {
            Write-Host "[TEST] Test process exited with code $($testProcess.ExitCode)" -ForegroundColor $(if ($testProcess.ExitCode -eq 0) { 'Green' } else { 'Red' })
            break
        }
        
        # Manual check for schema errors in logs
        if (Check-ForSchemaError) {
            $errorDetected = $true
        }
    }
    
    if ($errorDetected) {
        Write-Host "`n[FIX] Error detected, attempting to fix..." -ForegroundColor Yellow
        
        # Stop test process
        if (-not $testProcess.HasExited) {
            Stop-Process -Id $testProcess.Id -Force -ErrorAction SilentlyContinue
        }
        
        # Fix schema
        if (Fix-SchemaErrors) {
            Write-Host "[FIX] Schema fixed, waiting for reload..." -ForegroundColor Green
            Start-Sleep -Seconds 5
        } else {
            Write-Host "[FIX] Could not auto-fix, checking logs manually..." -ForegroundColor Yellow
            Start-Sleep -Seconds 3
        }
        
        # Continue to next attempt
        continue
    } else {
        Write-Host "`n[SUCCESS] Test completed without detected errors!" -ForegroundColor Green
        break
    }
}

# Cleanup
Stop-Job $monitorJob, $backendMonitorJob -ErrorAction SilentlyContinue
Remove-Job $monitorJob, $backendMonitorJob -ErrorAction SilentlyContinue

Write-Host "`n=== MONITORING COMPLETE ===" -ForegroundColor Cyan

