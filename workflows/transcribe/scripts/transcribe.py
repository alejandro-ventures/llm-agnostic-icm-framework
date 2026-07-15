#!/usr/bin/env python3
"""Transcribe call recordings (mp3) into speaker-labeled transcripts (Markdown + JSON).

All inference is local: faster-whisper large-v3 (ASR, auto language detect, ASR venv)
+ pyannote speaker diarization (global clustering, .venv-pyannote). pyannote's models are
license-gated: a one-time authenticated download (see docs/README.md), after which runs
execute with HF_HUB_OFFLINE=1 — network access is impossible, audio never leaves the box.
Content-hash cache skips unchanged files; overwriting an existing transcript requires
--overwrite (the human gate).

ASR and diarization execute in SEPARATE subprocesses (--stage asr|diar self-invocations),
each in its own venv: the two engines' CUDA/cuDNN DLL stacks segfault when loaded into one
process on Windows. Process isolation removes that class of failure entirely.

Usage:  .venv-asr\Scripts\python.exe scripts\transcribe.py
        [--input DIR] [--device auto|cuda|cpu] [--language auto|en|de|...]
        [--max-speakers 4] [--overwrite] [--asr-model large-v3]
"""
from __future__ import annotations
import argparse, csv, datetime, hashlib, json, os, re, shutil, subprocess, sys, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "_core" / "scripts"))
import sandbox  # filesystem guardrail — see _core/SANDBOXING.md

# Never let a non-ASCII char (⚠, em-dash) crash a print on a cp1252 Windows console — a
# UnicodeEncodeError at the finish line would abort an otherwise-complete run.
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

WF_DIR = sandbox.workflow_dir(__file__)
WORKSPACE = WF_DIR.parents[1]
# Load via the 3.1 pipeline id: pyannote 4.x resolves it to the current stack
# (segmentation-3.0 + wespeaker embeddings + community-1 PLDA). Loading community-1
# directly as a pipeline id fails offline (it probes a config.yaml that isn't cached).
DIAR_MODEL = "pyannote/speaker-diarization-3.1"
# Diarization runs in its own venv (pyannote); ASR runs in the ASR venv (faster-whisper).
# The two engines' CUDA stacks segfault when imported into one process, so stages are isolated.
DIAR_PYTHON = WF_DIR / ".venv-pyannote" / "Scripts" / "python.exe"
VRAM_NEEDED_MB = 10000    # observed peak: ~8.2 GB (ASR fp16 + pyannote on a 75-min call)


def hms(seconds: float) -> str:
    s = int(round(seconds))
    return f"{s // 3600:02d}:{s % 3600 // 60:02d}:{s % 60:02d}"


def file_token(path: Path, asr_model: str, language: str, max_speakers) -> str:
    """Cache token: content hash + every engine param that changes output, so any of them
    changing re-runs the file (else a --max-speakers change would silently reuse a stale run)."""
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return f"{h.hexdigest()}|{asr_model}|pyannote31|spk{max_speakers}|{language}"


def ffprobe_duration(path: Path) -> float:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
        capture_output=True, text=True, check=True)
    return float(out.stdout.strip())


def free_vram_mb() -> int | None:
    try:
        out = subprocess.run(
            ["nvidia-smi", "--query-gpu=memory.free", "--format=csv,noheader,nounits"],
            capture_output=True, text=True, check=True)
        return int(out.stdout.strip().splitlines()[0])
    except Exception:
        return None


def ollama_resident() -> list[str]:
    """Model name(s) Ollama currently holds in VRAM (empty if none / ollama not on PATH)."""
    exe = shutil.which("ollama")
    if not exe:
        return []
    try:
        out = subprocess.run([exe, "ps"], capture_output=True, text=True, timeout=15)
    except Exception:
        return []
    rows = [ln for ln in out.stdout.splitlines() if ln.strip()]
    return [ln.split()[0] for ln in rows[1:]]      # skip the header row


def ollama_stop(model: str) -> bool:
    exe = shutil.which("ollama")
    if not exe:
        return False
    try:
        subprocess.run([exe, "stop", model], capture_output=True, text=True, timeout=30, check=True)
        return True
    except Exception:
        return False


