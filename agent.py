import dotenv

dotenv.load_dotenv()

from datasets import load_dataset

swebench = load_dataset("princeton-nlp/SWE-bench", split="dev")
swebench[0]

from langgraph.graph import StateGraph, add_messages
from typing import TypedDict, Annotated
from langgraph.prebuilt import create_react_agent
from langchain_openai import ChatOpenAI
from vm import RepoVM
from agent_tools import create_tools


def do_prediction(data):
    with RepoVM(
        image_name="swe_img:latest",
        repo_name=data["repo"],
        commit_hash=data["base_commit"],
    ) as vm:

        llm = ChatOpenAI(model="gpt-4o-mini")
        tools = create_tools(vm)

        agent = create_react_agent(llm, tools=tools.values(), debug=True)

        final_state = agent.invoke(
            input={
                "messages": [
                    (
                        "system",
                        "You are an autonomous programmer, and you are going to propose a pull request based on the problem below. You are given several tools to help you with the task. The requested repo has been cloned to the root directory. You can use the tools to view, edit, and create files, and submit the patch.",
                    ),
                    (
                        "user",
                        f'Please submit a pull request based on the following problem:\nRepo: {data["repo"]}\nProblem: {data["problem_statement"]}\nHints: {data["hints_text"]}\nCreated at: {data["created_at"]}\nNow, start your work.\n',
                    ),
                ]
            },
            config={"recursion_limit": 50},
        )

    return final_state


result = do_prediction(swebench[0])
print(result)
