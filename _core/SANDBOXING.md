# _core/SANDBOXING.md — isolation, honestly

Companion to `AGENTS.md` → Execution environments. This file separates two things that are easy
to conflate: **dependency isolation** (what a venv gives you) and **security sandboxing** (a real
boundary around what code can read, write, and send).

## The correction
A Python venv is NOT a security sandbox. It pins package versions so workflows don't fight over
dependencies. It does nothing to stop a script — buggy, malicious, or hijacked by a poisoned input
— from reading a sibling folder of business records and POSTing them to the internet. Code in a
venv runs with your full user account: your files, your network, your credentials. Treat the venv
as hygiene, not protection.

## Threat model for this workspace
This is a single-user workspace where AI assistants generate and run Python over potentially
sensitive material (contracts, financial records, identity documents). Realistic risks,
most-likely first:

1. **Accidental damage (most likely).** AI-generated code has a bug and writes/deletes outside
   the workspace. Without the guardrail below, this is prevented only by a prompt-level rule
   ("write only inside the workspace") — nothing technical enforces it.
2. **Supply-chain.** `pip install <ocr-stack> ...` pulls dozens of transitive packages from PyPI.
   A compromised or typosquatted package runs arbitrary code at install and at import time, with
   your privileges. A venv does not help here.
3. **Data exfiltration / prompt injection.** A script (buggy, a bad dependency, or instructions
   smuggled in via an OCR'd / processed document) sends sensitive data over the network. Any
   workflow that processes documents you did not author carries this vector.
4. **Cloud-model reads (by design).** Whatever a CLOUD model reads leaves the machine. No Python
   sandbox touches that — only the cloud-vs-local discipline and human gates do.

## Tiers (match the tier to trust + where you're running)
There is no single "sandbox everything" that works equally from the desktop AND from a
phone-remote session. So tier it.

### Tier 0 — always on, universal, cheap
- **venv** for dependency isolation.
- **In-script filesystem guardrail** (`_core/scripts/sandbox.py`): a tiny helper every workflow
  imports that resolves the workspace root and refuses to open/write paths outside it, and refuses
  to touch secret files. This converts the "write only inside the workspace" convention into
  *code*. It is a guardrail, not a jail (determined malicious code can bypass pure-Python checks),
  but it catches the dominant real risk — bugs and accidents — and works on every device,
  including remote sessions.
- **Human gates** (CONVENTIONS): the strongest control that works everywhere.

### Tier 1 — untrusted code or sensitive data, on a Windows desktop
- **Windows Sandbox** (built into Windows 11 Pro/Enterprise). A disposable, lightweight VM
  configured by a small `.wsb` XML file: map only the workspace (read-only or read-write), set
  `<Networking>Disable</Networking>` to cut exfiltration outright, and the whole VM is thrown
  away on close. Best fit for: a brand-new workflow, a new/unvetted pip dependency, or anything
  touching sensitive records. Trade-offs: it's a GUI VM (heavier to spin up per run), ephemeral
  (deps reinstall each session unless you map a cache folder), and not usable from a
  phone-remote flow.

### Tier 2 — reproducible / portable / shareable
- **Docker** per workflow: `--network none`, read-only bind mounts, `--memory`/`--cpus` caps,
  non-root user. The strongest reproducible box, and the natural next tier if you need CI-grade
  isolation. Trade-offs: needs Docker Desktop + WSL2 running, multi-GB, more setup, complicates
  cross-device sync; not available from a phone.

## Recommendation
- **Default everywhere:** Tier 0 — venv + the filesystem guardrail + human gates.
- **Before running anything unvetted, or touching sensitive business records on the desktop:**
  add Tier 1 (Windows Sandbox, networking disabled).
- **Tier 2 (Docker):** only if you want reproducible/CI isolation.

The biggest exfiltration risk here is not the Python — it's a cloud model reading sensitive files
and prompt injection through processed documents. Sandboxing the interpreter does not address
those; the cloud-vs-local discipline and human gates (CONVENTIONS) do. Keep both.

## Using the tiers

### Tier 0 — already wired in
- Each workflow has its own `.venv` (see `AGENTS.md` → Execution environments).
- The guardrail lives at `_core/scripts/sandbox.py`. Every workflow script imports it and routes
  its write destination through `sandbox.guard_write(...)`, which raises `SandboxError` on any path
  outside the workspace or any secret file. Self-test it any time: `python _core/scripts/sandbox.py`.
- New workflows get this for free if they follow the pattern: at the top of the script,
  `sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "_core" / "scripts")); import sandbox`,
  then wrap the output dir with `sandbox.guard_write(...)` and derive default paths from
  `sandbox.workflow_dir(__file__)`.

### Tier 1 — Windows Sandbox (on the desktop, for unvetted code or sensitive data)
1. Enable the feature once, in an **elevated** PowerShell, then reboot:
   `Enable-WindowsOptionalFeature -Online -FeatureName "Containers-DisposableClientVM" -All`
   (Windows 11 Pro/Enterprise only.)
2. Generate a config for a workflow (no admin needed):
   `powershell -ExecutionPolicy Bypass -File _core/scripts/new-sandbox.ps1 -Workflow <name>`
   Add `-Launch` to start it, or `-Network` to allow pip inside the VM (off by default).
3. The generated `workflows/<name>/.sandbox/run.wsb` maps **only** the workspace (read-write) plus
   the host Python (read-only, same path so the host `.venv` runs offline). Nothing outside the
   workspace is mapped, so sandboxed code cannot read your other folders even if it tries. With
   networking disabled (default), it also cannot exfiltrate.
4. Inside the VM, `enter.ps1` orients you and prints the offline run command.

**Caveat — cloud-drive virtual filesystems:** if the workspace lives on a cloud-synced virtual
filesystem, mapping that path into the VM may force-hydrate files or behave unevenly. If a run
misbehaves, point the sandbox at a plain local `git clone` of the repo instead.

### Tier 2 — Docker
Not built. Scaffold on request: per-workflow Dockerfile, run with `--network none`, `input/`
mounted read-only, `output/` read-write, non-root user.

## Status
- Tier 0 (venv + `sandbox.py` guardrail, wired into every example workflow): **done**.
- Tier 1 (`new-sandbox.ps1` launcher + generated `.wsb`/`enter.ps1`): **built**; requires the
  Windows Sandbox feature to be enabled (step 1) before first launch.
- Tier 2 (Docker): **not built** — on request.
