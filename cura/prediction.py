import dotenv
__import__('pysqlite3')
import sys
sys.modules['sqlite3'] = sys.modules.pop('pysqlite3')

from langgraph.prebuilt import create_react_agent
from langchain_openai import ChatOpenAI
from cura.vm import RepoVM
from cura.agent_tools import create_tools
from langchain_core.prompts import ChatPromptTemplate
from typing import TypedDict, Optional, Union, Literal
from langchain_core.pydantic_v1 import BaseModel, Field
from langgraph.graph import StateGraph, START, END
from langgraph.errors import GraphRecursionError
dotenv.load_dotenv()

system_prompt = "You are an autonomous programmer, and you are working with several tools to help you solve software engineering problems step by step. "\
"Your goal is to solve the issue provided by the user. You can use the tools provided to help you solve the issue. "

user_message = "We're currently solving the following issue within our repository.\n"\
"REPOSITORY: \n"\
"{repo}\n"\
"ISSUE: \n"\
"{issue}\n"\
"HINTS: \n"\
"{hints}\n"\
"INSTRUCTIONS:\n"\
"Now, you're going to solve this issue on your own. "\
"The repository has been cloned to the root directory and you are always in the root directory. The package has been installed. "\
"You are going to use the provided tools to help you solve this issue. Provide your reasoning for each step you take. "\
"Edit all the files you need to and run any checks or tests that you want. "\
"Remember, YOU CAN ONLY USE ONE TOOL AT A TIME. "\
"You should always wait for tool output before entering the next command. "\
"When you're satisfied with all of the changes you've made, you can submit your changes to the code base by simply using the submit tool. "\
"Note however that you cannot use any interactive session commands (e.g. python, vim) in this environment, but you can write scripts and run them. E.g. you can write a python script and then run it with `python <script_name>.py`. "\
"\n"\
"NOTE ABOUT THE EDIT TOOL: Indentation really matters! When editing a file, make sure to insert appropriate indentation before each line!"\
"\n"\
"IMPORTANT TIPS:\n"\
"1. If you open a file and need to get to an area around a specific line that is not in the first 100 lines, say line 583, don't just use the scroll_down command multiple times. Instead, use the goto 583 command. It's much quicker.\n"\
"2. If the bug reproduction script requires inputting/reading a specific file, such as buggy-input.png, and you'd like to understand how to input that file, conduct a search in the existing repo code, to see whether someone else has already done that. Do this by running the tool: find_file buggy-input.png. If that doesn't work, use the linux 'find' command in bash tool.\n"\
"3. Always start by trying to replicate the bug that the issues discusses. If the issue includes code for reproducing the bug, we recommend that you re-implement that in your environment, and run it to make sure you can reproduce the bug. "\
"Then start trying to fix it. When you think you've fixed the bug, re-run the bug reproduction script to make sure that the bug has indeed been fixed.\n"\
"4. Never use python -c to run code. Instead, write a script and run it with python <script_name>.py.\n"\
"5. If you need to install a package, never use online package commands. Use local pip install commands. For example, Use pip install /sqlfluff where /sqlfluff is the path to the package instead of pip install sqlfluff.\n"\
"6. If a command is interactive, add --force if the command supports it. For example, sqlfluff fix --force.\n"\
"7. If the issue provides a configuration, use it to make sure you are using the same configuration as the issue.\n"      

prompt_template = ChatPromptTemplate(
    messages=[
        ('system', system_prompt),
        ('user', user_message)
    ]
)

def do_prediction(data):
    with RepoVM(image_name='swe_img:latest', repo_name=data['repo'], commit_hash=data['base_commit']) as vm:
        
        llm = ChatOpenAI(model='gpt-4o-mini', temperature=0, top_p=0.95)
        tools = create_tools(vm)
        agent = prompt_template | create_react_agent(llm, tools=tools.values())

        final_state = agent.invoke( 
            input={
                "repo": data['repo'],
                "issue": data['problem_statement'],
                "hints": data['hints_text']
            },
            config={
                "recursion_limit": 32,
            }
        )
        submit_patches = [message for message in final_state['messages'] if message.name == 'submit']
        if len(submit_patches) > 0:
            submit_patch = submit_patches[-1].content
        else:
            submit_patch = None
    
    return submit_patch


