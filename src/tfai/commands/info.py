"""Read-only top-level commands: version, show, output, providers."""

from typing import Annotated

import typer

from tfai.core.context import invoke
from tfai.core.flags import tf_flags
from tfai.core.options import EXTRA_ARGS, Json
from tfai.core.passthrough import passthrough

app = typer.Typer()


@app.command(context_settings=EXTRA_ARGS)
def version(ctx: typer.Context, json: Json = False) -> None:
    """Show the terraform version."""
    invoke(ctx, ["version", *tf_flags(json=json or None), *ctx.args])


@app.command(context_settings=EXTRA_ARGS)
def show(
    ctx: typer.Context,
    path: Annotated[
        str | None,
        typer.Argument(help="Plan or state file (defaults to current state)."),
    ] = None,
    json: Json = False,
) -> None:
    """Show the current state or a saved plan."""
    invoke(
        ctx,
        ["show", *tf_flags(json=json or None), *ctx.args, *([path] if path else [])],
    )


@app.command(context_settings=EXTRA_ARGS)
def output(
    ctx: typer.Context,
    name: Annotated[
        str | None, typer.Argument(help="Output name (defaults to all outputs).")
    ] = None,
    json: Json = False,
    raw: Annotated[
        bool, typer.Option("--raw", help="Print a single string output without quotes.")
    ] = False,
) -> None:
    """Show output values."""
    flags = tf_flags(json=json or None, raw=raw or None)
    invoke(ctx, ["output", *flags, *ctx.args, *([name] if name else [])])


passthrough(
    app,
    "providers",
    ["providers"],
    help="Show the providers required by the configuration.",
)
