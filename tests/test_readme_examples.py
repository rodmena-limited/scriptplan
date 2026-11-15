"""The README's examples, run as a reader would run them.

The example project stopped parsing in 0.10.3, when a scoped reference in it
became an error, and nothing noticed: no test read the README. These tests cut
the examples out of the file and run them unchanged.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
README = (REPO_ROOT / "README.md").read_text()


def block_after(heading: str, fence: str) -> str:
    section = README[README.index(heading) :]
    found = re.search(rf"^```{fence}\n(.*?)^```$", section, re.M | re.S)
    assert found is not None, f"no ```{fence} block after {heading!r}"
    return found.group(1)


def run(args: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    env = dict(os.environ, PYTHONPATH=str(REPO_ROOT) + os.pathsep + os.environ.get("PYTHONPATH", ""))
    return subprocess.run([sys.executable, *args], capture_output=True, text=True, env=env, cwd=str(cwd), timeout=300)


def test_the_example_project_gives_the_result_the_readme_prints(tmp_path: Path) -> None:
    section = README[README.index("## Example project") :]
    blocks = re.findall(r"^```\n(.*?)^```$", section, re.M | re.S)
    project, result = blocks[0], blocks[1]
    (tmp_path / "example.tjp").write_text(project)
    done = run(["-m", "scriptplan.cli.plan", "report", "--csv", "example.tjp"], tmp_path)
    assert done.returncode == 0, done.stdout + done.stderr
    rows = re.findall(r"^(\S+):\s+(\S+) -> (\S+)$", result, re.M)
    assert len(rows) == 3
    for task, start, end in rows:
        assert f"{task},{start},{end}" in done.stdout, done.stdout


def test_the_python_example_prints_project_time(tmp_path: Path) -> None:
    (tmp_path / "example.py").write_text(block_after("## Python API", "python"))
    (tmp_path / "project.tjp").write_text(
        'project p "P" 2026-06-01 +1m { timezone "Europe/London" }\n'
        'resource r "R" { workinghours mon - sun 00:00 - 24:00 }\n'
        'task t "T" { effort 2h allocate r start 2026-06-02-00:00 }\n'
    )
    done = run(["example.py"], tmp_path)
    assert done.returncode == 0, done.stdout + done.stderr
    assert "t: 2026-06-02 00:00:00 -> 2026-06-02 02:00:00" in done.stdout


def test_the_command_line_examples_run(tmp_path: Path) -> None:
    (tmp_path / "project.tjp").write_text(
        'project p "P" 2024-01-01 +1m { timezone "Etc/UTC" }\n'
        'resource r "R" {}\n'
        'task project "Project" { task task1 "T1" { effort 5d allocate r } }\n'
    )
    as_json = run(["-m", "scriptplan.cli.plan", "report", "project.tjp"], tmp_path)
    assert as_json.returncode == 0, as_json.stderr
    # The README's sample row, and the keys it shows.
    assert '"id": "project.task1"' in as_json.stdout
    assert '"start": "2024-01-01-09:00"' in as_json.stdout
    assert '"end": "2024-01-05-17:00"' in as_json.stdout
    assert re.search(r'"report_id": "[0-9a-f]{64}"', as_json.stdout)
    assert "{" not in as_json.stderr
    as_csv = run(["-m", "scriptplan.cli.plan", "report", "--csv", "project.tjp"], tmp_path)
    assert "project.task1,2024-01-01-09:00,2024-01-05-17:00" in as_csv.stdout
    # Nothing is left beside the project file.
    assert sorted(p.name for p in tmp_path.iterdir()) == ["project.tjp"]
