import shutil
from pathlib import Path
from typing import Optional, List


SKILL_SOURCE = Path(__file__).resolve().parents[1] / "skills/synctake/SKILL.md"


def install_skill(target_framework: str = "all", project_root: str | Path = ".") -> List[Path]:
    """
    Installs the SyncTake skill file into the user's project for coding agents
    (Claude Code, Cursor, Antigravity, OpenCode, Codex).
    """
    root = Path(project_root).resolve()
    if not SKILL_SOURCE.is_file():
        raise FileNotFoundError(f"SKILL.md source file not found at {SKILL_SOURCE}")

    installed_paths = []
    skill_content = SKILL_SOURCE.read_text(encoding="utf-8")

    # 1. Standard Agent Skills (.agents/skills/synctake/SKILL.md)
    if target_framework in ("all", "agents", "antigravity"):
        p = root / ".agents/skills/synctake/SKILL.md"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(skill_content, encoding="utf-8")
        installed_paths.append(p)

    # 2. Claude Code (.claude/skills/synctake/SKILL.md)
    if target_framework in ("all", "claude"):
        p = root / ".claude/skills/synctake/SKILL.md"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(skill_content, encoding="utf-8")
        installed_paths.append(p)

    # 3. Cursor Rules (.cursor/rules/synctake.mdc)
    if target_framework in ("all", "cursor"):
        p = root / ".cursor/rules/synctake.mdc"
        p.parent.mkdir(parents=True, exist_ok=True)
        cursor_content = f"---\ndescription: SyncTake automated video walkthrough creation skill\nglobs: *\n---\n\n{skill_content}"
        p.write_text(cursor_content, encoding="utf-8")
        installed_paths.append(p)

    return installed_paths
