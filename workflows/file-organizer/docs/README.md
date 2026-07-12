# file-organizer (human guide)

Two-phase, safe folder tidy: plan first, apply only on approval, never delete. Apply
destinations are checked by `_core/scripts/sandbox.py` and cannot leave the workspace.

## Set up the venv (first time)
From this workflow folder (standard library only, so this is just the convention):

    python -m venv .venv
    .\.venv\Scripts\Activate.ps1        # Windows; macOS/Linux: source .venv/bin/activate
    pip install -r requirements.txt

## Run manually
```bash
python scripts/plan_reorg.py input output/plan.csv   # phase 1: plan
python scripts/plan_reorg.py --apply output/plan.csv # phase 2: apply (after you review)
```