def pick_device(requested: str, free_gpu: bool = False) -> tuple[str, str]:
    """Return (device, compute_type); enforce the VRAM gate for auto. If --free-gpu and an
    Ollama model is holding VRAM, stop it and re-check before gating."""
    if requested == "cpu":
        return "cpu", "int8"
    if requested == "cuda":
        return "cuda", "float16"
    free = free_vram_mb()
    if free is not None and free >= VRAM_NEEDED_MB:
        return "cuda", "float16"
    resident = ollama_resident()
    if resident and free_gpu:
        print(f"[gpu] freeing VRAM: stopping Ollama model(s) {', '.join(resident)} ...", flush=True)
        for m in resident:
            ollama_stop(m)
        time.sleep(3)
        free = free_vram_mb()
        if free is not None and free >= VRAM_NEEDED_MB:
            return "cuda", "float16"
    who = f"  Ollama is holding: {', '.join(resident)}." if resident else ""
    print(f"GATE: only {free} MB VRAM free (< {VRAM_NEEDED_MB} MB needed).{who}")
    if resident:
        print(f"  Choose one and re-run:")
        print(f"    1) auto-free:    --free-gpu   (stops {', '.join(resident)}; reloads on next LLM use)")
        print(f"       or manually:  ollama stop {resident[0]}")
    else:
        print("  Free the GPU or re-run with:")
    print("    2) CPU fallback: --device cpu   (slower, int8)")
    sys.exit(2)


def to_wav(mp3: Path, tmp_dir: Path) -> Path:
    """ffmpeg -> 16 kHz mono WAV (both engines consume it)."""
    wav = sandbox.guard_write(tmp_dir / (mp3.stem + ".wav"))
    wav.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(mp3),
                    "-ac", "1", "-ar", "16000", str(wav)], check=True)
    return wav


# ---------------------------------------------------------------- preflight / quality gates

def find_source_video(mp3: Path, source_dir: Path):
    """Longest video in source_dir whose name shares the mp3's YYYY-MM-DD prefix, as
    (path, duration_sec). None if no dated match (so the truncation check is skipped)."""
    m = re.match(r"(\d{4}-\d{2}-\d{2})", mp3.stem)
    if not m or not source_dir.is_dir():
        return None
    best = None
    for pat in ("*.mkv", "*.mp4", "*.mov"):
        for v in source_dir.glob(pat):
            if v.stem.startswith(m.group(1)):
                try:
                    d = ffprobe_duration(v)
                except Exception:
                    continue
                if best is None or d > best[1]:
                    best = (v, d)
    return best


def channel_rms(path: Path) -> list[float]:
    """Per-channel RMS level (dB) via ffmpeg astats. [] on failure."""
    try:
        r = subprocess.run(["ffmpeg", "-i", str(path), "-af", "astats=metadata=1:reset=0",
                            "-f", "null", "-"], capture_output=True, text=True, timeout=180)
    except Exception:
        return []
    vals, cur = [], None
    for line in r.stderr.splitlines():
        mc = re.search(r"Channel:\s*(\d+)", line)
        if mc:
            cur = mc.group(1)
        mr = re.search(r"RMS level dB:\s*(-?\d+\.?\d*)", line)
        if mr and cur:
            vals.append(float(mr.group(1)))
            cur = None
    return vals


def audio_preflight(mp3: Path, duration: float, source_dir: Path, min_ratio: float):
    """Cheap checks before the expensive ASR. Returns (truncated, warnings)."""
    warnings: list[str] = []
    truncated = False
    src = find_source_video(mp3, source_dir)
    if src:
        vpath, vdur = src
        if vdur > 0 and duration < vdur * min_ratio:
            truncated = True
            warnings.append(
                f"TRUNCATED: mp3 is {duration/60:.1f} min but source {vpath.name} is "
                f"{vdur/60:.1f} min ({duration/vdur*100:.0f}%) — conversion looks incomplete")
    rms = channel_rms(mp3)
    if len(rms) >= 2 and abs(rms[0] - rms[1]) >= 6.0:
        warnings.append(
            f"channel imbalance: L/R RMS {rms[0]:.0f}/{rms[1]:.0f} dB — one side much quieter "
            f"(a mic on a separate channel may be under-captured; check the recording)")
    return truncated, warnings


