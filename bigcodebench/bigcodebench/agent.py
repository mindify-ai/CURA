# %%
from tqdm import tqdm
from dotenv import load_dotenv
from bigcodebench.data import get_bigcodebench, load_solutions
from bigcodebench.data.utils import CACHE_DIR
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from typing import Annotated
from IPython.display import Image, display
from langchain_core.runnables.graph import CurveStyle, MermaidDrawMethod, NodeStyles

from typing_extensions import TypedDict

from langchain_openai import ChatOpenAI
import os
import json

load_dotenv()
subset = "full"  # Replace with your subset name

NUM_SAMPLES = len(get_bigcodebench(subset=subset))
NUM_CORRECT = 0

# Load BigCodeBench dataset and solutions
problems = get_bigcodebench(subset=subset)
output_file = "samples.jsonl"  # Output file for samples

# Limit the number of samples to evaluate
# problems = dict(list(problems.items())[:NUM_SAMPLES])
print("NUM_SAMPLES:", NUM_SAMPLES)


class State(TypedDict):
    messages: Annotated[list, add_messages]


graph_builder = StateGraph(State)

llm = ChatOpenAI(
    model="gpt-4o-mini",
    api_key=os.getenv("OPENAI_API_KEY"),
)

llm_feedback_model = ChatOpenAI(
    model="gpt-4o",
    api_key=os.getenv("OPENAI_API_KEY"),
)

def code_problem_understanding(state: State):
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
    Analyze the problem or codebase and divide it into smaller sub-problems or logical components. Clearly describe each sub-problem, its purpose, and how it contributes to the overall solution. And provide two possible solutions for each sub-problem. 
    </Instructions>
    
    <OUTPUT_INSTRUCT>
    Please provide one possible solutions for each sub-problem. Please provide the solutions in the following format:
    <PLAN_1> Put your first possible solution here with confidence rating from 0 to 10 at <CONFIDENCE_RATING> </CONFIDENCE_RATING> </PLAN_1>
    </OUTPUT_INSTRUCT>
    """

    return {"messages": [llm.invoke(prompt)]}


def code_sol_reasoning(state: State):
    prompt = f"""
    <Identity>
    You are an expert AI assistant specializing in programmatic reasoning, problem decomposition, reflective reasoning, and solution verification. Your goal is to deliver clear, logically sound, and testable solutions to complex programming challenges with confidence and precision.
    </Identity>
    
    <Context>
    You are provided with a programming problem or codebase that requires a structured approach for analysis and resolution. The process include generating the final solution by combining the resolved sub-problems, verifying correctness through testing, and providing the final code solution.
    </Context>
    
    <Task>
    {state["messages"]}
    </Task>
    
    <Instructions>
    Based on the resolved sub-problems and their solutions, generate the final solution for the problem by combining the resolved sub-problems. Verify the correctness of the final solution through testing and provide the final code solution.
    </Instructions>
    
    <OUTPUT_INSTRUCT>
    Please generate one possible solutions for each plan. Please provide the solutions in the following format: 
    <SOLUTION_1> Put your first possible solution based on the first plan here with confidence rating from 0 to 10 at <CONFIDENCE_RATING> </CONFIDENCE_RATING> </SOLUTION_1>
    </OUTPUT_INSTRUCT>
    """

    return {"messages": [llm.invoke(prompt)]}

def feedback_model(state: State):
    prompt = f"""
    <Identity>
    You are an expert AI assistant specializing in programmatic reasoning, problem decomposition, reflective reasoning, and solution verification. Your goal is to deliver clear, logically sound, and testable solutions to complex programming challenges with confidence and precision.
    </Identity>
    
    <Context>
    You are provided with a programming problem or codebase that requires a structured approach for analysis and resolution. The process include generating the final solution by combining the resolved sub-problems, verifying correctness through testing, and providing the final code solution.
    </Context>
    
    <Task>
    {state["messages"]}
    </Task>
    
    <Instructions>
    Based on the resolved sub-problems and their solutions, generate the final solution for the problem by combining the resolved sub-problems. Verify the correctness of the final solution through testing and provide the final code solution. And provide a score from 0 to 10 for the confidence level of the each final solution.
    </Instructions>
    
    <OUTPUT_INSTRUCT>
    Please provide a score from 0 to 10 for the confidence level of the each final solution. Please provide the scores in the following format:
    <SOLUTION_1_UNDERSTANDING> Put your confidence score for the first understanding to the solution 1 here </SOLUTION_1_UNDERSTANDING>
    <SOLUTION_1_REASONING> Put your confidence score for the first reasoning to the solution 1 here </SOLUTION_1_REASONING>
    <FEEDBACK_1> Provide feedback for the first solution </FEEDBACK_1>
    </OUTPUT_INSTRUCT>
    """

    return {"messages": [llm_feedback_model.invoke(prompt)]}

def routing_condition(state: State):
    # If the first solution is not confident, go back to code_sol_reasoning or code_understanding based 
    if state["messages"][-1].content.find("<SOLUTION_1_UNDERSTANDING>") != -1:
        confidence_score = state["messages"][-1].content.split("<SOLUTION_1_UNDERSTANDING>")[1].split("</SOLUTION_1_UNDERSTANDING>")[0]
        if int(confidence_score) < 8:
            return "code_problem_understanding"
        
    # If the first reasoning is not confident, go back to code_sol_reasoning
    if state["messages"][-1].content.find("<SOLUTION_1_REASONING>") != -1:
        confidence_score = state["messages"][-1].content.split("<SOLUTION_1_REASONING>")[1].split("</SOLUTION_1_REASONING>")[0]
        if int(confidence_score) < 8:
            return "code_solution_reasoning"

    return END

graph_builder.add_node("code_problem_understanding", code_problem_understanding)
graph_builder.add_node("code_solution_reasoning", code_sol_reasoning)
graph_builder.add_node("feedback_model", feedback_model)
graph_builder.set_entry_point("code_problem_understanding")
graph_builder.add_edge("code_problem_understanding", "code_solution_reasoning")
graph_builder.add_edge("code_solution_reasoning", "feedback_model")
graph_builder.add_conditional_edges("feedback_model", routing_condition)
graph_builder.set_finish_point("code_solution_reasoning")
graph = graph_builder.compile()

"""
display(
    Image(
        graph.get_graph().draw_mermaid_png(
            draw_method=MermaidDrawMethod.API,
        )
    )
)
"""

# %%

# Ensure cache directory exists
os.makedirs(CACHE_DIR, exist_ok=True)

if __name__ == "__main__":
    print("Starting sample generation...")

    with open(output_file, "w") as f:
        for i, (task_id, problem) in enumerate(
            tqdm(problems.items(), desc="Processing Problems")
        ):
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
                    str(answer["messages"][-1].content)
                    .strip()
                    .replace("\n", "")
                    .replace("  ", " ")
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