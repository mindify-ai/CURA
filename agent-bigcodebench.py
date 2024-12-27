from tqdm import tqdm
from dotenv import load_dotenv
from bigcodebench.data import get_bigcodebench, load_solutions
from bigcodebench.data.utils import CACHE_DIR
from bigcodebench.eval import PASS, compatible_eval_result, estimate_pass_at_k, untrusted_check
from bigcodebench.gen.util import trusted_check
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from typing import Annotated

from typing_extensions import TypedDict

from langchain_openai import ChatOpenAI
import os
import json
import traceback

load_dotenv()

# Load BigCodeBench dataset and solutions
subset = "bigcodebench_instruct"  # Replace with your subset name
problems = get_bigcodebench(subset=subset)
solutions_path = "./solutions.jsonl"  # Replace with the path to your solutions
solutions = load_solutions(solutions_path)

NUM_SAMPLES = 50
NUM_CORRECT = 0

print(f"Loaded {len(solutions)} solutions for testing.")

class State(TypedDict):
    messages: Annotated[list, add_messages]


graph_builder = StateGraph(State)

llm = ChatOpenAI(
    model="gpt-4o-mini",
    api_key="your-api-key",
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


def evaluate_solution(problem, solution_code, cache_dir, max_time_limit=5.0):
    """
    Evaluates a solution using untrusted and trusted checks.

    Args:
        problem: The problem details from the dataset.
        solution_code: The solution code to evaluate.
        cache_dir: Path to the cache directory.
        max_time_limit: Maximum allowed time for execution.

    Returns:
        bool: True if the solution passes all checks, False otherwise.
    """
    try:
        # Untrusted Check
        untrusted_result = untrusted_check(
            solution_code,
            problem["test"],
            problem["entry_point"],
            max_as_limit=30 * 1024,
            max_data_limit=30 * 1024,
            max_stack_limit=10,
            min_time_limit=1.0,
            gt_time_limit=max_time_limit,
        )

        if untrusted_result[0] != PASS:
            print("Untrusted check failed.")
            return False

        # Trusted Check
        trusted_result = trusted_check(
            solution_code + "\n" + problem["canonical_solution"],
            problem["test"],
            problem["entry_point"],
            max_as_limit=30 * 1024,
            max_data_limit=30 * 1024,
            max_stack_limit=10,
            min_time_limit=1.0,
            cache_dir=cache_dir,
        )

        if trusted_result[0] != PASS:
            print("Trusted check failed.")
            return False

    except Exception as e:
        print(f"Error during evaluation: {traceback.format_exc()}")
        return False

    return True


graph_builder.add_node("code_understanding", code_understanding)
graph_builder.add_node("code_sol_reasoning", code_sol_reasoning)
graph_builder.set_entry_point("code_understanding")
graph_builder.add_edge("code_understanding", "code_sol_reasoning")
graph_builder.set_finish_point("code_sol_reasoning")
graph = graph_builder.compile()

# Ensure cache directory exists
os.makedirs(CACHE_DIR, exist_ok=True)

# Update the main loop to integrate testing
for i, solution in tqdm(enumerate(solutions), total=NUM_SAMPLES):
    if i >= NUM_SAMPLES:
        break
    print("--------------------")

    task_id = solution["task_id"]
    problem = problems.get(task_id)

    if not problem:
        print(f"Problem with task ID {task_id} not found in the dataset.")
        continue

    state = {
        "messages": problem["complete_prompt"]
        + " based on the instruction: "
        + problem["instruct_prompt"]
    }

    answer = graph.invoke(state)
    answer_snippet = (
        str(answer["messages"][-1].content).strip().replace("OUTPUT:", "").strip()
    )

    if "```python" in answer_snippet:
        answer_snippet = answer_snippet.split("```python")[1].split("```")[0].strip()

    print("Answer Snippet:", answer_snippet)

    # Evaluate the solution
    tests_passed = evaluate_solution(problem, answer_snippet, CACHE_DIR)
    if tests_passed:
        NUM_CORRECT += 1

    print(f"Correct: {tests_passed}")
    print("--------------------")

print(f"Correct: {NUM_CORRECT}/{NUM_SAMPLES}")
print(f"Accuracy: {NUM_CORRECT / NUM_SAMPLES * 100:.2f}%")
