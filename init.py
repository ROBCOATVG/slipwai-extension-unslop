#!/usr/bin/env python3
"""`./init --extension unslop`: install Damir Sokolovsky's unslop skill into `skills/`, and point the agent at it.

unslop (https://github.com/heydamir/unslop, CC BY 4.0) is an agent skill that turns AI-looking UI into a
designed interface: an audit of the usual tells, a direction drawn from the product, then ordered passes over
spacing, colour, icons, copy, type, layout, details, visuals and motion. Upstream installs it for Claude Code
and Codex. Here it goes into the project's root `skills/`, the canonical catalogue `make agents` projects
into every harness with a `skillsDir` and `check-agents` holds the projections to, so every harness this
project has gets it, and one added later gets it on the next `make agents`.

The skill is bundled with this package, pinned to the upstream commit `UPSTREAM` names, rather than fetched
here: the release digest and the publisher's trust cover it, and it installs offline and in CI. It is the
upstream text with three changes, which `NOTICE` lists: `SKILL.md` declares `capabilities: frontend`, so
`check-agents` names the skill if the browser app ever goes; the five reference pictures are installed under
`tools/unslop/refs/` instead of beside the text, because the projection copies a skill as text and a picture
is not text; and the links to them say so.

Both directories are ignored by Git (see `ignore` in `catalog.json`): installed, not maintained here, and
reproducible from this one command. `tools/unslop/installed.json` records a digest of every file this script
wrote, so a second run can tell its own copy from one a person edited. An edited file is kept, the new
version goes to `tools/unslop/pending/` under the same path, and a line names both.

A project with no browser app has nothing for it to design, so it is refused politely with the command that
would change that. Never fails `./init`: Node, Playwright and ffmpeg are only needed for the skill's optional
steps (a snapshot of a live site, a story video), and a missing one is reported, not fatal. See
docs/extensions.md for what every extension's `init.py` owes.

At `project` (every `make agents`) it rewrites its `AGENTS.md` block and installs nothing.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from guidance import harness_rows, installed_block, installed_harnesses, record_extension, replace_block  # noqa: E402

KEY = "unslop"
HERE = Path(__file__).resolve().parent
BUNDLE = HERE / "skill"
UPSTREAM = (HERE / "UPSTREAM").read_text(encoding="utf-8").split()
# What the projection would refuse to read as text, so it is installed outside `skills/`.
PICTURES = {".webp", ".png", ".jpg", ".jpeg", ".gif", ".avif", ".mp4"}


def project_root(script: Path, depth: int) -> Path:
    """The repository root: the nearest directory above this script holding `project.json`."""
    for candidate in script.parents:
        if (candidate / "project.json").is_file():
            return candidate
    return script.parents[depth]


ROOT = project_root(Path(__file__).resolve(), 3)

# Where `./init` actually is, from the repository root: beside this script's own tree at the root in a
# generated project, and under `layout.delivery` where the method was installed beside an existing codebase.
# Derived rather than written, because "run `./init --extension …`" is advice nobody can follow when the
# file is `./delivery/init` — the first real adoption to meet it typed `./init` four times.
DELIVERY = Path(__file__).resolve().parents[3]
INIT = "./init" if DELIVERY == ROOT else f"./{DELIVERY.relative_to(ROOT).as_posix()}/init"
SKILL_DIR = DELIVERY / "skills" / KEY
SKILL_AT = SKILL_DIR.relative_to(ROOT).as_posix()
TOOLS = ROOT / "tools" / KEY
REFS_AT = "tools/unslop/refs"
RECORD = TOOLS / "installed.json"
PENDING = TOOLS / "pending"
MARKER_BEGIN = "<!-- extension:unslop:begin -->"
MARKER_END = "<!-- extension:unslop:end -->"
GUIDANCE = f"""
{MARKER_BEGIN}
## unslop
`{SKILL_AT}/` is Damir Sokolovsky's unslop skill (CC BY 4.0; keep its credit in any copy): an audit of the
tells that make a screen look AI-generated, a direction drawn from the product, then ordered passes over
spacing, colour, icons, copy, type, layout, details, visuals and motion. Start it with `/unslop` (`$unslop`
in Codex) or a plain request to polish a screen; a harness with no skills folder reads `{SKILL_AT}/SKILL.md`
directly. Its reference pictures are at `{REFS_AT}/`, and the paths the skill gives them are from the
repository root.

**It is taste, not a gate.** ux-gates, where it is adopted, measures a screen; unslop decides how it should
look. `docs/design.md` is still the page every slice with a screen reads first, and where the two disagree
the page wins: write a direction that changes it into the page, in the same commit as the tokens.

**With a person in the session**, run it as the skill says: audit, propose the direction and stop for their
answer, then work the passes. Ask before every image generation that costs money. If a screen is already
good, say so and change nothing.

