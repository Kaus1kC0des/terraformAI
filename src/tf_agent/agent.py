import json
import logging
import os

from openai import Client

from tf_agent.tools import functions, general_tools, terraform_tools

logger = logging.getLogger(__name__)


def run_agent(client: Client, question: str, workdir: str, max_turns=20) -> str:
    conversations = [
        {
            "role": "user",
            "content": question,
        }
    ]
    INSTRUCTION = "You are a terraform agent that has a set of tools to work within a terraform managed environment. Help the user achieve their tasks."
    for i in range(max_turns):
        response = client.responses.create(
            model=os.getenv("TFAI_MODEL", "gpt-6-luna"),
            instructions=INSTRUCTION,
            tools=[*terraform_tools, *general_tools],
            input=conversations,
        )
        conversations.extend(response.output)
        calls = [item for item in response.output if item.type == "function_call"]
        if not calls:
            return response.output_text

        for item in response.output:
            if item.type == "function_call":
                try:
                    func_name = item.name
                    func_args = json.loads(item.arguments)
                    logger.info(f"Recieved arguments: {func_args}")
                    func_args["workdir"] = workdir
                    func = functions.get(func_name)

                    if func is None:
                        function_response = {"error": f"Unknown tool name {func_name}"}
                        conversations.append(
                            {
                                "call_id": item.call_id,
                                "type": "function_call_output",
                                "output": json.dumps(function_response),
                            }
                        )
                        continue
                    function_response = func(**func_args)
                    logger.info(
                        f"Function Name: {func_name}\nFunction Arguments: {func_args}\nFunction Response={function_response}"
                    )
                    conversations.append(
                        {
                            "call_id": item.call_id,
                            "type": "function_call_output",
                            "output": function_response,
                        }
                    )
                except Exception as e:
                    logger.error(str(e))
                    conversations.append(
                        {
                            "call_id": item.call_id,
                            "type": "function_call_output",
                            "output": json.dumps({"error": str(e)}),
                        }
                    )
    else:
        logger.info("Reached MAX_TURNS can't run anymore!")
        return "Reached MAX_TURNS can't run anymore!"
