from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _recipe_lines(name: str) -> list[str]:
    lines = (ROOT / "Justfile").read_text(encoding="utf-8").splitlines()
    marker = f"{name}:"
    start = lines.index(marker) + 1
    body: list[str] = []
    for line in lines[start:]:
        if line and not line[0].isspace() and line.endswith(":"):
            break
        if line.strip():
            body.append(line.strip())
    return body


def test_reusable_ci_installs_the_python_test_environment() -> None:
    requirements = {
        line.strip()
        for line in (ROOT / "requirements.txt").read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    }
    assert "-e ." in requirements
    assert "pytest" in requirements


def test_test_recipe_does_not_require_uv_after_pip_provisioning() -> None:
    recipe = _recipe_lines("test")
    assert "python -m pytest -q" in recipe
    assert all(not line.startswith("uv ") for line in recipe)
