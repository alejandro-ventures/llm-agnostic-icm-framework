# file-organizer (human guide)

Two-phase, safe folder tidy: plan first, apply only on approval, never delete.

## Run manually
```bash
python scripts/plan_reorg.py input output/plan.csv   # phase 1: plan
python scripts/plan_reorg.py --apply output/plan.csv # phase 2: apply (after you review)
```
