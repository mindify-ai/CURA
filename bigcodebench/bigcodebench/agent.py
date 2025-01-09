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

# Limit the number of samples to evaluate
# problems = dict(list(problems.items())[:NUM_SAMPLES])
print("NUM_SAMPLES:", NUM_SAMPLES)

class State(TypedDict):
    messages: Annotated[list, add_messages]


graph_builder = StateGraph(State)

llm = ChatOpenAI(
    model="gpt-4o-mini",
    api_key=os.getenv("OPENAI_API_KEY"),
    temperature=0.7,
)

llm_feedback_model = ChatOpenAI(
    model="gpt-4o-mini",
    api_key=os.getenv("OPENAI_API_KEY"),
    temperature=0.7,
)

def code_problem_understanding(state: State):
    prompt = f"""
    <Identity>
    You are an expert AI assistant specializing in programmatic reasoning, problem decomposition, reflective reasoning, and solution verification. 
    Your goal is to deliver clear, logically sound, and testable solutions to complex programming challenges with confidence and precision.
    </Identity>
    
    <Context>
    You are provided with a programming problem or codebase that requires a structured approach for analysis and resolution. 
    The process includes breaking the problem into sub-problems, solving each individually, merging solutions, and verifying correctness through testing.
    </Context>
    
    <Task>
    {state["messages"]}
    </Task>
    
    <Instructions>
    Analyze the problem or codebase and divide it into smaller sub-problems or logical components. 
    Clearly describe each sub-problem, its purpose, and how it contributes to the overall solution. 
    </Instructions>
    
    <OUTPUT_INSTRUCT>
    Please provide one possible solutions for each sub-problem. Please provide the solutions in the following format with the plan and understanding to the problem statement only in the code block: <PLAN_1> ... </PLAN_1>
    <PLAN_1> Put your first possible solution plan with the understanding to the problem statement here. </PLAN_1>
    </OUTPUT_INSTRUCT>
    """

    return {"messages": [llm.invoke(prompt)]}


def code_sol_reasoning(state: State):
    prompt = f"""
    <Identity>
    You are an expert AI assistant specializing in programmatic reasoning, problem decomposition, reflective reasoning, and solution verification. 
    Your goal is to deliver clear, logically sound, and testable solutions to complex programming challenges with confidence and precision.
    </Identity>
    
    <Context>
    You are provided with a programming problem or codebase that requires a structured approach for analysis and resolution. 
    The process include generating the final solution by combining the resolved sub-problems, verifying correctness through testing, and providing the final code solution.
    </Context>
    
    <Task>
    {state["messages"]}
    </Task>
    
    <Instructions>
    Based on the resolved sub-problems and their solutions, generate the final solution for the problem by combining the resolved sub-problems. 
    Verify the correctness of the final solution through testing and provide the final code solution.
    </Instructions>
    
    <OUTPUT_INSTRUCT>
    Please generate one possible solutions for each plan. Please provide the solutions in the following format with the code snippet only within the code block: <SOLUTION_1> ... </SOLUTION_1>
    <SOLUTION_1> Put your solution script here </SOLUTION_1>
    </OUTPUT_INSTRUCT>
    """

    return {"messages": [llm.invoke(prompt)]}

def feedback_model(state: State):
    prompt = f"""
    <Identity>
    You are an expert AI assistant specializing in programmatic reasoning, problem decomposition, reflective reasoning, and solution verification. 
    Your goal is to deliver clear, logically sound, and testable solutions to complex programming challenges with confidence and precision.
    </Identity>
    
    <Context>
    You are provided with a programming problem or codebase that requires a structured approach for analysis and resolution. 
    The process include generating the final solution by combining the resolved sub-problems, verifying correctness through testing, and providing the final code solution.
    </Context>
    
    <Task>
    {state["messages"]}
    </Task>
    
    <Instructions>
    Based on the resolved problems and their solutions, provide a score from 0 to 10 for the confidence level of correctness to the final solution. 
    Provide feedback to the solution and generate the final code solution based on the feedback proovided.
    </Instructions>
    
    <OUTPUT_INSTRUCT>
    Please provide a score from 0 to 10 for the confidence level of the each final solution. Please provide the scores in the following format:
    <SOLUTION_1_UNDERSTANDING_CONFIDENCE> Put your confidence score for the first understanding to the solution 1 here </SOLUTION_1_UNDERSTANDING_CONFIDENCE>
    <SOLUTION_1_REASONING_CONFIDENCE> Put your confidence score for the first reasoning to the solution 1 here </SOLUTION_1_REASONING_CONFIDENCE>
    <FEEDBACK_1> Provide feedback for the first solution </FEEDBACK_1>
    <SOLUTION> Put your final solution script here </SOLUTION>
    </OUTPUT_INSTRUCT>
    """

    return {"messages": [llm_feedback_model.invoke(prompt)]}