def quality_warnings(turns: list[dict], duration: float) -> list[str]:
    """Post-transcription heuristics (surface, don't block)."""
    w: list[str] = []
    if not turns:
        return ["no speech detected in the audio"]
    talk: dict[str, float] = {}
    for t in turns:
        talk[t["speaker"]] = talk.get(t["speaker"], 0.0) + (t["end"] - t["start"])
    speech = sum(talk.values())
    if speech and len(talk) > 1 and max(talk.values()) / speech > 0.85:
        top = max(talk, key=talk.get)
        w.append(f"{top} is {max(talk.values())/speech*100:.0f}% of all speech — the other "
                 f"side may be under-recorded (verify by ear)")
    if duration and speech / duration < 0.40:
        w.append(f"only {speech/duration*100:.0f}% of the runtime is speech — long silences "
                 f"or under-captured audio")
    return w


# ---------------------------------------------------------------- subprocess stages

def run_stage_asr(wavs: list[Path], args, device: str, compute_type: str) -> None:
    """Load faster-whisper once, transcribe every wav, write <stem>.asr.json next to it."""
    from faster_whisper import WhisperModel
    print(f"[asr] loading {args.asr_model} on {device} ({compute_type}) ...", flush=True)
    model = WhisperModel(args.asr_model, device=device, compute_type=compute_type)
    lang = None if args.language == "auto" else args.language
    for wav in wavs:
        if wav.with_suffix(".asr.json").exists():
            print(f"[asr] {wav.name}: already done (resume), skipping", flush=True)
            continue
        t0 = time.time()
        print(f"[asr] {wav.name} ...", flush=True)
        seg_iter, info = model.transcribe(str(wav), language=lang, beam_size=5,
                                          vad_filter=True, word_timestamps=True)
        segments = []
        for s in seg_iter:
            words = [{"start": w.start, "end": w.end, "word": w.word}
                     for w in (s.words or []) if w.start is not None and w.end is not None]
            segments.append({"start": s.start, "end": s.end, "text": s.text, "words": words})
        payload = {"language": info.language,
                   "language_probability": info.language_probability,
                   "segments": segments}
        with sandbox.safe_open_w(wav.with_suffix(".asr.json"), encoding="utf-8") as fh:
            json.dump(payload, fh, ensure_ascii=False)
        print(f"[asr] {wav.name}: {len(segments)} segments, language={info.language} "
              f"(p={info.language_probability:.2f}), {time.time() - t0:.0f}s", flush=True)


def run_stage_diar(wavs: list[Path], device: str, max_speakers: int | None) -> None:
    """Diarize each wav with pyannote 3.1 and write <stem>.diar.json.

    pyannote does segmentation + embedding + GLOBAL clustering internally, so speaker labels
    are consistent across the whole file — no chunking or stitching. Its own sliding-window
    keeps VRAM bounded (~10 GB even on 70-min files), so it fits without the whole-file
    allocation that crashed the machine under Sortformer.
    """
    import numpy as np
    import soundfile as sf
    import torch
    from pyannote.audio import Pipeline
    offline = os.environ.get("HF_HUB_OFFLINE") == "1"
    print(f"[diar] loading {DIAR_MODEL} on {device} "
          f"({'OFFLINE — no network possible' if offline else 'online: first-run download'}) ...",
          flush=True)
    pipeline = Pipeline.from_pretrained(DIAR_MODEL)   # token auto-resolves from `hf auth login`
    if pipeline is None:
        sys.exit(f"[diar] failed to load {DIAR_MODEL}. Accept its license on Hugging Face and run "
                 f"`{DIAR_PYTHON.parent / 'hf.exe'} auth login` first.")
    pipeline.to(torch.device(device))

    for wav in wavs:
        if wav.with_suffix(".diar.json").exists():
            print(f"[diar] {wav.name}: already done (resume), skipping", flush=True)
            continue
        t0 = time.time()
        print(f"[diar] {wav.name} ...", flush=True)
        # Hand pyannote an in-memory waveform so it never invokes torchcodec (its file
        # decoder can't load against FFmpeg 8 on this machine). Our WAV is already 16 kHz mono.
        data, sr = sf.read(str(wav), dtype="float32", always_2d=True)   # (samples, channels)
        waveform = torch.from_numpy(np.ascontiguousarray(data.T))       # (channels, samples)
        kwargs = {"max_speakers": max_speakers} if max_speakers else {}
        result = pipeline({"waveform": waveform, "sample_rate": sr}, **kwargs)
        # pyannote 4.x returns DiarizeOutput; its exclusive timeline has no overlapping
        # turns and is purpose-built for aligning with a transcript.
        annotation = getattr(result, "exclusive_speaker_diarization", result)
        segs = [[float(turn.start), float(turn.end), str(spk)]
                for turn, _, spk in annotation.itertracks(yield_label=True)]
        with sandbox.safe_open_w(wav.with_suffix(".diar.json"), encoding="utf-8") as fh:
            json.dump({"segments": sorted(segs)}, fh)
        print(f"[diar] {wav.name}: {len(segs)} segments, "
              f"{len({s[2] for s in segs})} speaker(s), {time.time() - t0:.0f}s", flush=True)


