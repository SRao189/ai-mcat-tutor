<# 
Agent-loop orchestrator for a Codex implementation pass followed by Claude Code
review and final verification.

Expected task.json shape:

{
  "codexWorktree": "C:\\path\\to\\codex-worktree",
  "claudeWorktree": "C:\\path\\to\\claude-worktree",
  "task": "Implement ...",
  "tests": [
    "python -m tests.test_citations"
  ],
  "codexCommand": ["codex", "exec", "--cd", "{worktree}", "{promptFile}"],
  "claudeCommand": ["claude", "-p", "{prompt}"],
  "reviewOutput": "claude-review.json"
}

Command placeholders:
  {worktree}    absolute worktree path
  {promptFile}  generated prompt file path
  {prompt}      generated prompt text
  {round}       current round number

The script intentionally does not merge, force-push, or deploy.
#>

[CmdletBinding()]
param(
    [string]$TaskPath = "",
    [int]$MaxRounds = 2,
    [int]$TimeoutSeconds = 900,
    [switch]$SelfTest,
    [switch]$AllowDirtyAtStart
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
$ScriptRoot = if ([string]::IsNullOrEmpty($PSScriptRoot)) {
    Split-Path -Parent $MyInvocation.MyCommand.Path
} else {
    $PSScriptRoot
}

function Resolve-RepoPath {
    param([Parameter(Mandatory)] [string]$PathValue)
    $expanded = [Environment]::ExpandEnvironmentVariables($PathValue)
    return (Resolve-Path -LiteralPath $expanded).Path
}

function ConvertTo-StringArray {
    param([Parameter(Mandatory)] $Value)
    if ($Value -is [System.Array]) {
        return @($Value | ForEach-Object { [string]$_ })
    }
    if ($Value -is [string]) {
        return @("powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", $Value)
    }
    throw "Command must be a string or string array."
}

function Format-CommandArg {
    param(
        [Parameter(Mandatory)] [string]$Value,
        [Parameter(Mandatory)] [hashtable]$Vars
    )
    $result = $Value
    foreach ($key in $Vars.Keys) {
        $result = $result.Replace("{$key}", [string]$Vars[$key])
    }
    return $result
}

function Get-GitHead {
    param([Parameter(Mandatory)] [string]$Worktree)
    return (& git -C $Worktree rev-parse HEAD).Trim()
}

function Get-GitStatusLines {
    param([Parameter(Mandatory)] [string]$Worktree)
    return @(& git -C $Worktree status --porcelain)
}

function Join-CommandArguments {
    param([Parameter(Mandatory)] [string[]]$Arguments)
    return ($Arguments | ForEach-Object {
        if ($_ -notmatch '[\s"]') {
            return $_
        }
        $escaped = $_ -replace '(\\*)"', '$1$1\"'
        $escaped = $escaped -replace '(\\+)$', '$1$1'
        return '"' + $escaped + '"'
    }) -join " "
}

function Stop-ChildProcessTree {
    param([Parameter(Mandatory)] [System.Diagnostics.Process]$Process)
    if ($Process.HasExited) {
        return
    }

    try {
        $Process.Kill($true)
    } catch {
        $taskkill = Join-Path $env:SystemRoot "System32\taskkill.exe"
        if (Test-Path -LiteralPath $taskkill) {
            $oldErrorActionPreference = $ErrorActionPreference
            try {
                $ErrorActionPreference = "SilentlyContinue"
                & $taskkill /PID $Process.Id /T /F *> $null
            } catch {
            } finally {
                $ErrorActionPreference = $oldErrorActionPreference
            }
            [void]$Process.WaitForExit(1000)
        }
        if (-not $Process.HasExited) {
            $Process.Kill()
        }
    }
}

function Invoke-ChildProcess {
    param(
        [Parameter(Mandatory)] [string]$FilePath,
        [string[]]$Arguments = @(),
        [Parameter(Mandatory)] [string]$WorkingDirectory,
        [Parameter(Mandatory)] [int]$TimeoutSeconds
    )

    if ($TimeoutSeconds -le 0) {
        throw "TimeoutSeconds must be greater than zero."
    }

    $proc = New-Object System.Diagnostics.Process
    $timedOut = $false

    try {
        $proc.StartInfo.FileName = $FilePath
        $proc.StartInfo.WorkingDirectory = $WorkingDirectory
        $proc.StartInfo.UseShellExecute = $false
        $proc.StartInfo.RedirectStandardOutput = $true
        $proc.StartInfo.RedirectStandardError = $true
        $proc.StartInfo.RedirectStandardInput = $true
        $proc.StartInfo.CreateNoWindow = $true

        if ($proc.StartInfo.PSObject.Properties.Name -contains "ArgumentList") {
            foreach ($argument in $Arguments) {
                [void]$proc.StartInfo.ArgumentList.Add($argument)
            }
        } else {
            $proc.StartInfo.Arguments = Join-CommandArguments -Arguments $Arguments
        }

        [void]$proc.Start()
        # Send EOF immediately so CLIs do not wait on inherited non-TTY stdin.
        try { $proc.StandardInput.Close() } catch {}
        $stdoutTask = $proc.StandardOutput.ReadToEndAsync()
        $stderrTask = $proc.StandardError.ReadToEndAsync()

        $timeoutMs = [Math]::Min([int64][int]::MaxValue, [int64]$TimeoutSeconds * 1000L)
        if (-not $proc.WaitForExit([int]$timeoutMs)) {
            $timedOut = $true
            Stop-ChildProcessTree -Process $proc
            [void]$proc.WaitForExit(10000)
        }

        if (-not $timedOut) {
            $proc.WaitForExit()
        }
        [void][System.Threading.Tasks.Task]::WaitAll(@($stdoutTask, $stderrTask), 10000)

        $output = New-Object System.Text.StringBuilder
        if ($stdoutTask.IsCompleted) {
            [void]$output.Append($stdoutTask.Result)
        }
        if ($stderrTask.IsCompleted) {
            [void]$output.Append($stderrTask.Result)
        }
        $exitCode = if ($timedOut) { -1 } else { $proc.ExitCode }

        return [ordered]@{
            exitCode = $exitCode
            timedOut = $timedOut
            output = $output.ToString()
        }
    } finally {
        if ($null -ne $proc) {
            try {
                if (-not $proc.HasExited) {
                    Stop-ChildProcessTree -Process $proc
                }
            } catch {
            }
            $proc.Dispose()
        }
    }
}

function Assert-CleanWorktree {
    param(
        [Parameter(Mandatory)] [string]$Worktree,
        [Parameter(Mandatory)] [string]$Label
    )
    $status = @(Get-GitStatusLines -Worktree $Worktree)
    if ($status.Count -gt 0) {
        $preview = ($status | Select-Object -First 20) -join [Environment]::NewLine
        throw "$Label worktree is not clean: $Worktree`n$preview"
    }
}

function Invoke-LoggedCommand {
    param(
        [Parameter(Mandatory)] [string[]]$CommandSpec,
        [Parameter(Mandatory)] [string]$Worktree,
        [Parameter(Mandatory)] [string]$LogPath,
        [Parameter(Mandatory)] [hashtable]$Vars,
        [Parameter(Mandatory)] [int]$TimeoutSeconds
    )
    $expanded = @($CommandSpec | ForEach-Object { Format-CommandArg -Value $_ -Vars $Vars })
    if ($expanded.Count -eq 0) {
        throw "Empty command."
    }

    $exe = $expanded[0]
    $arguments = @()
    if ($expanded.Count -gt 1) {
        $arguments = $expanded[1..($expanded.Count - 1)]
    }

    $parent = Split-Path -Parent $LogPath
    New-Item -ItemType Directory -Force -Path $parent | Out-Null

    $result = Invoke-ChildProcess -FilePath $exe -Arguments $arguments -WorkingDirectory $Worktree -TimeoutSeconds $TimeoutSeconds
    $result.output | Set-Content -LiteralPath $LogPath -Encoding UTF8
    if ($result.timedOut) {
        throw "Command timed out after $TimeoutSeconds seconds. See $LogPath"
    }
    $exitCode = [int]$result.exitCode
    if ($exitCode -ne 0) {
        throw "Command failed with exit code $exitCode. See $LogPath"
    }
}

function Invoke-TestCommands {
    param(
        [Parameter(Mandatory)] [string]$Worktree,
        [Parameter(Mandatory)] [array]$Tests,
        [Parameter(Mandatory)] [string]$LogPath,
        [Parameter(Mandatory)] [int]$TimeoutSeconds
    )
    $parent = Split-Path -Parent $LogPath
    New-Item -ItemType Directory -Force -Path $parent | Out-Null
    $lines = New-Object System.Collections.Generic.List[string]
    $failed = New-Object System.Collections.Generic.List[string]

    foreach ($test in $Tests) {
        $command = [string]$test
        $lines.Add(">>> $command")
        $result = Invoke-ChildProcess -FilePath "powershell" -Arguments @("-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", $command) -WorkingDirectory $Worktree -TimeoutSeconds $TimeoutSeconds
        $result.output -split "\r?\n" | Where-Object { $_ -ne "" } | ForEach-Object { $lines.Add([string]$_) }
        if ($result.timedOut) {
            $lines.Add("timed_out=true")
        }
        $exitCode = [int]$result.exitCode
        $lines.Add("exit_code=$exitCode")
        if ($result.timedOut -or $exitCode -ne 0) {
            $failed.Add($command)
        }
    }

    $lines.Add("overall_success=$($failed.Count -eq 0)")
    if ($failed.Count -gt 0) {
        $lines.Add("failed_commands:")
        $failed | ForEach-Object { $lines.Add("- $_") }
    }
    $lines | Set-Content -LiteralPath $LogPath -Encoding UTF8
    return [ordered]@{
        success = ($failed.Count -eq 0)
        failedCommands = @($failed)
    }
}

function Assert-SelfTest {
    param(
        [Parameter(Mandatory)] [bool]$Condition,
        [Parameter(Mandatory)] [string]$Message
    )
    if (-not $Condition) {
        throw "Self-test failed: $Message"
    }
}

function Invoke-SelfTest {
    $tempRoot = Join-Path ([System.IO.Path]::GetTempPath()) ("orchestrator-selftest-" + [guid]::NewGuid().ToString("N"))
    New-Item -ItemType Directory -Force -Path $tempRoot | Out-Null
    try {
        $logPath = Join-Path $tempRoot "child.log"
        $scratchPath = Join-Path $tempRoot "scratch.txt"

        $capture = Invoke-ChildProcess -FilePath "powershell" -Arguments @("-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", "Write-Output 'selftest-output'") -WorkingDirectory $tempRoot -TimeoutSeconds 10
        $capture.output | Set-Content -LiteralPath $logPath -Encoding UTF8
        Assert-SelfTest -Condition (-not $capture.timedOut) -Message "capture command timed out"
        Assert-SelfTest -Condition ([int]$capture.exitCode -eq 0) -Message "capture command exit code was $($capture.exitCode)"
        Assert-SelfTest -Condition ($capture.output -match "selftest-output") -Message "capture command output was not captured"

        "rewrite-ok" | Set-Content -LiteralPath $logPath -Encoding UTF8
        "scratch-ok" | Set-Content -LiteralPath $scratchPath -Encoding UTF8
        Remove-Item -LiteralPath $logPath -Force
        Remove-Item -LiteralPath $scratchPath -Force
        Assert-SelfTest -Condition (-not (Test-Path -LiteralPath $logPath)) -Message "log file remained locked"
        Assert-SelfTest -Condition (-not (Test-Path -LiteralPath $scratchPath)) -Message "scratch file remained locked"

        $timeout = Invoke-ChildProcess -FilePath "powershell" -Arguments @("-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", "Start-Sleep -Seconds 30") -WorkingDirectory $tempRoot -TimeoutSeconds 1
        Assert-SelfTest -Condition ([bool]$timeout.timedOut) -Message "sleeping child was not marked timed out"
        Assert-SelfTest -Condition ([int]$timeout.exitCode -eq -1) -Message "timed-out child exit code was $($timeout.exitCode)"

        Write-Host "SELFTEST capture=passed"
        Write-Host "SELFTEST lock_regression=passed"
        Write-Host "SELFTEST timeout=passed"
    } finally {
        Remove-Item -LiteralPath $tempRoot -Recurse -Force -ErrorAction SilentlyContinue
    }
}

function Read-ClaudeReview {
    param([Parameter(Mandatory)] [string]$ReviewPath)
    if (-not (Test-Path -LiteralPath $ReviewPath)) {
        throw "Claude review file not found: $ReviewPath"
    }
    $json = Get-Content -LiteralPath $ReviewPath -Raw -Encoding UTF8 | ConvertFrom-Json
    if (-not ($json.PSObject.Properties.Name -contains "changes_required")) {
        throw "Claude review JSON must contain changes_required."
    }
    return $json
}

function New-CodexPrompt {
    param(
        [Parameter(Mandatory)] $Task,
        [Parameter(Mandatory)] [int]$Round,
        $Review = $null
    )
    $base = @"
You are Codex running non-interactively in an agent loop.

Round: $Round

Task:
$($Task.task)

Constraints:
- Work only in the configured Codex worktree.
- Do not deploy.
- Do not expose secrets.
- Run the relevant tests or leave exact commands for the orchestrator.
- Commit your changes if the task is complete.
"@

    if ($null -ne $Review) {
        $reviewText = $Review | ConvertTo-Json -Depth 12
        $base += @"

Claude review requiring changes:
$reviewText

Address only the requested changes, rerun relevant tests, and commit the fix.
"@
    }
    return $base
}

function New-ClaudeReviewPrompt {
    param(
        [Parameter(Mandatory)] $Task,
        [Parameter(Mandatory)] [int]$Round,
        [Parameter(Mandatory)] [string]$CodexCommit,
        [Parameter(Mandatory)] [string]$TestLog,
        [Parameter(Mandatory)] $TestResult,
        [Parameter(Mandatory)] [string]$ReviewOutput
    )
    $testResultJson = $TestResult | ConvertTo-Json -Depth 8
    return @"
You are Claude Code running non-interactively as an independent reviewer.

Review the Codex implementation for this task:
$($Task.task)

Codex commit:
$CodexCommit

Test log path:
$TestLog

Test result summary:
$testResultJson

Do not modify code.

Write JSON only to:
$ReviewOutput

Required JSON shape:
{
  "changes_required": true,
  "blockers": [
    {"file": "...", "line": 1, "issue": "...", "required_change": "..."}
  ],
  "non_blocking": [],
  "verified_strengths": [],
  "tests_reviewed": [],
  "recommendation": "approve|reject"
}

Set changes_required to false only when the implementation should be accepted.
"@
}

function New-ClaudeFinalPrompt {
    param(
        [Parameter(Mandatory)] $Task,
        [Parameter(Mandatory)] [string]$CodexCommit,
        [Parameter(Mandatory)] [string]$ReviewOutput
    )
    return @"
You are Claude Code running final verification.

Task:
$($Task.task)

Final Codex commit:
$CodexCommit

Do not modify code.

Verify the implementation and write final JSON only to:
$ReviewOutput

Required JSON shape:
{
  "changes_required": false,
  "blockers": [],
  "non_blocking": [],
  "verified_strengths": [],
  "tests_reviewed": [],
  "recommendation": "approve|reject"
}
"@
}

if ($SelfTest) {
    Invoke-SelfTest
    return
}

if ([string]::IsNullOrWhiteSpace($TaskPath)) {
    $TaskPath = Join-Path $ScriptRoot "task.json"
}

if (-not (Test-Path -LiteralPath $TaskPath)) {
    throw "Task file not found: $TaskPath"
}

$task = Get-Content -LiteralPath $TaskPath -Raw -Encoding UTF8 | ConvertFrom-Json
$codexWorktree = Resolve-RepoPath $task.codexWorktree
$claudeWorktreeValue = if ($task.PSObject.Properties.Name -contains "claudeWorktree") {
    [string]$task.claudeWorktree
} else {
    [string]$task.codexWorktree
}
$claudeWorktree = Resolve-RepoPath $claudeWorktreeValue
$tests = @()
if ($task.PSObject.Properties.Name -contains "tests") {
    $tests = @($task.tests)
}

$codexCommand = if ($task.PSObject.Properties.Name -contains "codexCommand") {
    ConvertTo-StringArray $task.codexCommand
} else {
    @("codex", "exec", "--cd", "{worktree}", "{promptFile}")
}

$claudeCommand = if ($task.PSObject.Properties.Name -contains "claudeCommand") {
    ConvertTo-StringArray $task.claudeCommand
} else {
    @("claude", "-p", "{prompt}")
}

$reviewFileName = if ($task.PSObject.Properties.Name -contains "reviewOutput") {
    [string]$task.reviewOutput
} else {
    "claude-review.json"
}

$runRoot = Join-Path $ScriptRoot ("runs\" + (Get-Date -Format "yyyyMMdd-HHmmss"))
New-Item -ItemType Directory -Force -Path $runRoot | Out-Null

if (-not $AllowDirtyAtStart) {
    Assert-CleanWorktree -Worktree $codexWorktree -Label "Codex"
    Assert-CleanWorktree -Worktree $claudeWorktree -Label "Claude"
}

$summary = [ordered]@{
    startedAt = (Get-Date).ToString("o")
    codexWorktree = $codexWorktree
    claudeWorktree = $claudeWorktree
    rounds = @()
    finalRecommendation = $null
}

$review = $null
$finalCodexCommit = $null

for ($round = 1; $round -le $MaxRounds; $round++) {
    Assert-CleanWorktree -Worktree $codexWorktree -Label "Codex"
    Assert-CleanWorktree -Worktree $claudeWorktree -Label "Claude"

    $roundDir = Join-Path $runRoot ("round-$round")
    New-Item -ItemType Directory -Force -Path $roundDir | Out-Null

    $codexPrompt = New-CodexPrompt -Task $task -Round $round -Review $review
    $codexPromptFile = Join-Path $roundDir "codex-prompt.md"
    $codexPrompt | Set-Content -LiteralPath $codexPromptFile -Encoding UTF8
    $codexLog = Join-Path $roundDir "codex.log"

    $before = Get-GitHead -Worktree $codexWorktree
    Invoke-LoggedCommand -CommandSpec $codexCommand -Worktree $codexWorktree -LogPath $codexLog -Vars @{
        worktree = $codexWorktree
        promptFile = $codexPromptFile
        prompt = $codexPrompt
        round = $round
    } -TimeoutSeconds $TimeoutSeconds
    $after = Get-GitHead -Worktree $codexWorktree
    $finalCodexCommit = $after

    if ($before -eq $after) {
        throw "Codex did not create a new commit in round $round."
    }
    Assert-CleanWorktree -Worktree $codexWorktree -Label "Codex"

    $testLog = Join-Path $roundDir "tests.log"
    if ($tests.Count -gt 0) {
        $testResult = Invoke-TestCommands -Worktree $codexWorktree -Tests $tests -LogPath $testLog -TimeoutSeconds $TimeoutSeconds
    } else {
        "No tests configured in task.json." | Set-Content -LiteralPath $testLog -Encoding UTF8
        $testResult = [ordered]@{
            success = $true
            failedCommands = @()
        }
    }

    $reviewPath = Join-Path $roundDir $reviewFileName
    $claudePrompt = New-ClaudeReviewPrompt -Task $task -Round $round -CodexCommit $after -TestLog $testLog -TestResult $testResult -ReviewOutput $reviewPath
    $claudePromptFile = Join-Path $roundDir "claude-review-prompt.md"
    $claudePrompt | Set-Content -LiteralPath $claudePromptFile -Encoding UTF8
    $claudeLog = Join-Path $roundDir "claude-review.log"

    Invoke-LoggedCommand -CommandSpec $claudeCommand -Worktree $claudeWorktree -LogPath $claudeLog -Vars @{
        worktree = $claudeWorktree
        promptFile = $claudePromptFile
        prompt = $claudePrompt
        round = $round
    } -TimeoutSeconds $TimeoutSeconds
    Assert-CleanWorktree -Worktree $claudeWorktree -Label "Claude"

    $review = Read-ClaudeReview -ReviewPath $reviewPath
    $summary.rounds += [ordered]@{
        round = $round
        codexCommit = $after
        testLog = $testLog
        testsPassed = [bool]$testResult.success
        reviewPath = $reviewPath
        changesRequired = [bool]$review.changes_required
    }

    if (-not [bool]$review.changes_required) {
        break
    }

    if ($round -eq $MaxRounds) {
        throw "Claude still requires changes after $MaxRounds rounds. See $reviewPath"
    }
}

Assert-CleanWorktree -Worktree $codexWorktree -Label "Codex"
Assert-CleanWorktree -Worktree $claudeWorktree -Label "Claude"

$finalDir = Join-Path $runRoot "final"
New-Item -ItemType Directory -Force -Path $finalDir | Out-Null
$finalReviewPath = Join-Path $finalDir $reviewFileName
$finalPrompt = New-ClaudeFinalPrompt -Task $task -CodexCommit $finalCodexCommit -ReviewOutput $finalReviewPath
$finalPromptFile = Join-Path $finalDir "claude-final-prompt.md"
$finalPrompt | Set-Content -LiteralPath $finalPromptFile -Encoding UTF8
$finalLog = Join-Path $finalDir "claude-final.log"

Invoke-LoggedCommand -CommandSpec $claudeCommand -Worktree $claudeWorktree -LogPath $finalLog -Vars @{
    worktree = $claudeWorktree
    promptFile = $finalPromptFile
    prompt = $finalPrompt
    round = "final"
} -TimeoutSeconds $TimeoutSeconds

$finalReview = Read-ClaudeReview -ReviewPath $finalReviewPath
$summary.finalReviewPath = $finalReviewPath
$summary.finalRecommendation = $finalReview.recommendation
$summary.finishedAt = (Get-Date).ToString("o")

$summaryPath = Join-Path $runRoot "summary.json"
$summary | ConvertTo-Json -Depth 12 | Set-Content -LiteralPath $summaryPath -Encoding UTF8

Write-Host "Agent loop complete."
Write-Host "Summary: $summaryPath"
Write-Host "Final recommendation: $($summary.finalRecommendation)"

if ([string]$summary.finalRecommendation -eq "reject") {
    throw "Final Claude verification rejected the implementation. See $finalReviewPath"
}