def routing_condition(state: State):
    # If the first solution is not confident, go back to code_sol_reasoning or code_understanding based 
    if state["messages"][-1].content.find("<SOLUTION_1_UNDERSTANDING_CONFIDENCE>") != -1:
        confidence_score = state["messages"][-1].content.split("<SOLUTION_1_UNDERSTANDING_CONFIDENCE>")[1].split("</SOLUTION_1_UNDERSTANDING_CONFIDENCE>")[0]
        # if the confidence score is less than 8, go back to code_sol_reasoning
        if int(confidence_score) < 8:
            return "code_solution_reasoning"
        
    # If the first reasoning is not confident, go back to code_sol_reasoning
    if state["messages"][-1].content.find("<SOLUTION_1_REASONING_CONFIDENCE>") != -1:
        confidence_score = state["messages"][-1].content.split("<SOLUTION_1_REASONING_CONFIDENCE>")[1].split("</SOLUTION_1_REASONING_CONFIDENCE>")[0]
        # if the confidence score is less than 8, go back to code_sol_reasoning
        if int(confidence_score) < 8:
            return "code_solution_reasoning"
    
    # if the soluton is confident, finish the process
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
import json
from concurrent.futures import ProcessPoolExecutor, as_completed
from tqdm import tqdm

# Function to process a single problem
def process_problem(task_id, problem):
    try:
        # Create or import graph locally in each worker
        graph = graph_builder.compile()

        if not problem:
            return {
                "error": f"Problem with task ID {task_id} not found in the dataset.",
                "task_id": task_id,
            }

        # Construct the state object
        state = {
            "messages": problem["complete_prompt"]
            + " based on the instruction: "
            + problem["instruct_prompt"]
        }

        # Generate response using the graph
        answer = graph.invoke(state)

        answer_snippet = (
            str(answer["messages"][-1].content)
            .strip()
            .split("<SOLUTION>")[1]
            .split("</SOLUTION>")[0]
        )

        # Extract Python code if present
        if "```python" in answer_snippet:
            answer_snippet = (
                answer_snippet.split("```python")[1].split("```")[0].strip()
            )

        # Prepare JSON object
        return {
            "task_id": task_id,
            "solution": answer_snippet,
            "completion": answer_snippet,
            "instruction_prompt": problem["instruct_prompt"],
            "test_prompt": problem["test"],
        }

    except Exception as e:
        return {
            "error": str(e),
            "task_id": task_id,
        }

# Parallel processing main script
if __name__ == "__main__":
    print("Starting sample generation...")

    # Define the number of workers
    NUM_WORKERS = 16  # Adjust based on your system

    # Output file
    output_file = "full_output.jsonl"

    with open(output_file, "w") as f:
        # Use ProcessPoolExecutor for parallel processing
        with ProcessPoolExecutor(max_workers=NUM_WORKERS) as executor:
            futures = []
            for i, (task_id, problem) in enumerate(problems.items()):
                if i >= NUM_SAMPLES:
                    break
                
                # Submit tasks to the executor
                futures.append(executor.submit(process_problem, task_id, problem))

            for future in tqdm(as_completed(futures), total=len(futures), desc="Processing Problems"):
                result = future.result()

                if "error" in result:
                    print(f"Error processing Task ID {result['task_id']}: {result['error']}")
                else:
                    # Write successful results to file
                    f.write(json.dumps(result) + "\n")

    print(f"Sample generation completed. Output saved to {output_file}")
