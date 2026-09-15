from pathlib import Path

from terralab3d.infrastructure.bundler import _bundle_is_fresh


def touch(path: Path, timestamp: float) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("x", encoding="utf-8")
    path.touch()
    path.chmod(0o644)
    import os
    os.utime(path, (timestamp, timestamp))


def test_bundle_freshness_tracks_typescript_and_css(tmp_path: Path) -> None:
    frontend = tmp_path / "frontend"
    dist = frontend / "dist"
    touch(frontend / "src" / "main.ts", 10)
    touch(frontend / "src" / "styles" / "shell.css", 10)
    touch(dist / "bundle.js", 20)
    touch(dist / "bundle.css", 20)
    assert _bundle_is_fresh(frontend, dist)

    touch(frontend / "src" / "styles" / "shell.css", 30)
    assert not _bundle_is_fresh(frontend, dist)


def test_bundle_freshness_requires_both_esbuild_outputs(tmp_path: Path) -> None:
    frontend = tmp_path / "frontend"
    touch(frontend / "src" / "main.ts", 10)
    touch(frontend / "dist" / "bundle.js", 20)
    assert not _bundle_is_fresh(frontend, frontend / "dist")
