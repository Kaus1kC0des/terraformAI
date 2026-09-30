"""Core workflow commands: init, fmt, validate, plan, apply, destroy."""

from typing import Annotated

import typer

from tfai.core.context import invoke
from tfai.core.flags import tf_flags
from tfai.core.options import (
    EXTRA_ARGS,
    Json,
    Lock,
    Refresh,
    Targets,
    VarFiles,
    Vars,
    Yes,
)

app = typer.Typer()


@app.command(context_settings=EXTRA_ARGS)
def init(
    ctx: typer.Context,
    upgrade: Annotated[
        bool, typer.Option("--upgrade", help="Upgrade modules and providers.")
    ] = False,
    reconfigure: Annotated[
        bool, typer.Option("--reconfigure", help="Ignore existing backend config.")
    ] = False,
    backend_config: Annotated[
        list[str] | None,
        typer.Option(
            "--backend-config", help="Backend config file or key=value (repeatable)."
        ),
    ] = None,
) -> None:
    """Initialize the working directory."""
    flags = tf_flags(
        upgrade=upgrade or None,
        reconfigure=reconfigure or None,
        backend_config=backend_config,
    )
    invoke(ctx, ["init", *flags, *ctx.args], stream=True)


@app.command(context_settings=EXTRA_ARGS)
def fmt(
    ctx: typer.Context,
    check: Annotated[
        bool,
        typer.Option("--check", help="Only check formatting, exit non-zero if needed."),
    ] = False,
    recursive: Annotated[
        bool, typer.Option("--recursive", help="Also format subdirectories.")
    ] = False,
    diff: Annotated[
        bool, typer.Option("--diff", help="Show formatting differences.")
    ] = False,
) -> None:
    """Rewrite configuration files to canonical format."""
    flags = tf_flags(
        check=check or None, recursive=recursive or None, diff=diff or None
    )
    invoke(ctx, ["fmt", *flags, *ctx.args], stream=True)


@app.command(context_settings=EXTRA_ARGS)
def validate(ctx: typer.Context, json: Json = False) -> None:
    """Check whether the configuration is valid."""
    invoke(ctx, ["validate", *tf_flags(json=json or None), *ctx.args])


@app.command(context_settings=EXTRA_ARGS)
def plan(
    ctx: typer.Context,
    target: Targets = None,
    var: Vars = None,
    var_file: VarFiles = None,
    out: Annotated[
        str | None, typer.Option("--out", help="Save the plan to a file.")
    ] = None,
    destroy: Annotated[
        bool, typer.Option("--destroy", help="Plan to destroy all resources.")
    ] = False,
    refresh: Refresh = None,
    lock: Lock = None,
) -> None:
    """Show changes required by the current configuration."""
    flags = tf_flags(
        target=target,
        var=var,
        var_file=var_file,
        out=out,
        destroy=destroy or None,
        refresh=refresh,
        lock=lock,
    )
    invoke(ctx, ["plan", *flags, *ctx.args], stream=True)


@app.command(context_settings=EXTRA_ARGS)
def apply(
    ctx: typer.Context,
    plan_file: Annotated[
        str | None, typer.Argument(help="Saved plan file to apply.")
    ] = None,
    target: Targets = None,
    var: Vars = None,
    var_file: VarFiles = None,
    lock: Lock = None,
    yes: Yes = False,
) -> None:
    """Create or update infrastructure. Terraform asks for approval unless --yes is given."""
    flags = tf_flags(
        target=target, var=var, var_file=var_file, lock=lock, auto_approve=yes or None
    )
    invoke(
        ctx,
        ["apply", *flags, *ctx.args, *([plan_file] if plan_file else [])],
        stream=True,
    )


@app.command(context_settings=EXTRA_ARGS)
def destroy(
    ctx: typer.Context,
    target: Targets = None,
    var: Vars = None,
    var_file: VarFiles = None,
    lock: Lock = None,
    yes: Yes = False,
) -> None:
    """Destroy managed infrastructure. Terraform asks for approval unless --yes is given."""
    flags = tf_flags(
        target=target, var=var, var_file=var_file, lock=lock, auto_approve=yes or None
    )
    invoke(ctx, ["destroy", *flags, *ctx.args], stream=True)
