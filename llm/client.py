import os
import sys
from dotenv import load_dotenv
from typing import Optional

load_dotenv()
class BaseLLMClient:
    def generate(self, prompt: str, **kwargs) -> str:
        raise NotImplementedError("This method should be overridden by subclasses.")
    
class OpenAIClient(BaseLLMClient):
    def __init__(self, model_name="gpt-3.5-turbo"):
        import openai 
        self.api_key = os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY environment variable not set.")
        openai.api_key = self.api_key
        self.client = openai
        self.model = model_name
    
    def generate(self,prompt: str, **kwargs) -> str:
        response = self.client.ChatCompletion.create(
            model = self.model,
            messages = [{"role": "user", "content": prompt}],
            temperature = kwargs.get("temperature", 0.2),
            max_tokens = kwargs.get("max_tokens", 500),
        )
        return response["choices"][0]["message"]["content"].strip()

class LocalLlamaClient(BaseLLMClient):
    def __init__(self, model_path: Optional[str] = None):
        from llama_cpp import Llama
        self.model_path = model_path or os.getenv("LOCAL_LLM_PATH")
        if not self.model_path or not os.path.exists(self.model_path):
            raise ValueError("LOCAL_LLM_PATH is not set or file does not exist.")
        self.model = Llama(model_path=self.model_path, n_ctx=2048)
    
    def generate(self, prompt: str, **kwargs) -> str:
        response = self.model(prompt, max_tokens=kwargs.get("max_tokens_",512))
        return response["choices"][0]["text"].strip()

def get_llm_client(llm_type: str = "local", model_name: Optional[str] = None) -> BaseLLMClient:
    if llm_type == "openai":
        return OpenAIClient(model_name=model_name)
    elif llm_type == "local":
        return LocalLlamaClient(model_path=model_name)
    else:
        raise ValueError(f"Unsupported LLM type: {llm_type}")


