import logging
from typing import Annotated

import openai
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
    verbose: Annotated[
        bool,
        typer.Option("--verbose", help="Show each tool call the agent makes (stderr)."),
    ] = False,
) -> None:
    """Ask the agent about your Terraform code. It can read, validate and plan; it never changes anything."""
    if verbose:
        logging.basicConfig(level=logging.INFO)

    tfctx = ctx.find_object(TfContext) or TfContext()
    workdir = tfctx.chdir

    try:
        answer = run_agent(get_client(), question=question, workdir=workdir)
    except openai.AuthenticationError:
        typer.echo(
            "OpenAI rejected your API key. Check OPENAI_API_KEY in your .env or environment.",
            err=True,
        )
        raise typer.Exit(1)
    except openai.OpenAIError as e:
        typer.echo(f"OpenAI request failed: {e}", err=True)
        raise typer.Exit(1)

    typer.echo(answer)
