# Changelog

Release notes, newest first, one entry per released version; the entry being written is `changelog.d/`.

## 1.0.0

**unslop ships as an extension package: `slipwai extension install unslop`, elected in a project with `./init --extension unslop`.** Damir Sokolovsky's unslop skill (CC BY 4.0), bundled at heydamir/unslop `97daa3e`, is installed into `skills/unslop/`, so `make agents` gives it to every harness with a skills folder. Upstream supports Claude Code and Codex only. Its pictures go to `tools/unslop/refs/`. The `AGENTS.md` block covers how to run it with a person present and as a delegate on a slice. A hand-edited file is kept, with the new version waiting under `tools/unslop/pending/`. `check-unslop` fails on a half-finished or out-of-date install. Node, Playwright and ffmpeg are optional, and a missing one is reported, never fatal (#42).
