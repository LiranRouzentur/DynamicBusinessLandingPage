Param(
    [Parameter(Mandatory=$true)] [string]$Name,
    [Parameter(Mandatory=$true)] [string]$Command,
    [string[]]$Args = @(),
    [string]$WorkingDirectory = (Get-Location).Path,
    [string]$LogDirectory = (Join-Path (Split-Path -Parent $PSScriptRoot) "logs"),
    [switch]$NewWindow
)

if (-not (Test-Path $LogDirectory)) {
    New-Item -ItemType Directory -Path $LogDirectory | Out-Null
}
$logPath = Join-Path $LogDirectory ("{0}.log" -f $Name)
Set-Content -Path $logPath -Value "" -Encoding UTF8

if ($NewWindow) {
    $windowTitle = "${Name} (logged)"
    $argLine = ($Args | ForEach-Object { if ($_ -match ' ') { '"' + $_ + '"' } else { $_ } }) -join ' '
    # Mirror console output to file with UTF-8 to avoid NUL bytes and encoding errors
    $psCmd = "-NoExit -Command `$host.UI.RawUI.WindowTitle = '$windowTitle'; cd '$WorkingDirectory'; [Console]::OutputEncoding = New-Object System.Text.UTF8Encoding `$false; [Console]::InputEncoding = New-Object System.Text.UTF8Encoding `$false; `$env:PYTHONUNBUFFERED='1'; `$env:PYTHONIOENCODING='utf-8'; & '$Command' $argLine 2>&1 | ForEach-Object { `"`$_`"; `"`$_`" | Out-File -FilePath '$logPath' -Append -Encoding utf8 }"
    Start-Process powershell -ArgumentList $psCmd | Out-Null
} else {
    Push-Location $WorkingDirectory
    try {
        $env:PYTHONUNBUFFERED = '1'
        $env:PYTHONIOENCODING = 'utf-8'
        [Console]::OutputEncoding = New-Object System.Text.UTF8Encoding $false
        [Console]::InputEncoding = New-Object System.Text.UTF8Encoding $false
        & $Command @Args 2>&1 | ForEach-Object { "$_"; "$_" | Out-File -FilePath $logPath -Append -Encoding utf8 }
    } finally {
        Pop-Location
    }
}

