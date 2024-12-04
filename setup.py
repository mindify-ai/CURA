from setuptools import setup

setup(
    name='cura',
    version='1.0',
    packages=['cura'],
    install_requires=[
        'docker',
        'datasets',
        'langchain',
        'langchain-core',
        'langchain-community',
        'langgraph',
        'langsmith',
        'langchain-openai==0.1.20',
        'python-dotenv',
        'gitpython',
        'flask',
        'psycopg[binary]>=3.1.19',
        'markupsafe==2.0.1',
        'directory_tree',
        'pylint',
        'chromadb',
        # 'pysqlite3',
        'git+https://github.com/princeton-nlp/SWE-bench.git#egg=swebench',
        'langchain-huggingface',
        'langchain-text-splitters',
        'langchain-chroma',
        'pysqlite3-binary'
    ],
    entry_points={
        'console_scripts': [
            'cura=cura.cli:main'
        ]
    },
    author='Mark Chen, Cheng Pong Huang',
    author_email='mark@mindifyai.dev',
    description='A package for CURA - Code Understanding and Reasoning Agent',
    url='https://github.com/mindify-ai/cura',
)