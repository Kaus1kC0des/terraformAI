import json


def format_diagnostic(diagnostic: dict) -> str:
    """
    Given a terraform diagnostic response object, format it into a single string.
    :param diagnostic:
    :return: str
    """
    response = [f"{diagnostic.get('severity')} : {diagnostic.get('summary')}"]

    if "range" in diagnostic.keys():
        response.append(f"'range' : {diagnostic.get('range').get('filename')}")