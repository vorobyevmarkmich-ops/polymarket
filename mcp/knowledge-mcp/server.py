from __future__ import annotations

import logging
import os
from pathlib import Path

from mcp.server.fastmcp import FastMCP

LOGGER = logging.getLogger("knowledge-mcp")

ROOT = Path(__file__).resolve().parents[2]
SKILLS_DIR = ROOT / "skills"
CORE_DOCS = {
    "project-docs": ROOT / "PROJECT_DOCS.md",
    "agents": ROOT / "agents.md",
    "stack": ROOT / "STACK.md",
    "architecture": ROOT / "ARCHITECTURE.md",
}

mcp = FastMCP("knowledge-mcp", json_response=True)


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _skill_dirs() -> list[Path]:
    if not SKILLS_DIR.exists():
        return []
    return sorted(path for path in SKILLS_DIR.iterdir() if path.is_dir())


def _skill_name_to_path(name: str) -> Path:
    path = SKILLS_DIR / name / "SKILL.md"
    if not path.exists():
        raise ValueError(f"Unknown skill: {name}")
    return path


def _doc_name_to_path(name: str) -> Path:
    try:
        path = CORE_DOCS[name]
    except KeyError as exc:
        raise ValueError(
            f"Unknown document: {name}. Use one of: {', '.join(sorted(CORE_DOCS))}"
        ) from exc
    if not path.exists():
        raise ValueError(f"Document is configured but missing on disk: {name}")
    return path


@mcp.tool()
def list_project_documents() -> list[dict[str, str]]:
    """List the core local reference documents available in this project."""
    return [
        {"name": name, "path": str(path), "exists": str(path.exists()).lower()}
        for name, path in CORE_DOCS.items()
    ]


@mcp.tool()
def read_project_document(name: str, max_chars: int = 20000) -> dict[str, str]:
    """Read a core project document by name."""
    path = _doc_name_to_path(name)
    content = _read_text(path)
    return {
        "name": name,
        "path": str(path),
        "content": content[:max_chars],
        "truncated": str(len(content) > max_chars).lower(),
    }


@mcp.tool()
def search_project_documents(query: str, limit: int = 20) -> list[dict[str, str | int]]:
    """Search the core local project documents for a text query."""
    query_lower = query.lower()
    results: list[dict[str, str | int]] = []

    for name, path in CORE_DOCS.items():
        if not path.exists():
            continue
        lines = _read_text(path).splitlines()
        for lineno, line in enumerate(lines, start=1):
            if query_lower in line.lower():
                results.append(
                    {
                        "document": name,
                        "path": str(path),
                        "line": lineno,
                        "text": line.strip(),
                    }
                )
                if len(results) >= limit:
                    return results

    return results


@mcp.tool()
def list_project_skills() -> list[dict[str, str]]:
    """List the local project skills stored under the project's skills directory."""
    results: list[dict[str, str]] = []
    for skill_dir in _skill_dirs():
        skill_file = skill_dir / "SKILL.md"
        if skill_file.exists():
            results.append({"name": skill_dir.name, "path": str(skill_file)})
    return results


@mcp.tool()
def read_project_skill(name: str, max_chars: int = 20000) -> dict[str, str]:
    """Read a local project skill file by skill name."""
    path = _skill_name_to_path(name)
    content = _read_text(path)
    return {
        "name": name,
        "path": str(path),
        "content": content[:max_chars],
        "truncated": str(len(content) > max_chars).lower(),
    }


@mcp.resource("project-doc://document/{name}")
def project_document_resource(name: str) -> str:
    """Read a core local project document as a resource."""
    return _read_text(_doc_name_to_path(name))


@mcp.resource("project-doc://skill/{name}")
def project_skill_resource(name: str) -> str:
    """Read a local project skill file as a resource."""
    return _read_text(_skill_name_to_path(name))


@mcp.prompt()
def choose_project_context(task: str) -> str:
    """Generate a short guidance prompt for selecting the right local references."""
    return f"""You are working on this Pumpfun project task: {task}

Before making changes, consult the local project references that best match the task:
- Use PROJECT_DOCS.md for product logic, terminology, user flow, fees, risks, and disclaimers.
- Use STACK.md for the target stack and infrastructure choices.
- Use ARCHITECTURE.md for service boundaries, data flow, and storage rules.
- Use agents.md for the current working conventions, available skills, and MCP/plugin guidance.
- Use local project skills when the task clearly matches one of them.
"""


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    transport = os.getenv("MCP_TRANSPORT", "stdio")
    LOGGER.info("Starting knowledge-mcp with transport=%s", transport)
    mcp.run(transport=transport)
