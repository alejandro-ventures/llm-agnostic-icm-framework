[CmdletBinding()]
param(
    [ValidateSet('Preview', 'Install', 'Uninstall')]
    [string]$Mode = 'Preview',
    [switch]$Approved
)

$ErrorActionPreference = 'Stop'
$TaskName = 'AI Workflows - recurrence-review'
$WorkflowRoot = Split-Path -Parent $PSScriptRoot
$WorkspaceRoot = Split-Path -Parent (Split-Path -Parent $WorkflowRoot)
$Python = Join-Path $WorkflowRoot '.venv\Scripts\python.exe'
$ReviewScript = Join-Path $PSScriptRoot 'review.py'
$Arguments = '"' + $ReviewScript + '" scan'

if ($Mode -eq 'Preview') {
    [pscustomobject]@{
        TaskName = $TaskName
        Schedule = 'Every Monday at 09:00 local time'
        TimeZone = (Get-TimeZone).Id
        Execute = $Python
        Arguments = $Arguments
        WorkingDirectory = $WorkspaceRoot
        StateChange = 'None (preview only)'
    } | Format-List
    exit 0
}

if (-not $Approved) {
    throw "$Mode changes Windows Task Scheduler. Re-run only after explicit approval with -Approved."
}

if ($Mode -eq 'Uninstall') {
    $Existing = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
    if (-not $Existing) {
        Write-Host "Task is not installed: $TaskName"
        exit 0
    }
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
    Write-Host "Uninstalled: $TaskName"
    exit 0
}

if (-not (Test-Path -LiteralPath $Python -PathType Leaf)) {
    throw "Missing workflow venv Python: $Python. Create the venv before installing the task."
}
if (-not (Test-Path -LiteralPath $ReviewScript -PathType Leaf)) {
    throw "Missing review script: $ReviewScript"
}
if (Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue) {
    throw "Task already exists. This installer will not overwrite it: $TaskName"
}

$Action = New-ScheduledTaskAction -Execute $Python -Argument $Arguments -WorkingDirectory $WorkspaceRoot
$Trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Monday -At 9am
$Settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -MultipleInstances IgnoreNew
Register-ScheduledTask -TaskName $TaskName -Action $Action -Trigger $Trigger -Settings $Settings `
    -Description 'Review recurring scratch inquiries and write human-gated workflow proposals.' | Out-Null
Write-Host "Installed: $TaskName"
