"""The install path the keel's conformance cannot reach: its scratch project has no browser app, so the entry
point refuses there, correctly, and never installs. These run it in the same scratch project with one.

Run with the keel importable: `uv run --project <keel> pytest tests`.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from slipwai.conformance.extension import scratch, snapshot

PACKAGE = Path(__file__).resolve().parents[1]
COMMIT = (PACKAGE / "UPSTREAM").read_text(encoding="utf-8").split()[1]


@pytest.fixture
def project(tmp_path: Path) -> Path:
    root = scratch(tmp_path, "unslop", PACKAGE)
    (root / "apps/web").mkdir(parents=True)
    (root / "project.json").write_text(json.dumps(
        {"deployables": {"web": {"path": "apps/web", "capabilities": ["frontend"]}}}) + "\n", encoding="utf-8")
    return root


def run(root: Path, script: str = "init.py", **environment: str) -> subprocess.CompletedProcess:
    env = {**os.environ, "SLIPWAI_INTEGRATION": "claude", **environment}
    return subprocess.run([sys.executable, str(root / "scripts/extensions/unslop" / script)],
                          capture_output=True, text=True, cwd=root, env=env, timeout=120, check=False)


def test_installs_the_skill_its_pictures_and_the_pointer(project: Path) -> None:
    done = run(project)
    assert done.returncode == 0, done.stderr
    skill = (project / "skills/unslop/SKILL.md").read_text(encoding="utf-8")
    assert "\ncapabilities: frontend\n---\n" in skill
    assert "Damir Sokolovsky" in skill
    assert "](tools/unslop/refs/story-dashboard-frames.webp)" in skill
    assert "](tools/unslop/refs/meadow-3d.webp)" in (project / "skills/unslop/references/refs.md").read_text()
    assert not list((project / "skills/unslop").rglob("*.webp"))
    assert len(list((project / "tools/unslop/refs").glob("*.webp"))) == 5
    assert "<!-- extension:unslop:begin -->" in (project / "AGENTS.md").read_text(encoding="utf-8")
    assert "unslop" in json.loads((project / ".slipwai/extensions.json").read_text())["extensions"]
    held = json.loads((project / "tools/unslop/installed.json").read_text())
    assert held["commit"] == COMMIT and "skills/unslop/SKILL.md" in held["files"]
    assert "Claude Code: .claude/skills/unslop/" in done.stdout


def test_reaches_the_harness_through_the_projection(project: Path) -> None:
    run(project)
    projected = project / ".claude/skills/unslop/SKILL.md"
    assert projected.is_file(), "make agents' projector did not carry the skill to Claude Code"
    assert (project / ".claude/skills/unslop/scripts/snapshot.mjs").is_file()


def test_twice_is_once(project: Path) -> None:
    run(project)
    first = snapshot(project)
    run(project)
    assert snapshot(project) == first


def test_a_hand_edit_is_kept_and_the_new_copy_waits_beside_it(project: Path) -> None:
    run(project)
    skill = project / "skills/unslop/SKILL.md"
    edited = skill.read_text(encoding="utf-8") + "\nOur own rule.\n"
    skill.write_text(edited, encoding="utf-8")
    done = run(project)
    assert skill.read_text(encoding="utf-8") == edited
    waiting = project / "tools/unslop/pending/skills/unslop/SKILL.md"
    assert waiting.is_file() and "Our own rule." not in waiting.read_text(encoding="utf-8")
    assert "skills/unslop/SKILL.md was edited by hand" in done.stdout
    after_edit = snapshot(project)
    run(project)
    assert snapshot(project) == after_edit
    skill.unlink()
    run(project)
    assert "Our own rule." not in skill.read_text(encoding="utf-8")
    assert not (project / "tools/unslop/pending").exists()


def test_a_file_already_there_before_any_install_is_a_persons(project: Path) -> None:
    mine = project / "skills/unslop/SKILL.md"
    mine.parent.mkdir(parents=True)
    mine.write_text("my own unslop\n", encoding="utf-8")
    run(project)
    assert mine.read_text(encoding="utf-8") == "my own unslop\n"
    assert (project / "tools/unslop/pending/skills/unslop/SKILL.md").is_file()


def test_with_nothing_on_path_it_installs_and_says_what_is_off(project: Path) -> None:
    done = run(project, PATH="")
    assert done.returncode == 0
    assert (project / "skills/unslop/SKILL.md").is_file()
    assert "`node` was not found" in done.stdout and "`ffmpeg` was not found" in done.stdout


def test_a_reprojection_refreshes_the_block_and_installs_nothing(project: Path) -> None:
    done = run(project, SLIPWAI_POINT="project")
    assert done.returncode == 0
    assert not (project / "skills/unslop").exists()
    assert "extension:unslop" not in (project / "AGENTS.md").read_text(encoding="utf-8")
    run(project)
    agents = project / "AGENTS.md"
    agents.write_text(agents.read_text(encoding="utf-8").replace("## unslop", "## unslop, stale"), encoding="utf-8")
    run(project, SLIPWAI_POINT="project")
    text = agents.read_text(encoding="utf-8")
    assert "## unslop\n" in text and "stale" not in text and text.count("extension:unslop:begin") == 1


def test_no_browser_app_is_refused_with_the_way_on(project: Path) -> None:
    (project / "project.json").write_text("{}\n", encoding="utf-8")
    done = run(project)
    assert done.returncode == 0
    assert "slipwai add-frontend web" in done.stderr
    assert not (project / "skills/unslop").exists()


def test_the_check(project: Path) -> None:
    (project / ".slipwai").mkdir(exist_ok=True)
    (project / ".slipwai/extensions.json").write_text(json.dumps({"schemaVersion": 1, "extensions": ["unslop"]}))
    assert run(project, "hooks/check.py").returncode == 0
    assert run(project, "hooks/check.py", UNSLOP_REQUIRE="1").returncode == 1
    run(project)
    passed = run(project, "hooks/check.py")
    assert passed.returncode == 0 and COMMIT[:7] in passed.stdout
    record = project / "tools/unslop/installed.json"
    held = json.loads(record.read_text())
    record.write_text(json.dumps({**held, "commit": "0" * 40}))
    stale = run(project, "hooks/check.py")
    assert stale.returncode == 1 and "--extension unslop" in stale.stderr
    record.write_text(json.dumps(held))
    (project / "tools/unslop/refs/meadow-3d.webp").unlink()
    assert run(project, "hooks/check.py").returncode == 1
