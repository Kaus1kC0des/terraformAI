"""`tfai workspace ...` — manage terraform workspaces."""

from typing import Annotated

import typer

from tfai.core.context import confirm_or_abort, invoke
from tfai.core.flags import tf_flags
from tfai.core.options import EXTRA_ARGS, Yes
from tfai.core.passthrough import passthrough

app = typer.Typer(
    name="workspace", help="Manage terraform workspaces.", no_args_is_help=True
)

Name = Annotated[str, typer.Argument(help="Workspace name.")]

passthrough(app, "list", ["workspace", "list"], help="List workspaces.")
passthrough(app, "show", ["workspace", "show"], help="Show the current workspace name.")


@app.command(context_settings=EXTRA_ARGS)
def new(ctx: typer.Context, name: Name) -> None:
    """Create a new workspace."""
    invoke(ctx, ["workspace", "new", *ctx.args, name])


@app.command(context_settings=EXTRA_ARGS)
def select(ctx: typer.Context, name: Name) -> None:
    """Switch to a workspace."""
    invoke(ctx, ["workspace", "select", *ctx.args, name])


@app.command(context_settings=EXTRA_ARGS)
def delete(
    ctx: typer.Context,
    name: Name,
    force: Annotated[
        bool,
        typer.Option("--force", help="Delete even if the workspace has resources."),
    ] = False,
    yes: Yes = False,
) -> None:
    """Delete a workspace."""
    confirm_or_abort(f"Delete workspace {name!r}?", skip=yes)
    invoke(
        ctx, ["workspace", "delete", *tf_flags(force=force or None), *ctx.args, name]
    )
