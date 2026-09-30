"""`tfai state ...` — inspect and modify terraform state."""

from typing import Annotated

import typer

from tfai.core.context import confirm_or_abort, invoke
from tfai.core.flags import tf_flags
from tfai.core.options import EXTRA_ARGS, DryRun, Yes
from tfai.core.passthrough import passthrough

app = typer.Typer(
    name="state", help="Inspect and modify terraform state.", no_args_is_help=True
)


@app.command("list", context_settings=EXTRA_ARGS)
def list_resources(
    ctx: typer.Context,
    addresses: Annotated[
        list[str] | None, typer.Argument(help="Filter by resource address.")
    ] = None,
    id: Annotated[
        str | None, typer.Option("--id", help="Filter by resource ID.")
    ] = None,
) -> None:
    """List resources in the state."""
    invoke(ctx, ["state", "list", *tf_flags(id=id), *ctx.args, *(addresses or [])])


@app.command(context_settings=EXTRA_ARGS)
def show(
    ctx: typer.Context,
    address: Annotated[str, typer.Argument(help="Resource address.")],
) -> None:
    """Show a single resource in the state."""
    invoke(ctx, ["state", "show", *ctx.args, address])


@app.command(context_settings=EXTRA_ARGS)
def mv(
    ctx: typer.Context,
    source: Annotated[str, typer.Argument(help="Current resource address.")],
    destination: Annotated[str, typer.Argument(help="New resource address.")],
    dry_run: DryRun = False,
    yes: Yes = False,
) -> None:
    """Move an item in the state."""
    confirm_or_abort(f"Move {source} -> {destination} in state?", skip=dry_run or yes)
    invoke(
        ctx,
        [
            "state",
            "mv",
            *tf_flags(dry_run=dry_run or None),
            *ctx.args,
            source,
            destination,
        ],
    )


@app.command(context_settings=EXTRA_ARGS)
def rm(
    ctx: typer.Context,
    addresses: Annotated[
        list[str], typer.Argument(help="Resource addresses to forget.")
    ],
    dry_run: DryRun = False,
    yes: Yes = False,
) -> None:
    """Remove items from the state (does not destroy real infrastructure)."""
    confirm_or_abort(f"Remove {', '.join(addresses)} from state?", skip=dry_run or yes)
    invoke(
        ctx, ["state", "rm", *tf_flags(dry_run=dry_run or None), *ctx.args, *addresses]
    )


passthrough(app, "pull", ["state", "pull"], help="Print the current state as JSON.")
