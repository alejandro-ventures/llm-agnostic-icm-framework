---
name: transcribe
description: >-
  Turn call recordings (mp3/audio) into speaker-labeled, timestamped transcripts (Markdown +
  JSON), fully local — faster-whisper large-v3 ASR + pyannote speaker diarization on the GPU.
argument-hint: "mp3 files (default workflows/transcribe/input)"
requires-python: "3.10"
network: none at runtime — one license-gated model download at setup, then HF_HUB_OFFLINE=1 (hard-fails)
destructive: none — overwriting an existing transcript requires the gate
gates: ["overwriting an existing output (--overwrite)", "freeing the GPU from another process (--free-gpu)"]
---
# transcribe
Sensitive audio: **all inference is local** — audio and transcripts never leave this machine.
pyannote's models are license-gated on Hugging Face: ONE authenticated download at setup (see
docs/README.md), after which every run executes with `HF_HUB_OFFLINE=1` — network access is
impossible, not merely avoided. The HF token can be revoked after setup.
## Environment — two venvs, a deliberate exception to CONVENTIONS rule 10
| Stage | Engine | Interpreter |
|-------|--------|-------------|
| ASR | faster-whisper `large-v3` (CUDA fp16 / CPU int8) | `workflows/transcribe/.venv-asr` |
| Diarization | `pyannote/speaker-diarization-3.1` (pyannote.audio 4.x resolves it to the current community stack) | `workflows/transcribe/.venv-pyannote` |
Stages run as **separate subprocesses** — the two engines' CUDA/cuDNN DLLs segfault when
loaded into one process on Windows. Never merge them. `requirements.txt` pins both stacks.
## Inputs
| Source | Location | Why |
|--------|----------|-----|
| mp3 files | `input/` | recordings (copy reference audio here first — originals untouched) |
## Process
1. Preflight (cheap, before ASR): ffprobe each mp3; skip cached/existing outputs.
   **Truncation gate** — compare each mp3's duration to a same-date video in `--source-dir`;
   if the mp3 is < 95% of the source it's flagged truncated and skipped (re-convert, or
   `--allow-truncated`). Channel-imbalance check warns if L/R RMS differ ≥ 6 dB.
   **VRAM gate:** if < 10 GB free, the message names the resident Ollama model; free it with
   `--free-gpu` (opt-in — it never seizes the GPU from another session by default) or `--device cpu`.
   2. ffmpeg → 16 kHz mono WAV (temp). 3. ASR subprocess: word-level
   timestamps, language auto-detect per file. 4. Diar subprocess: pyannote whole-file
   (global clustering keeps speaker identity consistent; VRAM stays bounded ~8 GB even on
   75-min calls — do NOT swap in a diarizer that loads the whole file into attention; that
   crashed this machine twice, hypervisor bugcheck). 5. Merge: per-WORD speaker
   attribution by diar overlap, then group into turns. 6. Write `.md` + `.json` via
   `sandbox.guard_write`. 7. **Gate:** overwrite needs explicit "yes" (`--overwrite`).
   8. Append run-log + token-tracker entry.
## Outputs
| Artifact | Location | Format |
|----------|----------|--------|
| Transcript | `output/<name>.md` | header (source, duration, language, speakers, models) + `**SPEAKER n** [HH:MM:SS]` turns |
| Segments | `output/<name>.json` | `{metadata, segments:[{start,end,speaker,text}]}` |
## Gates & warnings
- **Truncation gate** (hard): mp3 shorter than its source video → skipped unless `--allow-truncated`.
- **VRAM gate** (hard): under threshold → names the resident model; `--free-gpu` or `--device cpu`.
- **Overwrite gate** (hard): re-transcribing an existing output needs `--overwrite`.
- **Quality warnings** (soft — surfaced in the run summary + `.md` header, never block): one
  speaker > 85% of speech, or speech < 40% of runtime, or a channel imbalance. Deliberately
  conservative — moderate imbalance won't fire; a mono-summed quiet mic is undetectable by
  design, so it stays a human-ear check.
## Languages
Auto-detect; EN/FR/DE/RU/ES (and ~95 more) natively strong. Dialects without whisper coverage
(e.g. Swiss German) come out as approximate standard language with reduced accuracy; a
fine-tune can be swapped in via `--asr-model`.
## Run log
`timestamp,transcribe,<action>,<n>` to `output/run-log.csv`, then
`python _core/token-tracker/tracker.py log --workflow transcribe --action transcribe --source local`.
