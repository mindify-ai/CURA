from tqdm import tqdm
from dotenv import load_dotenv
from bigcodebench.data import get_bigcodebench, load_solutions
from bigcodebench.data.utils import CACHE_DIR
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from typing import Annotated

from typing_extensions import TypedDict

from langchain_openai import ChatOpenAI
import os
import json

load_dotenv()

NUM_SAMPLES = len(get_bigcodebench(subset="hard"))
NUM_CORRECT = 0

# Load BigCodeBench dataset and solutions
subset = "hard"  # Replace with your subset name
problems = get_bigcodebench(subset=subset)
output_file = "samples.jsonl" # Output file for samples

# Limit the number of samples to evaluate
# problems = dict(list(problems.items())[:NUM_SAMPLES])
print("NUM_SAMPLES:", NUM_SAMPLES)

class State(TypedDict):
    messages: Annotated[list, add_messages]


graph_builder = StateGraph(State)

llm = ChatOpenAI(
    model="gpt-4o-mini-2024-07-18",
    api_key="",
)


def code_understanding(state: State):
    prompt = f"""
        <Identity>
    You are an expert AI assistant specializing in programmatic reasoning, problem decomposition, reflective reasoning, and solution verification. Your goal is to deliver clear, logically sound, and testable solutions to complex programming challenges with confidence and precision.
    </Identity>
    
    <Context>
    You are provided with a programming problem or codebase that requires a structured approach for analysis and resolution. The process includes breaking the problem into sub-problems, solving each individually, merging solutions, and verifying correctness through testing.
    </Context>
    
    <Task>
    {state["messages"]}
    </Task>
    
    <Instructions>
    Analyze the problem or codebase and divide it into smaller sub-problems or logical components. Clearly describe each sub-problem, its purpose, and how it contributes to the overall solution.
    </Instructions>
    """

    return {"messages": [llm.invoke(prompt)]}


def code_sol_reasoning(state: State):
    prompt = f"""
    <Identity>
    You are an expert AI assistant specializing in programmatic reasoning, problem decomposition, reflective reasoning, and solution verification. Your goal is to deliver clear, logically sound, and testable solutions to complex programming challenges with confidence and precision.
    </Identity>
    
    <Context>
    You are provided with a programming problem or codebase that requires a structured approach for analysis and resolution. The process includes breaking the problem into sub-problems, solving each individually, merging solutions, and verifying correctness through testing.
    </Context>
    
    <Task>
    {state["messages"]}
    </Task>
    
    <Instructions>
    Solve each sub-problem using reflective reasoning. Evaluate the solution’s logic, refine it to address edge cases or ambiguities, and present the final solution for each component. Combine the resolved sub-problems to create N potential solutions. Ensure logical compatibility between the components and explain the merging strategy.
    </Instructions>
    
    <OUTPUT_INSTRUCT>
    Please generate the final solution for the problem by combining the resolved sub-problems. Please generate the final code only and do not include any additional instructions or explanations or comments, purely the code.
    </OUTPUT_INSTRUCT>
    """

    return {"messages": [llm.invoke(prompt)]}


graph_builder.add_node("code_understanding", code_understanding)
graph_builder.add_node("code_sol_reasoning", code_sol_reasoning)
graph_builder.set_entry_point("code_understanding")
graph_builder.add_edge("code_understanding", "code_sol_reasoning")
graph_builder.set_finish_point("code_sol_reasoning")
graph = graph_builder.compile()

# Ensure cache directory exists
os.makedirs(CACHE_DIR, exist_ok=True)

if __name__ == "__main__":
    print("Starting sample generation...")
    
    with open(output_file, "w") as f:
        for i, (task_id, problem) in enumerate(tqdm(problems.items(), desc="Processing Problems")):
            if i >= NUM_SAMPLES:
                break

            print("--------------------")
            print(f"Task ID: {task_id}")
            print("Problem:", problem["complete_prompt"])

            if not problem:
                print(f"Problem with task ID {task_id} not found in the dataset.")
                continue

            # Construct the state object
            state = {
                "messages": problem["complete_prompt"]
                + " based on the instruction: "
                + problem["instruct_prompt"]
            }

            try:
                # Generate response using the graph
                answer = graph.invoke(state)
                answer_snippet = (
                    str(answer["messages"][-1].content).strip().replace("OUTPUT:", "").strip()
                )

                # Extract Python code if present
                if "```python" in answer_snippet:
                    answer_snippet = (
                        answer_snippet.split("```python")[1].split("```")[0].strip()
                    )

                print("Answer Snippet:", answer_snippet)

                # Prepare JSON object
                sample = {
                    "task_id": task_id,
                    "solution": answer_snippet,
                    "completion": answer_snippet,
                    "instruction_prompt": problem["instruct_prompt"],
                    "test_prompt": problem["test"],
                }

                # Write to JSONL file
                f.write(json.dumps(sample) + "\n")

            except Exception as e:
                print(f"Error processing Task ID {task_id}: {e}")

    print(f"Sample generation completed. Output saved to {output_file}")