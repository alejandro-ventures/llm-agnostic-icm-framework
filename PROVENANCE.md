# Provenance and Authorship Statement

## 1. Author

- Name: Alejandro Rodriguez
- ORCID: 0009-0002-4730-3933
- Personal email: alejandro.ventures@pm.me
- GitHub handle: alejandro-ventures
- Residence: Switzerland / United States
- Full legal identity: held in a private signed record, available to verify ownership if required.

## 2. Authorship Declaration

I, the author, created this project — all source code, documentation, architecture, and
configuration in this repository (the "Work") — independently and in a personal capacity, on my
own time and equipment. I am its sole author and copyright owner, and the Work contains no third
party's confidential or proprietary information.

## 3. Rights

I retain copyright in the Work and license it under the accompanying LICENSE. The Work is original
to me and does not incorporate any third party's confidential information or proprietary materials.

## 4. First Publication

- First public release date: 2026-06-28
- Repository: https://github.com/alejandro-ventures/llm-agnostic-icm-framework
- Initial release tag: v1.0.0
- Authoritative record: the v1.0.0 release tag and GitHub's immutable per-commit metadata
  (author name, email, and timestamp) constitute the primary first-publication evidence.

## 5. Independent Timestamping

- GitHub commit history — automatic, immutable author/date metadata on every commit.
- Content hash: `provenance.manifest.sha256` — SHA-256 of every **git-tracked source and
  documentation file** at the tagged release. Dependencies, virtual environments, and generated
  outputs are not covered (they are not tracked). Regenerate/verify:
  `python _core/scripts/make_provenance.py [--check]`.
- OpenTimestamps proof: `provenance.manifest.sha256.ots` — anchors the manifest's combined
  root hash to the Bitcoin blockchain. The proof and the manifest itself are excluded from the
  manifest's file list (derived artifacts cannot contain their own hash).
- Internet Archive snapshot: submit the repository URL at web.archive.org on release day and
  record the resulting snapshot URL here.

### Timestamp records
- **v2.1.0 (2026-07-15):** OTS proof committed as `provenance.manifest.sha256.ots`, submitted
  to four public calendar servers on 2026-07-15. Pending Bitcoin attestation — after ~24 h run
  `ots-cli.js upgrade provenance.manifest.sha256.ots` and commit the upgraded proof to make it
  locally verifiable. Internet Archive snapshot: submission was rate-limited on release day;
  record the snapshot URL here once accepted.
- Cross-publication (optional): a short public post linking the v1.0.0 release.

## 6. Scope and Domain Framing

The Work is a generic, model-agnostic framework for orchestrating LLM-based workflows with structured audit trails, governance controls, and reproducible execution. It is not specific to any organization.

Example workflows included in this repository must operate exclusively on publicly available data or synthetic/generic file operations.

## 7. Contact

alejandro.ventures@pm.me

Signed: Alejandro Rodriguez (full legal identity on file privately)

Date: 28 June 2026

