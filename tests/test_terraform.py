import subprocess

import pytest
from typer.testing import CliRunner

from tfai.cli import app
from tfai.core import runner
from tfai.core.flags import tf_flags
from tfai.core.runner import TerraformNotFoundError, TfResult

cli = CliRunner()


# --- tf_flags -------------------------------------------------------------


def test_tf_flags_conversions():
    assert tf_flags(
        skip=None, upgrade=True, lock=False, target=["a", "b"], var_file="x.tfvars"
    ) == ["-upgrade", "-lock=false", "-target=a", "-target=b", "-var-file=x.tfvars"]


def test_tf_flags_empty():
    assert tf_flags() == []
    assert tf_flags(target=None, json=None) == []


# --- runner.run -------------------------------------------------------------


@pytest.fixture
def fake_subprocess(monkeypatch):
    calls = []

    def fake_run(argv, **kwargs):
        calls.append((argv, kwargs))
        return subprocess.CompletedProcess(argv, 0, stdout="out", stderr="")

    monkeypatch.setattr(runner, "terraform_bin", lambda: "terraform")
    monkeypatch.setattr(subprocess, "run", fake_run)
    return calls


def test_run_capture_puts_chdir_before_subcommand(fake_subprocess):
    res = runner.run(["state", "list"], chdir="infra")
    argv, kwargs = fake_subprocess[0]
    assert argv == ["terraform", "-chdir=infra", "state", "list"]
    assert kwargs["capture_output"] is True
    assert res.ok and res.stdout == "out"


def test_run_stream_inherits_terminal(fake_subprocess):
    runner.run(["apply"], stream=True)
    argv, kwargs = fake_subprocess[0]
    assert argv == ["terraform", "apply"]
    assert kwargs == {"check": False}


def test_terraform_bin_missing(monkeypatch):
    runner.terraform_bin.cache_clear()
    monkeypatch.setattr(runner.shutil, "which", lambda _: None)
    with pytest.raises(TerraformNotFoundError):
        runner.terraform_bin()
    runner.terraform_bin.cache_clear()


# --- CLI ------------------------------------------------------------------


@pytest.fixture
def recorded(monkeypatch):
    calls = []

    def fake_run(args, *, chdir=None, stream=False):
        calls.append({"args": list(args), "chdir": chdir, "stream": stream})
        return TfResult(["terraform", *args], 0, stdout="ok\n")

    monkeypatch.setattr(runner, "run", fake_run)
    return calls


def test_plan_builds_flags(recorded):
    result = cli.invoke(
        app,
        [
            "plan",
            "--target",
            "a",
            "--target",
            "b",
            "--var-file",
            "x.tfvars",
            "--no-refresh",
        ],
    )
    assert result.exit_code == 0, result.output
    assert recorded[0]["args"] == [
        "plan",
        "-target=a",
        "-target=b",
        "-var-file=x.tfvars",
        "-refresh=false",
    ]
    assert recorded[0]["stream"] is True


def test_plan_forwards_extra_args(recorded):
    cli.invoke(app, ["plan", "--", "-parallelism=5"])
    assert recorded[0]["args"] == ["plan", "-parallelism=5"]


def test_single_dash_terraform_flags_pass_through_intact(recorded):
    cli.invoke(app, ["plan", "-no-color", "-out=p.tfplan"])
    assert recorded[0]["args"] == ["plan", "-no-color", "-out=p.tfplan"]


def test_apply_single_dash_destroy_does_not_auto_approve(recorded):
    cli.invoke(app, ["apply", "-destroy"])
    assert recorded[0]["args"] == ["apply", "-destroy"]


def test_global_chdir(recorded):
    result = cli.invoke(app, ["-C", "infra", "state", "list"])
    assert result.exit_code == 0, result.output
    assert recorded[0] == {"args": ["state", "list"], "chdir": "infra", "stream": False}
    assert "ok" in result.output


def test_apply_requires_explicit_yes_for_auto_approve(recorded):
    cli.invoke(app, ["apply"])
    cli.invoke(app, ["apply", "--yes", "plan.out"])
    assert recorded[0]["args"] == ["apply"]
    assert recorded[1]["args"] == ["apply", "-auto-approve", "plan.out"]


def test_state_rm_aborts_without_confirmation(recorded):
    result = cli.invoke(app, ["state", "rm", "aws_s3_bucket.x"], input="n\n")
    assert result.exit_code != 0
    assert recorded == []


def test_state_rm_dry_run_skips_prompt(recorded):
    result = cli.invoke(app, ["state", "rm", "--dry-run", "aws_s3_bucket.x"])
    assert result.exit_code == 0, result.output
    assert recorded[0]["args"] == ["state", "rm", "-dry-run", "aws_s3_bucket.x"]


def test_passthrough_command(recorded):
    cli.invoke(app, ["workspace", "list"])
    assert recorded[0]["args"] == ["workspace", "list"]


def test_version_json(recorded):
    cli.invoke(app, ["version", "--json"])
    assert recorded[0]["args"] == ["version", "-json"]


def test_nonzero_exit_propagates(monkeypatch):
    monkeypatch.setattr(
        runner, "run", lambda args, **_: TfResult(list(args), 3, stderr="boom\n")
    )
    result = cli.invoke(app, ["validate"])
    assert result.exit_code == 3


def test_missing_terraform_exits_127(monkeypatch):
    def raise_missing(*_, **__):
        raise TerraformNotFoundError()

    monkeypatch.setattr(runner, "run", raise_missing)
    result = cli.invoke(app, ["version"])
    assert result.exit_code == 127
    assert "terraform not found" in result.output
