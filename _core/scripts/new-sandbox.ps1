<#
.SYNOPSIS
  Generate (and optionally launch) a Windows Sandbox config for one workflow.
  Tier 1 isolation — see _core/SANDBOXING.md.

.DESCRIPTION
  Runs a workflow inside a disposable Windows Sandbox VM that:
    * Maps ONLY this workspace (read-write). Nothing else on the host — no sibling
      folders of sensitive business records — is mapped, so code inside the VM
      physically cannot read them.
    * Maps the host Python install (read-only) at its real path, so the per-workflow
      .venv created on the host works inside the VM with no install and no network.
    * Disables networking by default (zero exfiltration). Pass -Network to allow pip.

  Windows Sandbox has no Python preinstalled and resets on close. The mapped host Python
  + host .venv lets a vetted workflow run fully offline. To install NEW dependencies you
  need -Network (then create a VM-local venv as enter.ps1 explains).

  Generated files (.sandbox/run.wsb + enter.ps1) contain absolute host paths and are
  gitignored — regenerate per machine.

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File _core/scripts/new-sandbox.ps1 -Workflow ocr-folder -Launch
  powershell -ExecutionPolicy Bypass -File _core/scripts/new-sandbox.ps1 -Workflow file-organizer -Network
#>
[CmdletBinding()]
param(
  [Parameter(Mandatory = $true)][string]$Workflow,
  [switch]$Network,                                   # allow networking inside the VM (needed for pip)
  [switch]$Launch,                                    # launch the sandbox after generating the .wsb
  [string]$PythonHome = "C:\Program Files\Python310"  # host Python, mapped read-only at this same path
)

$ErrorActionPreference = "Stop"

$root = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path   # _core/scripts/ -> workspace root
$wf   = Join-Path $root "workflows\$Workflow"
if (-not (Test-Path $wf))         { throw "No such workflow: $wf" }
if (-not (Test-Path $PythonHome)) { Write-Warning "Python not found at $PythonHome - pass -PythonHome <path> or run with -Network to install inside the VM." }

$leaf      = Split-Path $root -Leaf            # workspace folder name
$vmWs      = "C:\Sandbox\$leaf"                # where the workspace appears inside the VM
$vmWf      = "$vmWs\workflows\$Workflow"
$net       = if ($Network) { "Default" } else { "Disable" }
$scripts   = (Get-ChildItem (Join-Path $wf "scripts") -Filter *.py -ErrorAction SilentlyContinue | ForEach-Object { $_.Name }) -join ", "
if (-not $scripts) { $scripts = "(none found)" }

$outDir = Join-Path $wf ".sandbox"
New-Item -ItemType Directory -Force -Path $outDir | Out-Null

# enter.ps1 runs inside the VM at logon: orient the user, prefer the offline host venv.
$enter = @"
`$ErrorActionPreference = 'Stop'
Set-Location '$vmWf'
Write-Host '=== Windows Sandbox: $Workflow ===' -ForegroundColor Cyan
Write-Host 'Workspace mapped read-write at $vmWs.'
Write-Host 'Nothing outside the workspace is mapped - the rest of the host is invisible in here.'
Write-Host 'Networking: $net.'
Write-Host ''
`$venvPy = Join-Path '$vmWf' '.venv\Scripts\python.exe'
if (Test-Path `$venvPy) {
  Write-Host 'Host venv found. Run a script OFFLINE with:' -ForegroundColor Green
  Write-Host ('  & "' + `$venvPy + '" scripts\<script>.py')
} else {
  Write-Host 'No .venv present here. With -Network on, build a VM-local one:' -ForegroundColor Yellow
  Write-Host '  python -m venv C:\wfvenv; C:\wfvenv\Scripts\Activate.ps1; pip install -r requirements.txt'
  Write-Host '  C:\wfvenv\Scripts\python.exe scripts\<script>.py'
}
Write-Host ''
Write-Host 'Scripts available: $scripts'
"@
$enterPath = Join-Path $outDir "enter.ps1"
$enter | Out-File -FilePath $enterPath -Encoding utf8

# run.wsb: the disposable-VM configuration.
$wsb = @"
<Configuration>
  <Networking>$net</Networking>
  <MappedFolders>
    <MappedFolder>
      <HostFolder>$root</HostFolder>
      <SandboxFolder>$vmWs</SandboxFolder>
      <ReadOnly>false</ReadOnly>
    </MappedFolder>
    <MappedFolder>
      <HostFolder>$PythonHome</HostFolder>
      <SandboxFolder>$PythonHome</SandboxFolder>
      <ReadOnly>true</ReadOnly>
    </MappedFolder>
  </MappedFolders>
  <LogonCommand>
    <Command>powershell.exe -NoExit -ExecutionPolicy Bypass -File "$vmWf\.sandbox\enter.ps1"</Command>
  </LogonCommand>
  <ClipboardRedirection>true</ClipboardRedirection>
  <ProtectedClient>true</ProtectedClient>
  <MemoryInMB>4096</MemoryInMB>
</Configuration>
"@
$wsbPath = Join-Path $outDir "run.wsb"
$wsb | Out-File -FilePath $wsbPath -Encoding utf8

Write-Host "Wrote $wsbPath  (networking: $net)"
Write-Host "Wrote $enterPath"

if ($Launch) {
  $exe = "$env:WINDIR\System32\WindowsSandbox.exe"
  if (-not (Test-Path $exe)) {
    throw "Windows Sandbox is not enabled. Enable it once (elevated PowerShell), then reboot:`n  Enable-WindowsOptionalFeature -Online -FeatureName 'Containers-DisposableClientVM' -All"
  }
  & $exe $wsbPath
} else {
  Write-Host "Review it, then launch with:  WindowsSandbox.exe `"$wsbPath`"   (or re-run with -Launch)"
}
