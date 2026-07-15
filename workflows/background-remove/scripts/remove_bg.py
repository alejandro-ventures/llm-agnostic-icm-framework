"""Remove backgrounds from images using U²-Net family models (rembg library).

Outputs PNGs with transparent alpha channels plus optional visual-composite
checkerboards for quick quality checks. Content-hash cache skips re-runs of the
same input+model combination.

Usage:
    python remove_bg.py [input_dir] [output_dir]
        --model <u2net|u2netp|u2net_human_seg>  (default: u2net_human_seg)
        [--post-process]                        enable edge refinement (on by default)
        [--no-composite]                        skip the checkerboard preview

"""
from __future__ import annotations

import argparse, csv, hashlib, io, sys, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "_core" / "scripts"))
import sandbox  # filesystem guardrail — see _core/SANDBOXING.md

from PIL import Image
import rembg

SUPPORTED = {".png", ".jpg", ".jpeg", ".bmp", ".webp"}

MODELS = {
    "u2net":           ("U²-Net (default, general purpose)",            False),
    "u2netp":          ("U²-Net small/faster — slightly lower quality",  True),
    "u2net_human_seg": ("Human-segmentation model — sharper portrait edges", True),
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _composite_checkerboard(img_rgba, tile=8):
    """4x upscaled checkerboard so you can actually see the alpha."""
    w, h = img_rgba.size
    big_w, big_h = w * 4, h * 4
    bg = Image.new("RGBA", (big_w, big_h), (255, 255, 255, 255))
    for x in range(0, big_w, tile):
        for y in range(0, big_h, tile):
            if ((x // tile) + (y // tile)) % 2 == 0:
                bg.putpixel((x, y), (190, 195, 200, 255))
    scaled = img_rgba.resize((big_w, big_h), Image.LANCZOS)
    bg.paste(scaled, (0, 0), mask=scaled.split()[3])
    return bg


def main(in_dir: str, out_dir: str, args) -> int:
    src = Path(in_dir)
    dst = sandbox.guard_write(out_dir)
    dst.mkdir(parents=True, exist_ok=True)

    cache_file = dst / ".bg_cache"
    # key is "digest:model:post" so swapping models does not reuse stale masks
    seen = {}
    if cache_file.exists():
        for line in cache_file.read_text().splitlines():
            parts = line.split(":", 3)
            if len(parts) >= 4 and ":".join(parts[1:]).count(":") >= 2:
                seen[line] = True

    images = sorted(src.iterdir())
    images = [f for f in images if f.is_file() and f.suffix.lower() in SUPPORTED]
    model_label, _ = MODELS[args.model]
    print(f"Found {len(images)} image(s) in {src}")
    print(f"Model: {args.model}  ({model_label})  post_process={args.post_process}")

    processed = 0
    skipped_cache = 0
    skipped_exists = 0
    errors = 0

    for img_path in images:
        digest = sha256(img_path)
        cache_key = f"{digest}:{args.model}:{bool(args.post_process)}:{bool(args.alpha_matting)}"
        if cache_key in seen:
            print(f"  skip (cached): {img_path.name}")
            skipped_cache += 1
            continue

        out_name = img_path.stem + ".png"
        out_path = dst / out_name
        if out_path.exists() and not args.force:
            print(f"  GATE: {out_name} exists. Use --force to overwrite.")
            skipped_exists += 1
            continue

        try:
            input_data = img_path.read_bytes()
            output_data = rembg.remove(
                input_data,
                session=rembg.new_session(args.model),
                alpha_matting=args.alpha_matting,
            post_process_mask=args.post_process,
            )
        except Exception as exc:
            print(f"  ERROR {img_path.name}: {exc}")
            errors += 1
            continue

        img = Image.open(io.BytesIO(output_data))

        # transparent PNG with alpha channel
        img.save(out_path)

        # checkerboard composite for visual verification
        if args.composite:
            comp_name = img_path.stem + "_on_checkerboard.png"
            _composite_checkerboard(img).save(dst / comp_name)
            print(f"  done: {img_path.name} -> {out_name} (+{comp_name})")
        else:
            print(f"  done: {img_path.name} -> {out_name}")

        seen[cache_key] = True
        processed += 1

    cache_file.write_text("\n".join(sorted(seen)))

    if skipped_exists and not args.force:
        print(f"\n  {skipped_exists} file(s) left alone. Add --force to overwrite.")

    with (dst / "run-log.csv").open("a", newline="") as fh:
        csv.writer(fh).writerow([
            datetime.datetime.now().isoformat(timespec="seconds"),
            "background-remove",
            f"bg-remove:model={args.model},post={int(args.post_process)}",
            processed, skipped_cache, errors,
        ])

    summary = [f"Done. {processed} file(s) processed"]
    if skipped_cache:   summary.append(f"{skipped_cache} cached")
    if skipped_exists and not args.force: summary.append(f"{skipped_exists} gated")
    if errors:          summary.append(f"{errors} errored")
    print("  ".join(summary))
    return 1 if errors else 0


if __name__ == "__main__":
    wf = sandbox.workflow_dir(__file__)

    parser = argparse.ArgumentParser(
        description="Remove image backgrounds (rembg U²-Net family).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"Models:\n  " + "\n  ".join(f"{k:<20s} {v[0]}" for k, v in MODELS.items()),
    )
    parser.add_argument("input_dir",  nargs="?", default=str(wf / "input"))
    parser.add_argument("output_dir", nargs="?", default=str(wf / "output"))
    parser.add_argument("--model", choices=list(MODELS.keys()), default="u2net_human_seg")
    parser.add_argument("--post-process", dest="post_process", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--alpha-matting", dest="alpha_matting", action=argparse.BooleanOptionalAction, default=False)
    parser.add_argument("--no-composite", dest="composite",  action="store_false")
    parser.add_argument("--force",      action="store_true", help="overwrite existing outputs without gating")
    args = parser.parse_args()

    raise SystemExit(main(str(args.input_dir), str(args.output_dir), args))



