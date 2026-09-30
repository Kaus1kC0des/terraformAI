"""The single place that spawns terraform. Typer-free so the AI agent can reuse it."""

import functools
import shutil
import subprocess
from collections.abc import Sequence
from dataclasses import dataclass


class TerraformNotFoundError(RuntimeError):
    """Raised when the terraform binary is not on PATH."""


@dataclass(frozen=True)
class TfResult:
    argv: list[str]
    returncode: int
    stdout: str = ""
    stderr: str = ""

    @property
    def ok(self) -> bool:
        return self.returncode == 0


@functools.cache
def terraform_bin() -> str:
    path = shutil.which("terraform")
    if path is None:
        raise TerraformNotFoundError("terraform not found on PATH")
    return path


def run(
    args: Sequence[str], *, chdir: str | None = None, stream: bool = False
) -> TfResult:
    """Run terraform with `args`.

    stream=True inherits the terminal (interactive prompts, colors, long output);
    stream=False captures stdout/stderr. Never raises on a non-zero exit code.
    """
    argv = [terraform_bin(), *([f"-chdir={chdir}"] if chdir else []), *args]

    if stream:
        proc = subprocess.run(argv, check=False)
        return TfResult(argv, proc.returncode)

    proc = subprocess.run(
        argv,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return TfResult(argv, proc.returncode, proc.stdout, proc.stderr)
