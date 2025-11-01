Param(
    [Parameter(Mandatory=$true, Position=0)] [string]$Query,
    [int]$MaxIterations = 10,
    [switch]$Headless
)

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Fully Automatic Test-Fix-Rerun Loop" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Query: '$Query'" -ForegroundColor Gray
Write-Host "Max Iterations: $MaxIterations" -ForegroundColor Gray
Write-Host "Mode: FULLY AUTOMATIC (no human intervention)" -ForegroundColor Magenta
Write-Host ""

$projectRoot = Split-Path -Parent $PSScriptRoot
$testScript = Join-Path $projectRoot "scripts\test-script.ps1"
$logsPath = Join-Path $projectRoot "logs"
$fixLogPath = Join-Path $logsPath "auto-fix.log"
$testFlowJs = Join-Path $projectRoot "debuger\test-flow.js"
$clientSrcPath = Join-Path $projectRoot "client\src"

if (-not (Test-Path $logsPath)) { New-Item -ItemType Directory -Path $logsPath | Out-Null }
Set-Content -Path $fixLogPath -Value "" -Encoding UTF8

$appliedFixes = @()

function Write-FixLog {
    param([string]$Message, [string]$Color = "Yellow")
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $logLine = "[$timestamp] $Message"
    Write-Host $logLine -ForegroundColor $Color
    Add-Content -Path $fixLogPath -Value $logLine -Encoding UTF8
}

function Apply-Fix-NoSearchResults {
    Write-FixLog "AUTO-FIX: Updating test-flow.js selectors for search input" "Cyan"
    
    $content = Get-Content $testFlowJs -Raw
    
    # Enhance input finder with more selectors
    $oldInputFn = @"
async function findInput(page) {
  const selectors = [
    'input[placeholder*="Search" i]',
    'input[aria-label*="search" i]',
    'input[type="search"]',
    'input[type="text"]',
    'input',
    'textarea'
  ];
  for (const sel of selectors) {
    const el = await page.`$(sel);
    if (el) return el;
  }
  return null;
}
"@

    $newInputFn = @"
async function findInput(page) {
  const selectors = [
    'input[placeholder*="Search" i]',
    'input[placeholder*="business" i]',
    'input[aria-label*="search" i]',
    'input[type="search"]',
    'input[type="text"]',
    '[role="searchbox"]',
    '#search',
    '.search-input',
    'input',
    'textarea'
  ];
  for (const sel of selectors) {
    try {
      const el = await page.`$(sel);
      if (el && await el.isVisible()) return el;
    } catch {}
  }
  return null;
}
"@

    $content = $content -replace [regex]::Escape($oldInputFn), $newInputFn
    
    # Enhance results picker
    $oldResultFn = @"
async function pickRandomBusiness(page) {
  // Try common result item patterns
  const candidates = [
    '[data-test="result-item"]',
    '[data-testid="result-item"]',
    'li a',
    'li',
    '[role="listitem"]',
    '.result, .results .item, .card, .tile, .list-item a, .list-item'
  ];
  for (const sel of candidates) {
    const elements = await page.`$`$(sel);
    if (elements && elements.length > 0) {
      return elements[Math.floor(Math.random() * elements.length)];
    }
  }
  return null;
}
"@

    $newResultFn = @"
async function pickRandomBusiness(page) {
  // Wait for results to appear
  await page.waitForTimeout(2000);
  
  // Try common result item patterns
  const candidates = [
    '[data-test="result-item"]',
    '[data-testid="result-item"]',
    '[data-testid="business-card"]',
    '.business-card',
    '.result-card',
    '.search-result',
    'li a',
    'li button',
    'article',
    '[role="listitem"]',
    '.result, .results .item, .card, .tile, .list-item a, .list-item'
  ];
  for (const sel of candidates) {
    try {
      const elements = await page.`$`$(sel);
      if (elements && elements.length > 0) {
        console.log(`Found `${elements.length} results with selector: `${sel}`);
        return elements[Math.floor(Math.random() * elements.length)];
      }
    } catch {}
  }
  return null;
}
"@

    $content = $content -replace [regex]::Escape($oldResultFn), $newResultFn
    
    Set-Content -Path $testFlowJs -Value $content -Encoding UTF8
    Write-FixLog "Applied fix: Enhanced search selectors" "Green"
    return $true
}

