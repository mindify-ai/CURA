# CURA - Code understanding and reasoning agent

## Getting started

Step 1: Open Docker and run the following command:

```bash
docker login
```

Step 2: un the following command to build the image:

```bash
docker build -t swe_img .
```

Step 3: Run the following Jupyter Notebook command to start the container:

```bash
ReAct_SWE.ipynb
```

Step 4: Add .env file to the root directory with the following content:

```bash
OPENAI_API_KEY=your_openai_api_key
```