class AgentState(TypedDict):
    input_data: dict
    plan: list[str]
    current_step: int
    last_step_result: bool
    history: list[tuple[str, str]]
    
class Plan(BaseModel):
    steps: list[str] = Field(..., description="different steps to follow, should be in sorted order")

planner_prompt = ChatPromptTemplate.from_template(
"""You are an autonomous programmer, and you are assigned to propose a pull request to solve a software engineering problem. \
Here is the objective: {objective}. Finally, you need to provide step that submit the total patch. \
For the given objective, come up with a simple step by step plan. \
This plan should involve individual tasks, that if executed correctly will yield the correct answer. Do not add any superfluous steps. \
Make sure that each step has all the information needed. Do not put numbered lists before each step.
Some Notes: 
1. The repository has been cloned to the root directory and you are always in the root directory, which is {repo_path}.
2. The repository has been installed. No need to install the repository again.
3. Use test-driven to solve the problem. Write tests first and then write the code to pass the tests.
4. Never create new branches or switch to other branches. Never check out to other commits. Always edit the files in the current commit. \
"""
)

class ExecuteResult(BaseModel):
    summary: str = Field(..., description="Summary of the execution")
    result: bool = Field(..., description="True if the execution was successful, False otherwise")

class ReplanAction(BaseModel):
    revised_plan: Optional[Plan] = Field(None, description="New plan to replace the current plan. If None, keep the current plan")
    

step_solver_prompt = ChatPromptTemplate.from_template(
"""Here is the objective of the plan: {objective}\nHere is the full plan: {plan}\nHere is the result of previous steps execution: {history}\nNow, you are assigned to solve the step: {step}.' \
Only do the step that you are assigned to do. You have only {recursion_limit} tools calls to solve the step. Do not waste your calls. If you are about to run out of calls, explain why you are not able to solve the step and stop using tools. \
If you think the step is not solvable, just stop using tools and explain why it is not solvable. The program will handle the rest. \
Some Notes: \
1. The repository has been cloned to the root directory and you are always in the root directory, which is {repo_path}. \
2. When using tools with paths as arguments, always use absolute paths, never use relative paths. \
3. pytest is installed. You can use bash_command tool to run pytest. Always use pytest to run specific single test files or several tests. Never use pytest in the whole repository. \
4. Use multiple tools to save calls. \
"""
)

step_solving_summary_prompt = ChatPromptTemplate(
    messages=[
        ('system', 'In the following plan: {plan}, with the step: {step}, write a brief summary of the execution, and based on the plan, give a boolean result of the execution that indicates whether the step was successful or not. \
You need to provide accurate information about the execution. \
You should provide sufficient information that the next step agent does not need to run tools to retrieve the same information. \
Some Notes: \
1. If creating files or editing files, provide the absolute path of the file. \
2. If you are running tests, provide the test results. \
3. All of the files you mentioned MUST be ABSOLUTE paths. \
4. It step solver agent need more steps to process the request, you should summarize that the agent was not successful. \
'),
        ("placeholder", "{messages}"),
        ('user', 'Now give me your execution summary and result.'),
    ]
)

replanner_prompt = ChatPromptTemplate.from_template(
    """For the given objective, come up with a simple step by step plan. \
This plan should involve individual tasks, that if executed correctly will yield the correct answer. Do not add any superfluous steps. \
Make sure that each step has all the information needed - do not skip steps. \
If the last step is not successful or the step summary is not satisfactory, update the plan, otherwise keep the plan. \
If the current step is the last step, the program will automatically submit the patch. You don't need to do any step to submit the patch. \
    
When you update the plan, the provided plan will replace redundant steps with the new steps. \
For example, if the plan is ["step1", "step2", "step3"] and we are currently finishing step2, you can provide ['step4', 'step5'] and the new plan will be ["step1", "step2", "step4", "step5"]. The next step will be step4. \

Your objective was this:
{objective}

Your original plan was this:
{plan}

You have currently done the following steps: (The last one is the latest step)
{history}

The last step success was: {last_step_result}.

Now update the plan by providing the next steps, or return None if you want to keep the current plan.
Some Notes:
1. If you want to keep the current plan, just return None.
2. The repository has been cloned to the root directory and you are always in the root directory, which is {repo_path}.
3. The repository has been installed. No need to install the repository again.
4. Use test-driven to solve the problem. Write tests first and then write the code to pass the tests.
5. pytest is installed. You can use bash_command tool to run pytest. Always use pytest to run specific single test files or several tests. Never use pytest in the whole repository. \
6. Never create new branches or switch to other branches. Never check out to other commits. Always edit the files in the current commit. \
7. Never create new branches or switch to other branches. Never check out to other commits. Always edit the files in the current commit. \
8. If meeting package version conflicts or missing packages, use pip to downgrade or install the package. \
"""
)