_DIAR_CACHE_REPOS = (          # every repo the 3.1 pipeline pulls; all must be cached
    "pyannote/speaker-diarization-3.1",
    "pyannote/segmentation-3.0",
    "pyannote/wespeaker-voxceleb-resnet34-LM",
    "pyannote/speaker-diarization-community-1",   # PLDA files
)


def _diar_model_cached() -> bool:
    """True once every repo the pyannote pipeline needs is snapshotted locally."""
    hub = Path.home() / ".cache" / "huggingface" / "hub"
    for repo in _DIAR_CACHE_REPOS:
        snaps = hub / ("models--" + repo.replace("/", "--")) / "snapshots"
        if not (snaps.is_dir() and any(snaps.iterdir())):
            return False
    return True


def spawn_stage(stage: str, wavs: list[Path], args, device: str, compute_type: str) -> None:
    """Re-invoke this script as an isolated child for one engine stage. ASR uses this
    interpreter (ASR venv / faster-whisper); diar uses the pyannote venv."""
    python = str(DIAR_PYTHON) if stage == "diar" else sys.executable
    if stage == "diar" and not DIAR_PYTHON.exists():
        sys.exit(f"pyannote venv missing at {DIAR_PYTHON} — see docs/README.md to build it.")
    env = dict(os.environ, HF_HUB_DISABLE_TELEMETRY="1")
    offline = stage == "diar" and _diar_model_cached()
    if offline:
        # Privacy lock: models are on disk, so forbid ALL network access in the child.
        # Any attempted call to Hugging Face hard-fails instead of silently reaching out.
        env["HF_HUB_OFFLINE"] = "1"
    cmd = [python, "-u", str(Path(__file__).resolve()), "--stage", stage,
           "--device", device, "--compute-type", compute_type,
           "--language", args.language, "--asr-model", args.asr_model,
           "--max-speakers", str(args.max_speakers),
           "--wavs"] + [str(w) for w in wavs]
    res = subprocess.run(cmd, env=env)
    if res.returncode != 0 and offline:
        print(f"stage '{stage}' failed OFFLINE (incomplete model cache?) — retrying ONLINE "
              f"once to re-download models. Audio still never leaves this machine.", flush=True)
        env.pop("HF_HUB_OFFLINE")
        res = subprocess.run(cmd, env=env)
    if res.returncode != 0:
        sys.exit(f"stage '{stage}' failed with exit code {res.returncode}")


# ---------------------------------------------------------------- merge + output

# Turn smoothing (validated on the 128-turn Feb call: cut <=3-word flicker turns 17->7):
# a short turn wedged between two turns of the SAME other speaker is almost always a
# mis-split backchannel — reassign it to that speaker.
ISLAND_SEC = 2.0
ISLAND_WORDS = 4


def _label_for_word(diar_segs, start: float, end: float) -> str | None:
    """Speaker for a word: diar segment with max time-overlap; if none overlaps, the
    nearest segment by time. Never inherits the previous speaker across a gap."""
    best, best_ov = None, 0.0
    for s, e, lab in diar_segs:
        ov = min(end, e) - max(start, s)
        if ov > best_ov:
            best, best_ov = lab, ov
    if best is not None:
        return best
    if not diar_segs:
        return None
    mid = (start + end) / 2
    return min(diar_segs, key=lambda seg: 0 if seg[0] <= mid <= seg[1]
               else min(abs(seg[0] - mid), abs(seg[1] - mid)))[2]


