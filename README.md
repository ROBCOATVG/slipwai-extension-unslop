# unslop

A slipwai extension: optional dev tooling a generated or adopted project can elect at `./init`.

Installs Damir Sokolovsky's [unslop](https://github.com/heydamir/unslop) skill into every harness here: an ordered redline pass that turns AI-looking screens into a designed interface. Needs a browser app.

unslop is by Damir Sokolovsky ([@heydamir](https://x.com/heydamir)), licensed under CC BY 4.0. This package bundles it at the commit named in `UPSTREAM`. `NOTICE` lists the three ways the installed copy differs from upstream.

## Installing

```sh
slipwai extension install unslop
```

Then, in a project:

```sh
./init --extension unslop
```

`./init` offers it in the extension menu too, where it was installed when the project was generated. It prints one line for each harness that received the skill, and a line for each optional step that is off and the command that turns it on.

## What it does

- **Installs the skill once, into `skills/unslop/`.** That is the project's canonical skill catalogue, so `make agents` copies it into every harness with a skills folder, and a harness added later gets it on the next `make agents`. A harness with no skills folder is pointed at `skills/unslop/SKILL.md` from `AGENTS.md`. Upstream supports Claude Code and Codex only.
- **Installs the reference pictures into `tools/unslop/refs/`**, because the projection copies a skill as text.
- **Writes an `AGENTS.md` block** that says how to run it with a person present (audit, then stop for the direction, then the passes, and ask before any paid image generation), and how to run it as a delegate on a slice (write the direction into `specs/<feature>/decisions.md` rather than wait, no paid generation, no story video, taste is a recorded decision and never a park).
- **Bundles the skill rather than fetching it.** The release digest and publisher trust cover it, and it installs offline and in CI. An upstream update is a new version of this package.

Both directories are ignored by Git and reinstalled by `./init --extension unslop`.

## Pairing with ux-gates

ux-gates measures a screen: tokens, contrast, focus, target size, overflow, axe. unslop is taste: what the screen should look like. Use both. Where ux-gates is installed and the project has no Playwright of its own, the skill's optional scripts can use the one ux-gates installed (`NODE_PATH=tools/ux-gates/node_modules`).

## Optional steps

| Step | Needs |
| --- | --- |
| Snapshot a live site (`scripts/snapshot.mjs`) | Node, Playwright and its Chromium |
| Story video (`scripts/story.mjs`) | Node, Playwright and ffmpeg |
| Generated pictures | An image-generation MCP server the person connects |

None of these is needed for the skill itself, and a missing one never fails `./init`.

## Hand edits

`tools/unslop/installed.json` records a digest of every file the install wrote. When a later install finds a file that differs from its record, it keeps that file, writes the new version to `tools/unslop/pending/<same path>`, and names both. `make check-extensions` keeps reporting it until it is merged or the edited file is deleted and `./init --extension unslop` is run again.

## What is in here

| File | What it is |
| --- | --- |
| `extension.json` | The manifest: what the catalogue shows, which keel schema it speaks, and the points it hooks |
| `init.py` | The entry point. At `init` it installs and projects; at `project` it rewrites its `AGENTS.md` block only |
| `hooks/check.py` | `check-unslop`: fails on a half-finished or out-of-date install, and reports a pending merge |
| `skill/` | Upstream `skills/unslop`, unmodified, at the commit in `UPSTREAM` |
| `NOTICE`, `LICENSE-unslop` | The credit and the CC BY 4.0 licence |
| `tests/` | The install path, run against a scratch project with a browser app |

To take a new upstream commit, replace `skill/` with that commit's `skills/unslop`, update `UPSTREAM`, and release a new version.

## The six obligations

An extension's entry point meets all six, and `slipwai extension check` says so:

1. **Idempotent**: running it twice does what running it once did.
2. **Non-fatal**: a tool it cannot install is reported, not fatal.
3. **Projects**: its `AGENTS.md` block is marker-fenced and replaced whole.
4. **Gated**: state that can go stale ships a check (`hooks/check.py`).
5. **Recovers**: every failure path names the command that fixes it.
6. **Merges**: a hand-edited file is merged, never overwritten.

The keel's conformance suite runs in a scratch project with no browser app, where this extension correctly refuses, so `tests/` covers the install path: `uv run --project <keel> --with pytest python -m pytest tests`.
