"""The pip-only entry point installs once and launches the existing app runner."""

import subprocess

import pytest

import run_with_pip


def test_pip_bootstrap_reuses_environment_and_reinstalls_after_dependency_change(
    tmp_path, monkeypatch
):
    (tmp_path / "pyproject.toml").write_text("[project]\nname = 'sample'\n")
    requirements = tmp_path / "requirements-pip.txt"
    requirements.write_text("streamlit==1.66.1\n")
    calls = []

    def create(environment, with_pip):
        assert with_pip
        python = run_with_pip.environment_python(environment)
        python.parent.mkdir(parents=True)
        python.touch()

    def install(command, *, cwd, check):
        assert cwd == tmp_path and check
        assert command[1:4] == ["-m", "pip", "install"]
        assert command[4:6] == ["-r", str(requirements)]
        assert command[6:] == ["-e", str(tmp_path)]
        calls.append(command)

    monkeypatch.setattr(run_with_pip.venv, "create", create)
    monkeypatch.setattr(run_with_pip.subprocess, "run", install)
    python = run_with_pip.prepare_pip_environment(tmp_path)
    assert python.exists()
    assert len(calls) == 1
    assert run_with_pip.prepare_pip_environment(tmp_path) == python
    assert len(calls) == 1
    requirements.write_text("streamlit==1.66.2\n")
    run_with_pip.prepare_pip_environment(tmp_path)
    assert len(calls) == 2


def test_failed_pip_install_does_not_mark_environment_ready(tmp_path, monkeypatch):
    (tmp_path / "pyproject.toml").write_text("[project]\nname = 'sample'\n")
    (tmp_path / "requirements-pip.txt").write_text("streamlit==1.66.1\n")

    def create(environment, with_pip):
        python = run_with_pip.environment_python(environment)
        python.parent.mkdir(parents=True)
        python.touch()

    def fail(command, *, cwd, check):
        raise subprocess.CalledProcessError(1, command)

    monkeypatch.setattr(run_with_pip.venv, "create", create)
    monkeypatch.setattr(run_with_pip.subprocess, "run", fail)
    with pytest.raises(subprocess.CalledProcessError):
        run_with_pip.prepare_pip_environment(tmp_path)
    assert not (tmp_path / ".venv-pip/.saifa-pip-dependencies").exists()
