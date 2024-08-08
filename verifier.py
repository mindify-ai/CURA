"""
Verifier module
"""

from openai import OpenAI


class Verifier:
    def __init__(self, isOpenAI: bool, model_name: str, config):
        """
        Verifier class

        Args:
            isOpenAI (bool): Whether to use OpenAI API
            model_name (str): Name of the model to use
            config (dict): Configuration dictionary

        Returns:
            None
        """
        self.config = config 
        self.isOpenAI = isOpenAI | True
        self.model_name = model_name | "gpt-4o-mini"

        if self.isOpenAI:
            self.client = OpenAI()

        else:
            self.client = None
            print("Verifier not initialized, no OpenAI client provided")

    def run_model_infer(self, prompt: str):
        """
        Run model inference

        Args:
            prompt (str): Prompt for the model

        Returns:
            str: Model output
        """
        # Run model
        response = self.client.chat.completions.create(
            model=self.model_name,
            messages=[
                {"role": "system", "content": "You are a helpful coding agent."},
                {"role": "user", "content": prompt},
            ],
        )

        return response.choices[0].message["content"]

    def run_verification(self, coder_output):
        # Run verification
        pass

    def generate_supervision(self, data):
        # Generate supervision
        pass