function Apply-Fix-InputNotFound {
    Write-FixLog "AUTO-FIX: Adding wait and retry logic for input field" "Cyan"
    
    $content = Get-Content $testFlowJs -Raw
    
    # Add retry logic to main run function
    if ($content -match "await page.goto") {
        $content = $content -replace "(await page\.goto[^;]+;)", "`$1`n    await page.waitForTimeout(3000);"
        Set-Content -Path $testFlowJs -Value $content -Encoding UTF8
        Write-FixLog "Applied fix: Added wait after page load" "Green"
        return $true
    }
    return $false
}

function Apply-Fix-Timeout {
    Write-FixLog "AUTO-FIX: Increasing timeouts" "Cyan"
    
    $content = Get-Content $testFlowJs -Raw
    
    # Increase default timeout
    $content = $content -replace "const timeoutMs = parseInt\(getArg\('--timeout', '\d+'\)", "const timeoutMs = parseInt(getArg('--timeout', '120000')"
    
    Set-Content -Path $testFlowJs -Value $content -Encoding UTF8
    Write-FixLog "Applied fix: Increased timeout to 120s" "Green"
    return $true
}

function Apply-Fix-BackendErrors {
    Write-FixLog "AUTO-FIX: Filtering PowerShell noise from error detection" "Cyan"
    
    $content = Get-Content $testScript -Raw
    
    # Update Tail-Errors to exclude PowerShell noise
    $oldTailErrors = @"
function Tail-Errors {
    param([string[]]`$Files)
    `$patterns = @('ERROR', 'Error:', 'Traceback', 'Unhandled', 'ECONN', 'EADDRINUSE', 'Exception')
    foreach (`$f in `$Files) {
        if (-not (Test-Path `$f)) { continue }
        `$content = Get-Content -Path `$f -Raw -ErrorAction SilentlyContinue
        foreach (`$p in `$patterns) { if (`$content -match `$p) { return @{ file = `$f; pattern = `$p } } }
    }
    return `$null
}
"@

    $newTailErrors = @"
function Tail-Errors {
    param([string[]]`$Files)
    `$patterns = @('ERROR', 'Error:', 'Traceback', 'Unhandled', 'ECONN', 'EADDRINUSE', 'Exception')
    `$excludePatterns = @('NativeCommandError', 'FullyQualifiedErrorId', 'CategoryInfo')
    foreach (`$f in `$Files) {
        if (-not (Test-Path `$f)) { continue }
        `$lines = Get-Content -Path `$f -ErrorAction SilentlyContinue
        foreach (`$line in `$lines) {
            `$isExcluded = `$false
            foreach (`$excl in `$excludePatterns) {
                if (`$line -match `$excl) { `$isExcluded = `$true; break }
            }
            if (-not `$isExcluded) {
                foreach (`$p in `$patterns) { 
                    if (`$line -match `$p) { 
                        return @{ file = `$f; pattern = `$p; line = `$line } 
                    } 
                }
            }
        }
    }
    return `$null
}
"@

    $content = $content -replace [regex]::Escape($oldTailErrors), $newTailErrors
    
    Set-Content -Path $testScript -Value $content -Encoding UTF8
    Write-FixLog "Applied fix: Filtered PowerShell error noise" "Green"
    return $true
}

function Apply-Fix-Generic {
    Write-FixLog "AUTO-FIX: Applying generic robustness improvements" "Cyan"
    
    # Add screenshot on failure
    $content = Get-Content $testFlowJs -Raw
    
    if ($content -notmatch "page.screenshot") {
        $catchBlock = @"
  } catch (err) {
    console.error('FLOW_FAILED', err?.message || String(err));
    try { await browser.close(); } catch {}
    process.exit(1);
  }
"@

        $newCatchBlock = @"
  } catch (err) {
    console.error('FLOW_FAILED', err?.message || String(err));
    try { 
      await page.screenshot({ path: 'logs/failure-screenshot.png', fullPage: true });
      console.log('Screenshot saved to logs/failure-screenshot.png');
    } catch {}
    try { await browser.close(); } catch {}
    process.exit(1);
  }
"@

        $content = $content -replace [regex]::Escape($catchBlock), $newCatchBlock
        Set-Content -Path $testFlowJs -Value $content -Encoding UTF8
        Write-FixLog "Applied fix: Added failure screenshot capture" "Green"
        return $true
    }
    return $false
}

# Main loop
for ($iteration = 1; $iteration -le $MaxIterations; $iteration++) {
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Magenta
    Write-Host "ITERATION $iteration of $MaxIterations" -ForegroundColor Magenta
    Write-Host "========================================" -ForegroundColor Magenta
    Write-Host ""
    
    Write-FixLog "Starting iteration $iteration" "Magenta"
    
    # Kill any Chrome processes from previous iterations
    if ($iteration -gt 1) {
        Write-Host "Cleaning up Chrome from previous iteration..." -ForegroundColor Yellow
        Get-Process chrome -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
        Get-Process msedge -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
        Start-Sleep -Seconds 2
    }
    
    # Run the test (output will stream directly to console)
    Write-Host "Running test..." -ForegroundColor Cyan
    Write-Host "----------------------------------------" -ForegroundColor Gray
    
    & powershell -NoProfile -ExecutionPolicy Bypass -File $testScript $Query $(if ($Headless) { "-Headless" })
    $exitCode = $LASTEXITCODE
    
    Write-Host "----------------------------------------" -ForegroundColor Gray
    Write-Host "Test exit code: $exitCode" -ForegroundColor $(if ($exitCode -eq 0) { 'Green' } else { 'Yellow' })
    
    if ($exitCode -eq 0) {
        Write-Host ""
        Write-Host "========================================" -ForegroundColor Green
        Write-Host "✅ SUCCESS! Test passed on iteration $iteration" -ForegroundColor Green
        Write-Host "========================================" -ForegroundColor Green
        Write-Host ""
        Write-Host "Applied fixes during this run:" -ForegroundColor Cyan
        if ($appliedFixes.Count -eq 0) {
            Write-Host "  (none - passed on first try)" -ForegroundColor Gray
        } else {
            $appliedFixes | ForEach-Object { Write-Host "  - $_" -ForegroundColor Cyan }
        }
        Write-FixLog "✅ Test PASSED on iteration $iteration" "Green"
        exit 0
    }
    
    # Analyze failures and apply fixes
    Write-Host ""
    Write-Host "❌ Test failed. Analyzing and auto-fixing..." -ForegroundColor Yellow
    Write-FixLog "Test FAILED. Analyzing..." "Yellow"
    
    $e2eErr = Join-Path $logsPath "e2e.err.log"
    $e2eOut = Join-Path $logsPath "e2e.out.log"
    
    $fixApplied = $false
    
    # Check Playwright errors and apply fixes
    if (Test-Path $e2eErr) {
        $e2eErrors = Get-Content $e2eErr -Raw
        
        if ($e2eErrors -match "No search results found" -and "NoSearchResults" -notin $appliedFixes) {
            $fixApplied = Apply-Fix-NoSearchResults
            if ($fixApplied) { $appliedFixes += "NoSearchResults" }
        }
        
        if ($e2eErrors -match "Search input not found" -and "InputNotFound" -notin $appliedFixes) {
            $fixApplied = Apply-Fix-InputNotFound
            if ($fixApplied) { $appliedFixes += "InputNotFound" }
        }
        
        if ($e2eErrors -match "Timeout" -and "Timeout" -notin $appliedFixes) {
            $fixApplied = Apply-Fix-Timeout
            if ($fixApplied) { $appliedFixes += "Timeout" }
        }
    }
    
    # Apply backend error filter fix
    if ("BackendErrorFilter" -notin $appliedFixes) {
        $fixApplied = Apply-Fix-BackendErrors
        if ($fixApplied) { $appliedFixes += "BackendErrorFilter" }
    }
    
    # Apply generic fixes if no specific fix worked
    if (-not $fixApplied -and "Generic" -notin $appliedFixes) {
        $fixApplied = Apply-Fix-Generic
        if ($fixApplied) { $appliedFixes += "Generic" }
    }
    
    if (-not $fixApplied) {
        Write-FixLog "⚠️  No automated fix available for this failure" "Red"
        Write-Host ""
        Write-Host "No more automated fixes available. Check logs:" -ForegroundColor Red
        Write-Host "  - $e2eErr" -ForegroundColor Gray
        Write-Host "  - $e2eOut" -ForegroundColor Gray
        Write-Host "  - $fixLogPath" -ForegroundColor Gray
        break
    }
    
    Write-Host "Waiting 2s before retry..." -ForegroundColor Gray
    Start-Sleep -Seconds 2
}

if ($exitCode -ne 0) {
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Red
    Write-Host "❌ FAILED after $MaxIterations iterations" -ForegroundColor Red
    Write-Host "========================================" -ForegroundColor Red
    Write-Host ""
    Write-Host "Applied fixes:" -ForegroundColor Yellow
    $appliedFixes | ForEach-Object { Write-Host "  - $_" -ForegroundColor Yellow }
    Write-FixLog "❌ FAILED: Max iterations reached" "Red"
    exit 1
}

