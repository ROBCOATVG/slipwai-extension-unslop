#!/usr/bin/env python3
"""Fail when the skill this extension installs is adopted and half there, or is not the pinned one.

`skills/unslop/` and `tools/unslop/` are ignored by Git — installed by `./init --extension unslop` from the copy
this package bundles — so a fresh clone and every CI runner has the election and not the skill. **State that can
go stale and that nothing checks is state nobody trusts and everybody rebuilds**, which is the obligation this
file answers (`docs/extensions.md`).

Four states, and each is said rather than guessed at:

* **Not adopted.** No `.slipwai/extensions.json` naming `unslop`, or no browser app to design for: nothing to
  check, and `make verify` is not the place to argue about an optional tool.
* **Adopted, not installed here.** Reported as *skipped* by default, because a clone that has not run `./init`
  is the ordinary case and not a fault — and as a *failure* where `UNSLOP_REQUIRE=1`, which is what to set
  wherever the skill is expected to be present.
* **Installed, and not this package's.** `tools/unslop/installed.json` names a different upstream commit than
  this package bundles, or a file it recorded is gone: the package was updated and `./init` was not run, or the
  install did not finish. A failure, with the command that fixes it.
* **Installed, with a newer copy waiting.** A file a person edited was kept and this version's copy is under
  `tools/unslop/pending/`. Said, never failed: merging it is a person's call, and the kept file still works.

Never fatal on its own terms beyond that: `scripts/extensions/hooks.py check --fatal` is what makes a `check`
hook a gate, and `make verify` is the only caller that passes it.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve()
KEY = "unslop"
UPSTREAM = (HERE.parents[1] / "UPSTREAM").read_text(encoding="utf-8").split()


def project_root(script: Path) -> Path:
    for candidate in script.parents:
        if (candidate / "project.json").is_file():
            return candidate
    return script.parents[4]


ROOT = project_root(HERE)
DELIVERY = HERE.parents[4]
INIT = "./init" if DELIVERY == ROOT else f"./{DELIVERY.relative_to(ROOT).as_posix()}/init"
SKILL_MD = DELIVERY / "skills" / KEY / "SKILL.md"
RECORD = ROOT / "tools" / KEY / "installed.json"
PENDING = ROOT / "tools" / KEY / "pending"
ELECTED = ROOT / ".slipwai/extensions.json"


def adopted() -> bool:
    """Whether this project elected `unslop`. Absent or unreadable is *not adopted*: a project that never
    asked for an optional tool is not a project with a problem."""
    try:
        held = json.loads(ELECTED.read_text(encoding="utf-8"))
    except (OSError, ValueError, UnicodeDecodeError):
        return False
    named = held.get("extensions") if isinstance(held, dict) else held
    return KEY in named if isinstance(named, list | dict) else False


def browser_apps() -> list[str]:
    """The deployables that declare a `frontend` capability and are still here. None is nothing to design
    for, which is the same answer `init.py` gives."""
    try:
        deployables = json.loads((ROOT / "project.json").read_text(encoding="utf-8")).get("deployables")
    except (OSError, ValueError, UnicodeDecodeError):
        return []
    if not isinstance(deployables, dict):
        return []
    return [str(one.get("path")) for one in deployables.values()
            if isinstance(one, dict) and "frontend" in (one.get("capabilities") or [])
            and (ROOT / str(one.get("path", ""))).is_dir()]


def record() -> dict | None:
    try:
        held = json.loads(RECORD.read_text(encoding="utf-8"))
    except (OSError, ValueError, UnicodeDecodeError):
        return None
    return held if isinstance(held, dict) else None


def main() -> int:
    if not adopted():
        print("check-unslop: not adopted here; nothing to check")
        return 0
    if not browser_apps():
        print("check-unslop: adopted, and this project has no browser app to design for; nothing to check")
        return 0
    if not SKILL_MD.parent.is_dir() and not RECORD.is_file():
        required = os.environ.get("UNSLOP_REQUIRE") == "1"
        said = ("check-unslop: the skill is not installed here. skills/unslop/ is ignored by Git, so a fresh "
                "clone and a CI runner have the election and not the skill.\n"
                "Install it:\n"
                f"  {INIT} --extension unslop")
        print(said, file=sys.stderr if required else sys.stdout)
        return 1 if required else 0
    held = record()
    if not SKILL_MD.is_file() or held is None:
        print("check-unslop: the skill is here in part (no SKILL.md, or no tools/unslop/installed.json), so the "
              "install did not finish.\n"
              "Install it again:\n"
              f"  {INIT} --extension unslop", file=sys.stderr)
        return 1
    if held.get("commit") != UPSTREAM[1]:
        print(f"check-unslop: the installed skill is from {str(held.get('commit'))[:7]}, and this package bundles "
              f"{UPSTREAM[1][:7]}: the package was updated and the project was not.\n"
              "Update it:\n"
              f"  {INIT} --extension unslop", file=sys.stderr)
        return 1
    files = held.get("files")
    files = files if isinstance(files, dict) else {}
    missing = sorted(shown for shown in files if not (ROOT / shown).is_file())
    if missing:
        print(f"check-unslop: {len(missing)} installed file(s) are missing, the first {missing[0]}.\n"
              "Install it again:\n"
              f"  {INIT} --extension unslop", file=sys.stderr)
        return 1
    waiting = sorted(p.relative_to(PENDING).as_posix() for p in PENDING.rglob("*") if p.is_file()) \
        if PENDING.is_dir() else []
    for shown in waiting:
        print(f"check-unslop: {shown} was edited by hand and kept; this version's copy is at "
              f"tools/unslop/pending/{shown}. Merge the two, or delete yours and run `{INIT} --extension unslop`")
    print(f"check-unslop: skills/unslop/ is {UPSTREAM[0]} {UPSTREAM[1][:7]}, as this package bundles")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
