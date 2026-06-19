"""Multi-file (folder) skills, plus backward compatibility with legacy flat skills.

A skill is now either ~/.claude/skills/<id>/SKILL.md (with optional supporting
files) or a legacy ~/.claude/skills/<id>.md. Both must list, read, and delete
correctly, and a folder skill with supporting files must get its folder path
appended to the prompt so the agent can read those files on demand.
"""

from __future__ import annotations

import os
import json

import pytest

import backend.apps.skills.skills as skills_mod
from backend.apps.agents.manager.prompt.prompt_context import _resolve_attached_skills


@pytest.fixture
def skills_dir(tmp_path, monkeypatch):
    d = tmp_path / "skills"
    d.mkdir()
    monkeypatch.setattr(skills_mod, "SKILLS_DIR", str(d))
    monkeypatch.setattr(skills_mod, "INDEX_PATH", str(d / ".skills_index.json"))
    return d


def _write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def test_flat_skill_still_syncs(skills_dir):
    _write(str(skills_dir / "my-flat.md"), "do the flat thing")
    skills = {s.id: s for s in skills_mod._sync_skills()}
    assert "my-flat" in skills
    s = skills["my-flat"]
    assert s.content == "do the flat thing"
    assert s.dir_path == ""
    assert s.has_supporting_files is False


def test_folder_skill_syncs_with_supporting_files(skills_dir):
    base = skills_dir / "remotion"
    _write(str(base / "SKILL.md"), "---\nname: Remotion\ndescription: make videos\n---\nrender stuff")
    _write(str(base / "helper.py"), "print('hi')")
    skills = {s.id: s for s in skills_mod._sync_skills()}
    assert "remotion" in skills
    s = skills["remotion"]
    assert "render stuff" in s.content
    assert s.dir_path == str(base)
    assert s.has_supporting_files is True
    # Frontmatter fills name/description when the index hasn't catalogued it.
    assert s.name == "Remotion"
    assert s.description == "make videos"


def test_folder_skill_without_extra_files_flags_false(skills_dir):
    base = skills_dir / "solo"
    _write(str(base / "SKILL.md"), "just one file")
    s = {x.id: x for x in skills_mod._sync_skills()}["solo"]
    assert s.dir_path == str(base)
    assert s.has_supporting_files is False


@pytest.mark.asyncio
async def test_delete_removes_folder(skills_dir):
    base = skills_dir / "doomed"
    _write(str(base / "SKILL.md"), "x")
    _write(str(base / "data.txt"), "y")
    assert base.is_dir()
    await skills_mod.delete_skill("doomed")
    assert not base.exists()


@pytest.mark.asyncio
async def test_update_writes_folder_skill_md(skills_dir):
    base = skills_dir / "editable"
    _write(str(base / "SKILL.md"), "old body")
    from backend.apps.skills.models import SkillUpdate
    res = await skills_mod.update_skill("editable", SkillUpdate(content="new body", description="d"))
    assert res["ok"]
    with open(base / "SKILL.md", encoding="utf-8") as f:
        assert f.read() == "new body"
    assert res["skill"]["dir_path"] == str(base)


def test_injection_points_at_folder_for_supporting_files(skills_dir):
    base = skills_dir / "withfiles"
    _write(str(base / "SKILL.md"), "use the template")
    _write(str(base / "template.html"), "<html></html>")

    block = _resolve_attached_skills([{"id": "withfiles", "name": "WithFiles", "content": "use the template"}])
    assert "[Using skill: WithFiles]" in block
    assert str(base) in block
    assert "Read" in block  # tells the agent to read supporting files


def test_injection_no_folder_note_for_flat_skill(skills_dir):
    _write(str(skills_dir / "plain.md"), "plain content")
    block = _resolve_attached_skills([{"id": "plain", "name": "Plain", "content": "plain content"}])
    assert "[Using skill: Plain]" in block
    assert "supporting files" not in block.lower()
