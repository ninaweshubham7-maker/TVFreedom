$ErrorActionPreference = "Continue"

$ProjectRoot = (Get-Location).Path
$Timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$ReportPath = Join-Path $ProjectRoot "tvfreedom_test_report_$Timestamp.txt"

function Write-Report($Message) {
    $Message | Tee-Object -FilePath $ReportPath -Append
}

Write-Report "TV FREEDOM TEST REPORT"
Write-Report "Date: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
Write-Report "Project: $ProjectRoot"
Write-Report ""

if (-not (Test-Path (Join-Path $ProjectRoot "app.py"))) {
    Write-Report "ERROR: app.py not found. Open the TVFreedom project folder in VS Code and run this script from that folder."
    exit 2
}

Write-Report "=== 1. Python version ==="
python --version 2>&1 | Tee-Object -FilePath $ReportPath -Append
Write-Report ""

Write-Report "=== 2. Compile Python files (syntax check) ==="
python -m compileall -q app.py
$CompileExit = $LASTEXITCODE
Write-Report "compileall exit code: $CompileExit"
if ($CompileExit -eq 0) { Write-Report "RESULT: PASS" } else { Write-Report "RESULT: FAIL" }
Write-Report ""

Write-Report "=== 3. Dependency check ==="
python -m pip check 2>&1 | Tee-Object -FilePath $ReportPath -Append
$PipCheckExit = $LASTEXITCODE
Write-Report "pip check exit code: $PipCheckExit"
if ($PipCheckExit -eq 0) { Write-Report "RESULT: PASS" } else { Write-Report "RESULT: FAIL (review dependency output)" }
Write-Report ""

Write-Report "=== 4. Existing pytest suite ==="
python -m pytest -q
$PytestExit = $LASTEXITCODE
Write-Report "pytest exit code: $PytestExit"
if ($PytestExit -eq 0) { Write-Report "RESULT: PASS" } else { Write-Report "RESULT: FAIL (see pytest output above)" }
Write-Report ""

Write-Report "=== SUMMARY ==="
Write-Report "Syntax check exit code: $CompileExit"
Write-Report "Dependency check exit code: $PipCheckExit"
Write-Report "Pytest exit code: $PytestExit"
Write-Report "Full report saved to: $ReportPath"

if ($CompileExit -ne 0 -or $PytestExit -ne 0) {
    exit 1
}
exit 0
