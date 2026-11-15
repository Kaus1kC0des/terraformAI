import json
from dataclasses import asdict
from pathlib import Path

from tfai.core.runner import TfResult, run


def tf_result_to_string(result: TfResult) -> str:
    deny_list = ["argv"]
    result_dict = asdict(result)
    for i in deny_list:
        result_dict.pop(i, None)
    return json.dumps(result_dict)


def terrraform_validate(workdir: str):
    """
    Runs terraform validate on a given directory
    """
    response = run(["validate", "-json"], chdir=workdir)
    return tf_result_to_string(response)


def terraform_plan(workdir: str):
    """
    Runs terraform plan on a given directory
    """
    response = run(["plan", "-no-color", "-input=false"], chdir=workdir)
    return tf_result_to_string(response)


def read_file(workdir: str, filename: str):
    root_dir = Path(workdir).resolve()
    filepath = (root_dir / filename).resolve()

    if not filepath.is_relative_to(root_dir):
        return "Invalid filepath or filename, specified file does not exists. Please check and try again"

    if filepath.suffix != ".tf":
        return "Can only read terraform files. Cannot read a file that does not end with .tf"
    return filepath.read_text()


terraform_tools = [
    {
        "type": "function",
        "name": "terraform_validate",
        "description": """
            Runs terraform validate.
            Can be used to validate if a given terraform code / module is correctly written or not.
        """,
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
            "additionalProperties": False,
        },
    },
    {
        "type": "function",
        "name": "terraform_plan",
        "description": """
                Runs terraform plan.
                Can be used to plan the potential outcome of a given terraform code / module and can be used to verify if it can correctly achieve our requirement or not.
            """,
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
            "additionalProperties": False,
        },
    },
]

general_tools = [
    {
        "type": "function",
        "name": "read_file",
        "description": """
                Reads the content of a file.
                Can be used to read terraform code to understand issues and potentially sugggest accurate fixes.
            """,
        "parameters": {
            "type": "object",
            "properties": {
                "filename": {
                    "type": "string",
                    "description": "The filename of the terraform file that is to be read.",
                },
            },
            "required": ["filename"],
            "additionalProperties": False,
        },
    }
]

functions = {
    "terraform_validate": terrraform_validate,
    "read_file": read_file,
    "terraform_plan": terraform_plan,
}