**As a delegate working a slice** (nobody to answer), when the slice changes a screen:
- Do not stop for the direction. Write it, with the audit that led to it, as an entry in the slice's
  `specs/<feature>/decisions.md`, then work the passes.
- Generate no image that costs money and render no story video. Where the skill would generate a picture,
  leave a slot of the right size and write its prompt into the same entry.
- A matter of taste is a decision with its reason in that entry, never a park: a person reviews it on the
  board and can reverse it there.

**Check you can reach it before you trust it.** `{SKILL_AT}/` and `{REFS_AT}/` are ignored by Git and
installed by this extension, so a fresh clone, a container or a CI runner has this pointer and not the skill.
When `{SKILL_AT}/SKILL.md` is absent, say so and work from `docs/design.md` alone; `{INIT} --extension unslop`
restores it. Its optional steps need Node and Playwright (`scripts/snapshot.mjs`) and ffmpeg as well
(`scripts/story.mjs`). Where Playwright is not in the project but ux-gates installed one, run them with
`NODE_PATH=tools/ux-gates/node_modules`.
{MARKER_END}
"""


def browser_apps() -> list[str]:
    """The deployables that declare a `frontend` capability and are still here."""
    manifest = ROOT / "project.json"
    if not manifest.is_file():
        return []
    deployables = json.loads(manifest.read_text(encoding="utf-8")).get("deployables")
    if not isinstance(deployables, dict):
        return []
    return [
        str(deployable.get("path"))
        for deployable in deployables.values()
        if isinstance(deployable, dict)
        and "frontend" in deployable.get("capabilities", [])
        and (ROOT / str(deployable.get("path", ""))).is_dir()
    ]


def relinked(text: str) -> str:
    """The links to a reference picture, pointed at where it is installed."""
    return re.sub(r"\]\((?:references/)?refs/([^)\s]+)\)", rf"]({REFS_AT}/\1)", text)


def with_capability(skill_md: str) -> str:
    """Declare `capabilities: frontend`, so `check-agents` names the skill if the browser app ever goes."""
    if not skill_md.startswith("---\n"):
        return skill_md
    front, separator, rest = skill_md[4:].partition("\n---\n")
    if not separator or "\ncapabilities:" in f"\n{front}":
        return skill_md
    return f"---\n{front}\ncapabilities: frontend\n---\n{rest}"


def planned() -> dict[Path, bytes]:
    """Every file this version installs, where it goes, and what it holds."""
    files: dict[Path, bytes] = {}
    for source in sorted(BUNDLE.rglob("*")):
        if not source.is_file() or "__pycache__" in source.parts:
            continue
        if source.suffix.lower() in PICTURES:
            files[ROOT / REFS_AT / source.name] = source.read_bytes()
            continue
        relative = source.relative_to(BUNDLE)
        text = source.read_text(encoding="utf-8")
        if source.suffix == ".md":
            text = relinked(text)
        if relative.as_posix() == "SKILL.md":
            text = with_capability(text)
        files[SKILL_DIR / relative] = text.encode("utf-8")
    return files


def digest(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def recorded() -> dict[str, str]:
    """What the last install wrote, by path from the root. Absent or unreadable is nothing recorded, which
    makes every file that differs a person's — the safe way to be wrong."""
    try:
        held = json.loads(RECORD.read_text(encoding="utf-8"))
    except (OSError, ValueError, UnicodeDecodeError):
        return {}
    files = held.get("files") if isinstance(held, dict) else None
    return {str(path): str(sha) for path, sha in files.items()} if isinstance(files, dict) else {}


def write(path: Path, content: bytes) -> None:
    if path.is_file() and path.read_bytes() == content:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)


def install() -> list[str]:
    """Put this version in place, merging rather than overwriting. Returns one line per thing worth saying."""
    before = recorded()
    after: dict[str, str] = {}
    kept: list[str] = []
    said: list[str] = []
    files = planned()
    for path, content in files.items():
        shown = path.relative_to(ROOT).as_posix()
        current = path.read_bytes() if path.is_file() else None
        if current is not None and current != content and digest(current) != before.get(shown):
            kept.append(shown)
            write(PENDING / shown, content)
            if shown in before:
                after[shown] = before[shown]
            continue
        write(path, content)
        after[shown] = digest(content)
    shipped = {path.relative_to(ROOT).as_posix() for path in files}
    for shown, sha in before.items():
        if shown in shipped:
            continue
        gone = ROOT / shown
        if gone.is_file() and digest(gone.read_bytes()) != sha:
            said.append(f"{shown} is no longer part of unslop and was edited by hand, so it was left; delete it "
                        "when you are done with it")
        elif gone.is_file():
            gone.unlink()
    for stale in sorted(PENDING.rglob("*")) if PENDING.is_dir() else []:
        if stale.is_file() and stale.relative_to(PENDING).as_posix() not in kept:
            stale.unlink()
    if PENDING.is_dir():
        for folder in sorted((p for p in PENDING.rglob("*") if p.is_dir()), reverse=True):
            if not any(folder.iterdir()):
                folder.rmdir()
        if not any(PENDING.iterdir()):
            PENDING.rmdir()
    for shown in kept:
        said.append(f"{shown} was edited by hand, so it was kept, and this version's copy is at "
                    f"tools/unslop/pending/{shown}. Merge the two by hand, or delete yours and run "
                    f"`{INIT} --extension unslop` again")
    held = {"upstream": UPSTREAM[0], "commit": UPSTREAM[1], "files": dict(sorted(after.items()))}
    write(RECORD, (json.dumps(held, indent=2) + "\n").encode("utf-8"))
    return said


