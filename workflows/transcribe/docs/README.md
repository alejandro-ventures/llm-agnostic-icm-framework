# transcribe

Human guide for turning call recordings (mp3) into speaker-labeled transcripts, fully local.

## Architecture (differs from other workflows)
Two stages, two venvs, run as separate subprocesses (their CUDA DLL stacks segfault if loaded
into one process — a hard-won lesson, do not "simplify" this):

- **ASR** — faster-whisper `large-v3` in `workflows/transcribe/.venv-asr` (gitignored;
  documented rule-9 exception: two venvs, one workflow).
- **Diarization** — pyannote in `workflows/transcribe/.venv-pyannote` (gitignored).

## One-time setup
1. Build the pyannote venv (from this workflow folder):

       py -3.10 -m venv .venv-pyannote
       .venv-pyannote\Scripts\python -m pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu128
       .venv-pyannote\Scripts\python -m pip install "pyannote.audio>=4.0" soundfile

2. pyannote's models are license-gated (free): with a Hugging Face account, click
   "Agree and access repository" on ALL THREE pages —
   `pyannote/speaker-diarization-3.1`, `pyannote/segmentation-3.0`,
   `pyannote/speaker-diarization-community-1` — then create a **Read** token
   (huggingface.co/settings/tokens) and log in:

       .venv-pyannote\Scripts\hf.exe auth login

3. The first run downloads ~200 MB of models into `~/.cache/huggingface`. Every later run sets
   `HF_HUB_OFFLINE=1` automatically (network access hard-fails). You can revoke the HF token
   after the first successful run — cached models keep working.

## Run
Put mp3s in `input/`, then from this workflow folder:

    .venv-asr\Scripts\python.exe scripts\transcribe.py

Flags:

    --device auto|cuda|cpu   # auto checks free VRAM (needs ~10 GB); cpu = slower int8
    --free-gpu               # if VRAM is short, stop the resident Ollama model (opt-in)
    --language auto|en|de|…  # default auto-detect per file
    --overwrite              # re-transcribe files whose output exists (the gate)
    --max-speakers 4         # diarization upper bound
    --asr-model large-v3     # swap for a fine-tune (e.g. Swiss German) if ever needed
    --names "1=Ana,2=Bob"    # friendly speaker names (per file; .json keeps SPEAKER n)
    --relabel out/Foo.json   # GPU-free: rename an existing transcript's speakers (with --names)
    --source-dir DIR         # videos to check mp3 durations against (default ~/Videos)
    --allow-truncated        # transcribe even if an mp3 is shorter than its source video

## Preflight gates (catch problems before wasting compute)
- **Truncation:** each mp3's duration is checked against a same-date video in `--source-dir`.
  A short mp3 (incomplete conversion) is flagged and skipped — re-convert it, e.g.
  `ffmpeg -i "Videos\<date> <time>.mkv" -vn -b:a 128k input\"<date> Call.mp3"`.
- **VRAM:** if the GPU is busy the run stops and names the Ollama model holding it; `--free-gpu`
  stops it for you (it reloads on next LLM use), or use `--device cpu`.
- **Quality warnings:** after transcription, a lopsided speaker split (>85%), low speech
  coverage (<40%), or channel imbalance are surfaced in the run summary and the `.md` header.
  These never block — they're a review nudge. Note a mono-summed quiet mic can't be detected;
  that is a capture-side fix (record the mic on its own track / at a higher level).

## VRAM note
A resident local LLM (e.g. under Ollama) may be holding VRAM. The script stops with instructions if less than
~10 GB is free: run `ollama stop <model>` (it reloads on next LLM use) or use `--device cpu`.

## Outputs
Per input mp3: `output/<name>.md` (readable transcript) and `output/<name>.json` (segments for
downstream automation). Re-runs skip unchanged files via `output/.transcribe_cache`.

## Known limits
- Speaker labels flicker on rapid back-and-forth (short fragments may get the wrong speaker) —
  normal diarization noise; the transcript remains usable. A v2 could smooth turn boundaries.
- Swiss German is not supported by whisper (comes out as rough Standard German).
- pyannote caps at the `--max-speakers` bound; calls with more voices need a higher bound.