def _group(units: list) -> list:
    """Merge consecutive same-label [start, end, text, label] units into turns."""
    turns: list = []
    for start, end, text, lab in units:
        if turns and turns[-1][3] == lab:
            turns[-1][1] = end
            turns[-1][2] += text
        else:
            turns.append([start, end, text, lab])
    return turns


def build_turns(asr_segs, diar_segs) -> list[dict]:
    """Attribute speakers at WORD granularity (max diar overlap, nearest-segment fallback),
    group into turns, then remove single-turn islands. Falls back to per-segment attribution
    if word timestamps are absent."""
    diar_segs = sorted(tuple(s) for s in diar_segs)
    label_order: dict[str, str] = {}          # diar label -> SPEAKER n (first appearance)

    def display(label: str) -> str:
        if label not in label_order:
            label_order[label] = f"SPEAKER {len(label_order) + 1}"
        return label_order[label]

    units: list[list] = []
    prev = None
    for seg in asr_segs:
        words = seg.get("words") or []
        items = ([(w["start"], w["end"], w["word"]) for w in words]
                 if words else [(seg["start"], seg["end"], seg["text"])])
        for start, end, text in items:
            lab = _label_for_word(diar_segs, start, end) or prev
            prev = lab
            units.append([start, end, text, lab])
    if units and units[0][3] is None:          # leading gap before any diar coverage
        first = next((u[3] for u in units if u[3] is not None), None)
        for u in units:
            if u[3] is not None:
                break
            u[3] = first

    turns = _group(units)
    changed = True
    while changed:                             # island removal (iterate to convergence)
        changed = False
        for i in range(1, len(turns) - 1):
            start, end, text, lab = turns[i]
            if (end - start <= ISLAND_SEC or len(text.split()) <= ISLAND_WORDS) \
                    and turns[i - 1][3] == turns[i + 1][3] and turns[i - 1][3] != lab:
                turns[i][3] = turns[i - 1][3]
                changed = True
        if changed:
            turns = _group(turns)

    return [{"start": round(s, 2), "end": round(e, 2),
             "speaker": display(lab), "text": text.strip()} for s, e, text, lab in turns]


def parse_names(spec: str) -> dict:
    """'1=Alejandro,2=Christopher' or 'SPEAKER 1=...' -> {'SPEAKER 1':'Alejandro', ...}."""
    names = {}
    for part in filter(None, (p.strip() for p in (spec or "").split(","))):
        k, _, v = part.partition("=")
        k, v = k.strip(), v.strip()
        if not v:
            continue
        label = k if k.upper().startswith("SPEAKER") else f"SPEAKER {k}"
        names[label] = v
    return names


def write_outputs(mp3: Path, out_dir: Path, turns, meta, names: dict | None = None) -> Path:
    """Write <stem>.md + .json. JSON segments always keep canonical `SPEAKER n` labels;
    any friendly names live in meta['speaker_names'] so relabeling stays reversible.
    The .md renders the friendly name when one is mapped."""
    names = names or {}
    if names:
        meta = {**meta, "speaker_names": names}

    def disp(label):
        return names.get(label, label)

    md_path = out_dir / (mp3.stem + ".md")
    who = "  ·  ".join(f"{disp(l)}" for l in sorted({t["speaker"] for t in turns})) if names \
        else str(meta["speakers_detected"])
    lines = [f"# Transcript — {mp3.name}", "",
             "| | |", "|---|---|",
             f"| Source | {mp3.name} |",
             f"| Duration | {hms(meta['duration_sec'])} |",
             f"| Language | {meta['language']} (p={meta['language_probability']:.2f}) |",
             f"| Speakers | {who} |",
             f"| ASR | faster-whisper {meta['asr_model']} ({meta['device']}/{meta['compute_type']}) |",
             f"| Diarization | {DIAR_MODEL} |",
             f"| Generated | {meta['generated']} |", ""]
    for w in meta.get("warnings", []):
        lines.append(f"> ⚠ {w}")
    lines += ["", "---", ""]
    for t in turns:
        lines.append(f"**{disp(t['speaker'])}** [{hms(t['start'])}]")
        lines.append(t["text"])
        lines.append("")
    with sandbox.safe_open_w(md_path, encoding="utf-8") as fh:
        fh.write("\n".join(lines))
    with sandbox.safe_open_w(out_dir / (mp3.stem + ".json"), encoding="utf-8") as fh:
        json.dump({"metadata": meta, "segments": turns}, fh, ensure_ascii=False, indent=1)
    return md_path


