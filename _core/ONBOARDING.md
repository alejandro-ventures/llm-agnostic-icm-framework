# _core/ONBOARDING.md — Stand this up in ten minutes

1. **Clone** the repo and open the folder in VS Code.
2. **Install deps:** `pip install -r requirements.txt` (a virtual environment is recommended).
3. **Verify structure:** `python _core/scripts/health_check.py` — expect `GO`.
4. **Open Copilot Chat** (or any LLM coding assistant). It reads `.github/copilot-instructions.md`,
   which points it at `AGENTS.md`.
5. **Ask in plain English**, e.g. *"OCR the PDFs in workflows/ocr-folder/input."* The agent routes,
   reads the matching `SKILL.md`, and walks the stages, pausing at each human gate.
6. **Your data stays local.** Put inputs in a workflow's `input/`; results land in `output/`. Both are gitignored.
