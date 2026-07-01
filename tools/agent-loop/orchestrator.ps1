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
    [string]$TaskPath = (Join-Path $PSScriptRoot "task.json"),
    [int]$MaxRounds = 2,
    [switch]$AllowDirtyAtStart
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

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

function Assert-CleanWorktree {
    param(
        [Parameter(Mandatory)] [string]$Worktree,
        [Parameter(Mandatory)] [string]$Label
    )
    $status = Get-GitStatusLines -Worktree $Worktree
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
        [Parameter(Mandatory)] [hashtable]$Vars
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

    Push-Location -LiteralPath $Worktree
    try {
        $output = & $exe @arguments 2>&1
        $exitCode = $LASTEXITCODE
    } finally {
        Pop-Location
    }
    $output | Set-Content -LiteralPath $LogPath -Encoding UTF8
    if ($exitCode -ne 0) {
        throw "Command failed with exit code $exitCode. See $LogPath"
    }
}

function Invoke-TestCommands {
    param(
        [Parameter(Mandatory)] [string]$Worktree,
        [Parameter(Mandatory)] [array]$Tests,
        [Parameter(Mandatory)] [string]$LogPath
    )
    $parent = Split-Path -Parent $LogPath
    New-Item -ItemType Directory -Force -Path $parent | Out-Null
    $lines = New-Object System.Collections.Generic.List[string]

    foreach ($test in $Tests) {
        $command = [string]$test
        $lines.Add(">>> $command")
        Push-Location -LiteralPath $Worktree
        try {
            $output = & powershell -NoProfile -ExecutionPolicy Bypass -Command $command 2>&1
            $exitCode = $LASTEXITCODE
        } finally {
            Pop-Location
        }
        $output | ForEach-Object { $lines.Add([string]$_) }
        $lines.Add("exit_code=$exitCode")
        if ($exitCode -ne 0) {
            $lines | Set-Content -LiteralPath $LogPath -Encoding UTF8
            throw "Test command failed: $command. See $LogPath"
        }
    }

    $lines | Set-Content -LiteralPath $LogPath -Encoding UTF8
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
        [Parameter(Mandatory)] [string]$ReviewOutput
    )
    return @"
You are Claude Code running non-interactively as an independent reviewer.

Review the Codex implementation for this task:
$($Task.task)

Codex commit:
$CodexCommit

Test log path:
$TestLog

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

if (-not (Test-Path -LiteralPath $TaskPath)) {
    throw "Task file not found: $TaskPath"
}

$task = Get-Content -LiteralPath $TaskPath -Raw -Encoding UTF8 | ConvertFrom-Json
$codexWorktree = Resolve-RepoPath $task.codexWorktree
$claudeWorktree = Resolve-RepoPath $task.claudeWorktree
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

$runRoot = Join-Path $PSScriptRoot ("runs\" + (Get-Date -Format "yyyyMMdd-HHmmss"))
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
    }
    $after = Get-GitHead -Worktree $codexWorktree
    $finalCodexCommit = $after

    if ($before -eq $after) {
        throw "Codex did not create a new commit in round $round."
    }
    Assert-CleanWorktree -Worktree $codexWorktree -Label "Codex"

    $testLog = Join-Path $roundDir "tests.log"
    if ($tests.Count -gt 0) {
        Invoke-TestCommands -Worktree $codexWorktree -Tests $tests -LogPath $testLog
    } else {
        "No tests configured in task.json." | Set-Content -LiteralPath $testLog -Encoding UTF8
    }

    $reviewPath = Join-Path $roundDir $reviewFileName
    $claudePrompt = New-ClaudeReviewPrompt -Task $task -Round $round -CodexCommit $after -TestLog $testLog -ReviewOutput $reviewPath
    $claudePromptFile = Join-Path $roundDir "claude-review-prompt.md"
    $claudePrompt | Set-Content -LiteralPath $claudePromptFile -Encoding UTF8
    $claudeLog = Join-Path $roundDir "claude-review.log"

    Invoke-LoggedCommand -CommandSpec $claudeCommand -Worktree $claudeWorktree -LogPath $claudeLog -Vars @{
        worktree = $claudeWorktree
        promptFile = $claudePromptFile
        prompt = $claudePrompt
        round = $round
    }
    Assert-CleanWorktree -Worktree $claudeWorktree -Label "Claude"

    $review = Read-ClaudeReview -ReviewPath $reviewPath
    $summary.rounds += [ordered]@{
        round = $round
        codexCommit = $after
        testLog = $testLog
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
}

$finalReview = Read-ClaudeReview -ReviewPath $finalReviewPath
$summary.finalReviewPath = $finalReviewPath
$summary.finalRecommendation = $finalReview.recommendation
$summary.finishedAt = (Get-Date).ToString("o")

$summaryPath = Join-Path $runRoot "summary.json"
$summary | ConvertTo-Json -Depth 12 | Set-Content -LiteralPath $summaryPath -Encoding UTF8

Write-Host "Agent loop complete."
Write-Host "Summary: $summaryPath"
Write-Host "Final recommendation: $($summary.finalRecommendation)"
