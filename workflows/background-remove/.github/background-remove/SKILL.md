---
name: background-remove
description: >-
  Remove backgrounds from portrait and general images, outputting PNGs with transparent backgrounds.
argument-hint: "Folder of images (default workflows/background-remove/input)"
network: none after the one-time model download (~50 MB into ~/.u2net)
destructive: none — overwriting an existing output requires the gate
gates: ["overwriting any existing output (--force)"]
---
# background-remove

## Inputs
| Source | Location | Why |
|--------|----------|-----|
| Images | `input/` | source photos to process (copy reference images here first) |

## Model selection — the decision tree

The right choice depends on image type, subject matter, and how much detail matters.
Tested against close-up portraits with patterned backgrounds; results transfer reasonably well elsewhere.

| Model | Use when... | Time (on this box) | Notes |
|-------|-------------|--------------------:|-------|
| **`u2net_human_seg`** _(default)_ | portraits, busts, people, fashion shots | ~1.5 s | Best balance of speed + clean edges for human subjects. Shoulders preserve up to ~80% image height on standard portrait framing. |
| `u2net_human_seg --post-process=false` | you need the **most shoulder coverage** and can accept fuzzier edges | ~1.2 s | Disables rembg's mask-tightening pass, which is what chews into shoulders. Edge pixels go from crisp to semi-transparent (500K+ partial-alpha transitions). Visualize with checkerboard composites before committing. |
| `u2net_human_seg --alpha-matting` | hair, fine boundaries, feathered edges matter more than speed | ~1.8 s | Adds alpha matting post-process for smoother gradient edges. Worth it on close-ups where individual strands are visible. +30% time vs default. |
| `u2netp` | you just need something fast and clean enough | ~0.3 s | Smallest, fastest model. Quality visibly lower at fine boundaries. Good for thumbnails or quick previews; not recommended for final output on detailed portraits. |
| `sam` | extreme quality is worth the cost, and subject is complex/non-human (animals, objects) | ~4–10 s | Segment Anything produces clean masks but **still truncates shoulders** on close-up portrait framing (body covers only ~65% of image height). Useful for non-portrait subjects; skip for people. |

### Default recommendation
Use `u2net_human_seg --post-process` as your first pass. It handles 80%+ of close-up portrait work reliably and runs in ~1.5 s. Only change defaults when the user tells you something specific looks off.

## Patterned backgrounds — what to know

- A patterned background (tiles, checkerboard, textured walls) trips naive thresholding. U²-Net family handles it well by default because it learns object semantics rather than pixel-level color cues; that's why `u2net_human_seg` is the right choice here over anything color-threshold based.
- If you see **color bleeding** or pattern pixels surviving on the cutout edge, try `--alpha-matting`: rembg's matting step re-samples edges against local gradients and usually cleans up residual pattern artifacts.
- For very high-contrast patterns (e.g., striped shirt vs matching stripes in background) no single model nails it perfectly — consider post-processing with a manual edge pass if needed, or accept that this is at the boundary of what automatic segmentation handles cleanly on hard cases.

## Process
1. List images; report count/format.
2. Remove background using `rembg.remove()`. **Default session: `u2net_human_seg`** with post-processing enabled.
3. Save PNG with alpha channel to `output/`. Also save a 4x checkerboard composite for visual verification (toggled via `--no-composite`).
4. **Gate:** overwriting an existing output needs explicit "yes" or `--force`.
5. Append run-log.

## Outputs
| Artifact | Location | Format |
|----------|----------|--------|
| Image (transparent BG) | `output/<name>.png` | PNG with alpha channel |
| Checkerboard preview | `output/<name>_on_checkerboard.png` | 4× upscaled RGBA for visual inspection |

## Gates
- Overwrite needs "yes" or `--force`.

## Run log
`timestamp,background-remove,bg-remove:model=<m>,post=<0/1>,<processed>,<cached>,<errors>` to `output/run-log.csv`.

## Troubleshooting quick reference
| Symptom | Likely cause | Fix |
|---------|-------------|-----|
| Shoulders cut off / body truncated | default u2net (not human_seg) on a portrait crop | use the **default** (`u2net_human_seg --post-process`) — this is now the fix; older runs with plain `--model u2net` hit this. |
| Edges too fuzzy, "halo" of background color | using `--no-post-process`; rembg left partial-alpha pixels in raw mask | drop `--no-post-process`, or add `--alpha-matting` for cleaner edge gradients. |
| Hair looks sawtoothy | u2net's binary alpha on fine strands | add `--alpha-matting`. |
| Subject too small / lots of padding around it | post_process tightening aggressively trimmed mask edges | try `--no-post-process` (accept fuzzier edges) or reframe subject closer in the source photo. |

## Usage reference
```powershell
python scripts/remove_bg.py                                          # default: u2net_human_seg --post-process
python scripts/remove_bg.py --model u2netp                           # fast preview mode
python scripts/remove_bg.py --alpha-matting                          # add edge refinement
python scripts/remove_bg.py --no-post-process                        # raw mask, most body coverage
python scripts/remove_bg.py --no-composite --force                   # skip checkerboard, overwrite existing
```