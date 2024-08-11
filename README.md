# Coder-verifier makes LLM a better coding agent

## Getting started

1. Open Docker and run the following command:

```bash
docker login
```

2. Run the following command to build the image:

```bash
docker build -t swe_img .
```

3. Run the following Jupyter Notebook command to start the container:

```bash
ReAct_SWE.ipynb
```

4. Add .env file to the root directory with the following content:

```bash
OPENAI_API_KEY=your_openai_api_key
```