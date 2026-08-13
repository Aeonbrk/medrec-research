"""Build and smoke-test the installed wheel without a Node.js runtime."""

from __future__ import annotations

import argparse
import os
import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory
from zipfile import ZipFile


def _run(command: list[str], *, cwd: Path, env: dict[str, str] | None = None) -> None:
    subprocess.run(command, cwd=cwd, env=env, check=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--uv", default="uv")
    arguments = parser.parse_args()
    root = Path(__file__).parents[2]

    with TemporaryDirectory(prefix="medrec-wheel-") as directory:
        temporary = Path(directory)
        distribution = temporary / "dist"
        _run(
            [arguments.uv, "build", "--wheel", "--out-dir", str(distribution), str(root)],
            cwd=temporary,
        )
        wheel = next(distribution.glob("medrec_research-*.whl"))
        with ZipFile(wheel) as archive:
            names = set(archive.namelist())
            resources = {
                name.removeprefix("medrec_research/web/")
                for name in archive.namelist()
                if name.startswith("medrec_research/web/")
            }
        assert "index.html" in resources
        assert "__init__.py" in resources
        assert "GEIST-OFL-1.1.txt" in resources
        assert any(name.startswith("assets/") and name.endswith(".js") for name in resources)
        assert any(name.startswith("assets/") and name.endswith(".css") for name in resources)
        assert len([name for name in resources if name.endswith(".woff2")]) == 2
        assert "medrec_research/resources/execution-declarations.toml" in names

        environment = temporary / "venv"
        _run([arguments.uv, "venv", "--python", "3.11", str(environment)], cwd=temporary)
        python = environment / "bin/python"
        _run(
            [arguments.uv, "pip", "install", "--python", str(python), str(wheel)],
            cwd=temporary,
        )
        smoke = """
import http.client
import re
from datetime import UTC, datetime
from pathlib import Path
from threading import Thread

from medrec_research.harness import create_harness_server
from medrec_research.project_status import ProjectStatus

status_path = Path(__import__('sys').argv[1])
snapshot = ProjectStatus.from_json(status_path.read_text(encoding='utf-8'))
server = create_harness_server(
    status_path=status_path,
    expected_authorities=snapshot.authorities,
    clock=lambda: datetime(2026, 7, 11, 1, 3, tzinfo=UTC),
)
thread = Thread(target=server.serve_forever, daemon=True)
thread.start()
try:
    connection = http.client.HTTPConnection('127.0.0.1', server.server_port, timeout=2)
    connection.request('GET', '/', headers={'Host': f'127.0.0.1:{server.server_port}'})
    response = connection.getresponse()
    html = response.read().decode()
    assert response.status == 200
    assert 'MedRec Research' in html
    assert re.search(r'/assets/[^\" ]+\\.js', html)
finally:
    server.shutdown()
    server.server_close()
    thread.join(timeout=2)
"""
        runtime_env = os.environ.copy()
        runtime_env["PATH"] = "/usr/bin:/bin"
        runtime_env.pop("NODE_PATH", None)
        _run(
            [
                str(python),
                "-c",
                smoke,
                str(root / "fixtures/status/discovery-eligible.json"),
            ],
            cwd=temporary,
            env=runtime_env,
        )
        print(f"wheel verified without Node: {wheel.name} ({len(resources)} web resources)")


if __name__ == "__main__":
    main()
