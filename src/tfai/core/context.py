"""CLI glue between Typer commands and the terraform runner."""

from dataclasses import dataclass

import typer

from tfai.core import runner

INSTALL_HINT = "terraform not found on PATH. Install it: https://developer.hashicorp.com/terraform/install"


@dataclass
class TfContext:
    chdir: str | None = None


def invoke(
    ctx: typer.Context, args: list[str], *, stream: bool = False
) -> runner.TfResult:
    """Run terraform for a CLI command, echo its output and exit on failure."""
    tfctx = ctx.find_object(TfContext) or TfContext()
    try:
        res = runner.run(args, chdir=tfctx.chdir, stream=stream)
    except runner.TerraformNotFoundError:
        typer.echo(INSTALL_HINT, err=True)
        raise typer.Exit(127)

    if res.stdout:
        typer.echo(res.stdout, nl=False)
    if res.stderr:
        typer.echo(res.stderr, err=True, nl=False)
    if not res.ok:
        raise typer.Exit(res.returncode)
    return res


def confirm_or_abort(message: str, *, skip: bool = False) -> None:
    if not skip and not typer.confirm(message):
        raise typer.Abort()
