import dotenv


from langgraph.prebuilt import create_react_agent
from langchain_openai import ChatOpenAI
from vm import RepoVM
from agent_tools import create_tools
from langchain_core.prompts import ChatPromptTemplate
dotenv.load_dotenv()

system_prompt = "You are an autonomous programmer, and you are working with several tools to help you solve software engineering problems."

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
"7. If the issue provides a configuration, use it to make sure you are using the same configuration as the issue.\n" \
"8. You will need to index and query the codebase first to understand the structure of the codebase. Use the index tool to index the codebase and the query tool to query the codebase. "\

prompt_template = ChatPromptTemplate(
    messages=[
        ('system', system_prompt),
        ('user', user_message)
    ]
)

def do_prediction(data):
    with RepoVM(image_name='swe_img:latest', repo_name=data['repo'], commit_hash=data['base_commit']) as vm:
        
        llm = ChatOpenAI(model='gpt-4o-mini', temperature=0)
        tools = create_tools(vm)
        agent = prompt_template | create_react_agent(llm, tools=tools.values())

        final_state = agent.invoke(
            input={
                "repo": data['repo'],
                "issue": data['problem_statement'],
                "hints": data['hints_text']
            },
            config={
                "recursion_limit": 40,
            }
        )
        submit_patches = [message for message in final_state['messages'] if message.name == 'submit']
        if len(submit_patches) > 0:
            submit_patch = submit_patches[-1].content
        else:
            submit_patch = None
    
    return submit_patch