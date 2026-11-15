from typing import Annotated

import typer

from tf_agent.agent import run_agent
from tf_agent.models import get_client
from tfai.core.context import TfContext

app = typer.Typer()


@app.command()
def ask(
    ctx: typer.Context,
    question: Annotated[
        str, typer.Argument(help="The question you want to ask the agent.")
    ],
) -> None:
    """Ask the agent about your Terraform code. It can read, validate and plan; it never changes anything."""

    tfctx = ctx.find_object(TfContext) or TfContext()
    workdir = tfctx.chdir
    answer = run_agent(get_client(), question=question, workdir=workdir)
    typer.echo(answer)
