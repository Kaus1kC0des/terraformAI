"""Factory for commands that only forward their arguments to terraform."""

import typer

from tfai.core.context import confirm_or_abort, invoke
from tfai.core.options import EXTRA_ARGS


def passthrough(
    app: typer.Typer,
    name: str,
    tf_args: list[str],
    *,
    help: str,
    stream: bool = False,
    confirm: str | None = None,
) -> None:
    @app.command(name, help=help, context_settings=EXTRA_ARGS)
    def _command(ctx: typer.Context) -> None:
        if confirm:
            confirm_or_abort(confirm)
        invoke(ctx, [*tf_args, *ctx.args], stream=stream)
