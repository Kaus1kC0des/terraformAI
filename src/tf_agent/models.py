import functools
import os

from dotenv import load_dotenv
from openai import OpenAI

DEFAULT_MODEL = "gpt-6-luna"


@functools.cache
def get_client() -> OpenAI:
    """Return the shared OpenAI client, creating it on first use."""
    load_dotenv()
    return OpenAI()


def complete(system: str, user: str) -> str:
    """Send one message to the model and return its text reply."""
    response = get_client().responses.create(
        model=os.getenv("TFAI_MODEL", DEFAULT_MODEL),
        instructions=system,
        input=user,
    )
    return response.output_text