def reproject() -> None:
    """`./init` projected `skills/` before this ran; the new skill has to reach the harness too.

    `./init` names the harness it chose in `SLIPWAI_INTEGRATION`; run by hand later, the projector reads
    the one Spec Kit recorded. Either way a failure is reported by the projector and `make agents` retries.
    """
    projector = DELIVERY / "scripts/agents/project.py"
    if not projector.is_file():
        return
    chosen = os.environ.get("SLIPWAI_INTEGRATION", "")
    subprocess.run([sys.executable, str(projector), *([chosen] if chosen else [])], cwd=ROOT, check=False)


def reach() -> list[str]:
    """One line per harness here: where it finds the skill, or that it reads it through `AGENTS.md`."""
    keys = installed_harnesses()
    if not keys:
        return [f"no harness is recorded here, so the skill is only at {SKILL_AT}/ for now; "
                f"`{INIT} --integration <agent>` records one and `make agents` then gives it the skill"]
    rows = harness_rows()
    lines = []
    for key in keys:
        row = rows.get(key, {})
        name = row.get("name", key)
        where = row.get("skillsDir")
        lines.append(f"{name}: {where}/{KEY}/" if where
                     else f"{name}: no skills folder, so it reads {SKILL_AT}/SKILL.md through AGENTS.md")
    return lines


def resolves(module: str, node_path: Path | None) -> bool:
    """Whether Node finds `module` from the root, as the skill's scripts look for it."""
    environment = {**os.environ}
    if node_path is not None:
        environment["NODE_PATH"] = str(node_path)
    try:
        found = subprocess.run(["node", "-e", f"require.resolve({json.dumps(module)})"], cwd=ROOT,
                               env=environment, capture_output=True, timeout=10, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return False
    return found.returncode == 0


def optional_steps() -> list[str]:
    """What is missing for the skill's optional steps. The skill itself needs none of it."""
    lines = []
    if shutil.which("node") is None:
        lines.append("`node` was not found, so the live-site snapshot and the story video are off; install Node.js "
                     "(`brew install node`) to turn them on")
    else:
        ux_gates = ROOT / "tools/ux-gates/node_modules"
        names = ("playwright", "playwright-core")
        here = any(resolves(name, None) for name in names)
        if not here and ux_gates.is_dir() and any(resolves(name, ux_gates) for name in names):
            lines.append("Playwright comes from ux-gates here: run the skill's scripts with "
                         "`NODE_PATH=tools/ux-gates/node_modules`")
        elif not here:
            lines.append("Playwright is missing, so the live-site snapshot and the story video are off; add it with "
                         "`npm install -D playwright && npx playwright install chromium`")
    if shutil.which("ffmpeg") is None:
        lines.append("`ffmpeg` was not found, so the story video is off; install it (`brew install ffmpeg`) to turn "
                     "it on")
    return lines


def project_guidance() -> None:
    """Record this election and make its factory-owned guidance region current."""
    record_extension(KEY)
    replace_block(KEY, GUIDANCE)


def main() -> int:
    if os.environ.get("SLIPWAI_POINT") == "project":
        # A re-projection is not an election: refresh the block where there is one, and install nothing.
        if installed_block(KEY) is not None:
            replace_block(KEY, GUIDANCE)
        return 0
    if not browser_apps():
        print(
            "unslop designs screens, and this project has no browser app for it to design: nothing was "
            "installed and AGENTS.md is unchanged.\n"
            "Add one first, then adopt it here:\n"
            "  slipwai add-frontend web\n"
            f"  {INIT} --extension unslop",
            file=sys.stderr,
        )
        return 0
    merged = install()
    project_guidance()
    reproject()
    print(f"unslop installed at {SKILL_AT}/ and its pictures at {REFS_AT}/ (both ignored by Git; "
          f"`{INIT} --extension unslop` reinstalls them), from {UPSTREAM[0]} {UPSTREAM[1][:7]}.")
    for line in [*reach(), *merged, *optional_steps()]:
        print(f"  {line}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
