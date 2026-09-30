"""Reusable option types shared across commands."""

from typing import Annotated

import typer

Targets = Annotated[
    list[str] | None,
    typer.Option("--target", help="Resource address to target (repeatable)."),
]
Vars = Annotated[
    list[str] | None,
    typer.Option("--var", help="Set a variable, key=value (repeatable)."),
]
VarFiles = Annotated[
    list[str] | None,
    typer.Option("--var-file", help="Load variables from a .tfvars file (repeatable)."),
]
Json = Annotated[bool, typer.Option("--json", help="Machine-readable JSON output.")]
Lock = Annotated[
    bool | None,
    typer.Option("--lock/--no-lock", help="Hold a state lock during the operation."),
]
Refresh = Annotated[
    bool | None,
    typer.Option("--refresh/--no-refresh", help="Refresh state before planning."),
]
DryRun = Annotated[
    bool,
    typer.Option("--dry-run", help="Show what would change without changing anything."),
]
Yes = Annotated[bool, typer.Option("--yes", help="Skip confirmation.")]

# Lets commands forward unmodelled terraform flags, e.g. `tfai plan -no-color`.
# Subcommand options must stay long-only: Click splits `-destroy` into short flags,
# so a `-y` alias would turn `tfai apply -destroy` into an auto-approve.
EXTRA_ARGS = {"allow_extra_args": True, "ignore_unknown_options": True}
