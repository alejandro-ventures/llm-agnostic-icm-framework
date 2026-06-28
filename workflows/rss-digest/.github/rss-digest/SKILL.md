---
name: rss-digest
description: >-
  Read a list of public RSS/Atom feeds and produce a dated markdown digest of new
  items. Read-only against the network; writes only a local markdown file.
argument-hint: "A feeds list (defaults to references/feeds.example.md)"
---

# rss-digest

## Inputs
| Source | Location | Why |
|--------|----------|-----|
| Feed URLs | `references/feeds.example.md` | which public feeds to read |

## Process
1. Parse the feed list; fetch each public feed (read-only).
2. Collect items newer than the last run (state in `output/.last_run`).
3. Write `output/digest-<date>.md`.
4. Append a run-log line. (Emailing/sending is out of scope and left to the user.)

## Outputs
| Artifact | Location | Format |
|----------|----------|--------|
| Digest | `output/digest-<date>.md` | Markdown |

## Gates
- None: read-only on the network, writes a single local file. Sending is the user's manual step.

## Run log
Append `timestamp,rss-digest,digest,<n_items>` to `output/run-log.csv`.