def do_prediction_plan(data):
    with RepoVM(image_name='swe_img:latest', repo_name=data['repo'], commit_hash=data['base_commit']) as vm:
        
        execution_limit = 20
        
        tools = create_tools(vm)
        planner_llm = ChatOpenAI(model='gpt-4o-mini', temperature=0, top_p=0.95)
        step_solver_llm = ChatOpenAI(model='gpt-4o-mini', temperature=0, top_p=0.95)
        
        replanner_llm = ChatOpenAI(model='gpt-4o-mini', temperature=0, top_p=0.95)
        
        planner = planner_prompt | planner_llm.with_structured_output(Plan)
        step_solver = step_solver_prompt | create_react_agent(step_solver_llm, tools=tools.values())
        replanner = replanner_prompt | replanner_llm.with_structured_output(ReplanAction)
        
        def plan_step(state: AgentState):
            objective = f"{data['problem_statement']}\n\nHINTS:\n{data['hints_text']}"
            plan = planner.invoke(
                input={
                    "objective": objective,
                    "repo_path": vm.repo_path
                }
            )
            state['plan'] = plan.steps
            return state
        
        def execute_step(state: AgentState):
            objective = f"{data['problem_statement']}\n\nHINTS:\n{data['hints_text']}"
            
            summarizer = step_solving_summary_prompt | ChatOpenAI(model='gpt-4o-mini', temperature=0, top_p=0.95).with_structured_output(ExecuteResult)
            try:
                result_messages = step_solver.invoke(
                    input={
                        "objective": objective,
                        "plan": state['plan'],
                        "history": state['history'],
                        "repo_path": vm.repo_path,
                        "step": state['plan'][state['current_step']],
                        "recursion_limit": execution_limit
                    },
                    config={
                        "recursion_limit": execution_limit
                    }
                )['messages']
            except GraphRecursionError:
                result_messages = [("user", "The agent exceeded the recursion limit and was unable to solve the step.")]
            summary = summarizer.invoke(
                input={
                    "plan": state['plan'],
                    "step": state['plan'][state['current_step']],
                    "messages": result_messages
                }
            )
            state['history'].append((state['plan'][state['current_step']], summary.summary))
            state['last_step_result'] = summary.result
            return state
        
        def replan_step(state: AgentState):
            objective = f"{data['problem_statement']}\n\nHINTS:\n{data['hints_text']}"
            replan_action: ReplanAction = replanner.invoke(
                input={
                    "objective": objective,
                    "plan": state['plan'],
                    "history": state['history'],
                    "repo_path": vm.repo_path,
                    "last_step_result": state['last_step_result']
                }
            )
            if replan_action.revised_plan is None:
                plan = state['plan']
            else:
                plan = state['plan'][:state['current_step']+1] + replan_action.revised_plan.steps
            state['plan'] = plan
            state['current_step'] += 1
            return state
            
            
        def should_end(state: AgentState) -> Literal["execute_step", "__end__"]:
            if state['current_step'] >= len(state['plan']):
                return "__end__"
            else:
                return "execute_step"
        
        workflow = StateGraph(AgentState)
        workflow.add_node(plan_step)
        workflow.add_node(execute_step)
        workflow.add_node(replan_step)
        
        workflow.add_edge(START, "plan_step")
        workflow.add_edge("plan_step", "execute_step")
        workflow.add_edge("execute_step", "replan_step")
        workflow.add_conditional_edges("replan_step", should_end)
        
        graph = workflow.compile()
        
        init_state: AgentState = {
            "input_data": data,
            "plan": [],
            "current_step": 0,
            "last_step_result": False,
            "history": [],
        }
        try:
            graph.invoke(init_state, config={"recursion_limit": 20})
        except GraphRecursionError:
            pass
        patch = vm.interface.get_patch_file(vm.repo_path)
        return patch
        
        