def relabel_existing(json_path: Path, names: dict) -> None:
    """GPU-free: rewrite an existing transcript's .md/.json with friendly speaker names,
    without re-transcribing. Merges into any existing name map."""
    data = json.loads(json_path.read_text(encoding="utf-8"))
    meta, turns = data["metadata"], data["segments"]
    merged = {**meta.get("speaker_names", {}), **names}
    stem = json_path.with_suffix("")
    # write_outputs derives file names from mp3.stem/out_dir; emulate with the json's own stem.
    out_dir = json_path.parent
    fake_mp3 = Path(meta.get("source", json_path.stem))
    # ensure the output filename matches the existing files (json stem, not mp3 name)
    if fake_mp3.stem != json_path.stem:
        fake_mp3 = Path(json_path.stem + ".mp3")
    write_outputs(fake_mp3, out_dir, turns, {k: v for k, v in meta.items() if k != "speaker_names"},
                  names=merged)
    print(f"relabeled {json_path.name}: {merged}")


# ---------------------------------------------------------------- orchestrator

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--input", default=str(WF_DIR / "input"))
    ap.add_argument("--device", default="auto", choices=["auto", "cuda", "cpu"])
    ap.add_argument("--language", default="auto")
    ap.add_argument("--max-speakers", type=int, default=4)
    ap.add_argument("--overwrite", action="store_true")
    ap.add_argument("--asr-model", default="large-v3")
    ap.add_argument("--names", default="",
                    help='map speakers to names, e.g. "1=Alejandro,2=Christopher" (per run; '
                         'the SPEAKER->person mapping differs per file, so name one file at a time)')
    ap.add_argument("--relabel", default="",
                    help="GPU-free: rewrite an existing transcript .json's speaker names using "
                         "--names, without re-transcribing")
    ap.add_argument("--source-dir", default=str(Path.home() / "Videos"),
                    help="folder of source videos; mp3 durations are checked against a same-date "
                         "video to catch truncated conversions (default ~/Videos; skipped if absent)")
    ap.add_argument("--allow-truncated", action="store_true",
                    help="transcribe even if an mp3 is much shorter than its source video")
    ap.add_argument("--min-source-ratio", type=float, default=0.95,
                    help="truncation gate fires if mp3 duration < this fraction of the source video")
    ap.add_argument("--free-gpu", action="store_true",
                    help="if VRAM is short, stop the resident Ollama model instead of gating")
    # internal (stage children only)
    ap.add_argument("--stage", choices=["asr", "diar"], help=argparse.SUPPRESS)
    ap.add_argument("--compute-type", default="float16", help=argparse.SUPPRESS)
    ap.add_argument("--wavs", nargs="*", help=argparse.SUPPRESS)
    args = ap.parse_args()

    if args.stage:  # child process: run one engine stage and exit
        wavs = [Path(w) for w in args.wavs]
        if args.stage == "asr":
            run_stage_asr(wavs, args, args.device, args.compute_type)
        else:
            run_stage_diar(wavs, args.device, args.max_speakers)
        return 0

    names = parse_names(args.names)

    if args.relabel:  # GPU-free relabel mode: no transcription, just rewrite names
        if not names:
            print("--relabel needs --names, e.g. --relabel out/Foo.json --names '1=Alejandro,2=Chris'")
            return 1
        relabel_existing(sandbox.guard_write(args.relabel), names)
        return 0

    src = Path(args.input)
    out_dir = sandbox.guard_write(WF_DIR / "output")
    out_dir.mkdir(parents=True, exist_ok=True)
    tmp_dir = out_dir / ".tmp_wav"

    mp3s = sorted(src.glob("*.mp3"))
    if not mp3s:
        print(f"No mp3 files in {src}")
        return 1
    print(f"Found {len(mp3s)} mp3(s) in {src}")

    cache_file = out_dir / ".transcribe_cache"
    seen = set(filter(None, cache_file.read_text().splitlines())) if cache_file.exists() else set()

    # Build the worklist (cache + overwrite gate, audio preflight), preflight durations.
    source_dir = Path(args.source_dir)
    work: list[tuple[Path, str, float, list]] = []
    for mp3 in mp3s:
        duration = ffprobe_duration(mp3)
        print(f"  {mp3.name}: {hms(duration)}")
        token = file_token(mp3, args.asr_model, args.language, args.max_speakers)
        md_out = out_dir / (mp3.stem + ".md")
        if token in seen and md_out.exists() and not args.overwrite:
            print("    skip (cached)")
            continue
        if md_out.exists() and not args.overwrite:
            print(f"    GATE: {md_out.name} exists. Re-run with --overwrite after explicit approval. Skipping.")
            continue
        truncated, pre_warn = audio_preflight(mp3, duration, source_dir, args.min_source_ratio)
        for w in pre_warn:
            print(f"    warn: {w}")
        if truncated and not args.allow_truncated:
            print(f"    GATE: {mp3.name} looks truncated — re-convert it from the source video, "
                  f"or pass --allow-truncated to transcribe anyway. Skipping.")
            continue
        work.append((mp3, token, duration, pre_warn))
    if not work:
        print("Nothing to do.")
        return 0

    device, compute_type = pick_device(args.device, free_gpu=args.free_gpu)
    print(f"Device: {device} ({compute_type})")

    # Stage children skip work whose .asr/.diar.json already exists, so a failed run
    # resumes instead of recomputing. tmp_dir is only removed after full success.
    wavs = [to_wav(mp3, tmp_dir) for mp3, _, _, _ in work]
    spawn_stage("asr", wavs, args, device, compute_type)   # isolated: ctranslate2 stack
    spawn_stage("diar", wavs, args, device, compute_type)  # isolated: pyannote/torch stack

    processed = 0
    run_warnings: list[str] = []
    for (mp3, token, duration, pre_warn), wav in zip(work, wavs):
        asr = json.loads(wav.with_suffix(".asr.json").read_text(encoding="utf-8"))
        diar = json.loads(wav.with_suffix(".diar.json").read_text(encoding="utf-8"))
        diar_segs = [(s, e, lab) for s, e, lab in diar["segments"]]
        turns = build_turns(asr["segments"], diar_segs)
        warns = list(pre_warn) + quality_warnings(turns, duration)
        meta = {"source": mp3.name, "duration_sec": round(duration, 1),
                "language": asr["language"],
                "language_probability": round(asr["language_probability"], 3),
                "asr_model": args.asr_model, "device": device,
                "compute_type": compute_type, "diarization_model": DIAR_MODEL,
                "speakers_detected": len({t["speaker"] for t in turns}),
                "warnings": warns,
                "generated": datetime.datetime.now().isoformat(timespec="seconds")}
        md_path = write_outputs(mp3, out_dir, turns, meta, names=names)
        seen.add(token)
        processed += 1
        run_warnings += [f"{mp3.name}: {w}" for w in warns]
        print(f"  -> {md_path.name} + .json  ({len(turns)} turns, "
              f"{meta['speakers_detected']} speakers)")
    shutil.rmtree(tmp_dir, ignore_errors=True)
    if run_warnings:
        print("\n⚠ quality warnings (review):")
        for w in run_warnings:
            print(f"  - {w}")

    with sandbox.safe_open_w(cache_file, "w", encoding="utf-8") as fh:
        fh.write("\n".join(sorted(seen)))

    with sandbox.safe_open_w(out_dir / "run-log.csv", "a", newline="") as fh:
        csv.writer(fh).writerow([datetime.datetime.now().isoformat(timespec="seconds"),
                                 "transcribe", f"transcribe:asr={args.asr_model},diar=pyannote31",
                                 processed])
    # Token-tracker entry (CONVENTIONS rule 11) — non-fatal if it hiccups.
    try:
        subprocess.run([sys.executable, str(WORKSPACE / "_core" / "token-tracker" / "tracker.py"),
                        "log", "--workflow", "transcribe", "--action", "transcribe",
                        "--model", f"{args.asr_model}+pyannote31", "--source", "local",
                        "--outcome", "success", "--summary", f"{processed} file(s)"],
                       check=True, capture_output=True)
    except Exception as e:
        print(f"  (token-tracker logging failed: {e})")

    print(f"\nDone. {processed} file(s) transcribed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
