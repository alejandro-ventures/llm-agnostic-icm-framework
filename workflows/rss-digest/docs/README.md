# rss-digest (human guide)

Turns public RSS/Atom feeds into a dated markdown digest. Read-only on the network.

## Set up the venv (first time)
From this workflow folder:

    python -m venv .venv
    .\.venv\Scripts\Activate.ps1        # Windows; macOS/Linux: source .venv/bin/activate
    pip install -r requirements.txt

## Run manually
```bash
python scripts/build_digest.py references/feeds.example.md output
```
