"""Composition root for the `tfai` CLI."""

from typing import Annotated

import typer

from tfai.commands import ask, info, lifecycle, state, workspace
from tfai.core.context import TfContext

app = typer.Typer(name="tfai", help="AI-assisted Terraform CLI.", no_args_is_help=True)


@app.callback()
def main(
    ctx: typer.Context,
    chdir: Annotated[
        str,
        typer.Option(
            "--chdir", "-C", envvar="TFAI_CHDIR", help="Terraform working directory."
        ),
    ] = ".",
) -> None:
    ctx.obj = TfContext(chdir=chdir)


app.add_typer(info.app)
app.add_typer(lifecycle.app)
app.add_typer(state.app)
app.add_typer(workspace.app)
app.add_typer(ask.app)
