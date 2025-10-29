import os
from dotenv import load_dotenv
from typing import Optional

load_dotenv()

class BaseLLMClient:
    def generate(self, prompt: str, **kwargs) -> str:
        raise NotImplementedError("This method should be overridden by subclasses.")
    
class OpenAIClient(BaseLLMClient):
    def __init__(self, model_name="gpt-4o-mini"):
        from openai import OpenAI
        self.api_key = os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY environment variable not set.")
        self.client = OpenAI(api_key=self.api_key)
        self.model = model_name
    
    def generate(self, prompt: str, **kwargs) -> str:
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=kwargs.get("temperature", 0.2),
                max_tokens=kwargs.get("max_tokens", 2000),
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            raise RuntimeError(f"OpenAI API error: {str(e)}")

class GeminiClient(BaseLLMClient):
    def __init__(self, model_name="gemini-1.5-flash"):
        import google.generativeai as genai
        self.api_key = os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY environment variable not set.")
        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel(model_name)
    
    def generate(self, prompt: str, **kwargs) -> str:
        try:
            response = self.model.generate_content(
                prompt,
                generation_config={
                    "temperature": kwargs.get("temperature", 0.2),
                    "max_output_tokens": kwargs.get("max_tokens", 2000),
                }
            )
            return response.text.strip()
        except Exception as e:
            raise RuntimeError(f"Gemini API error: {str(e)}")

class AnthropicClient(BaseLLMClient):
    def __init__(self, model_name="claude-3-5-haiku-20241022"):
        import anthropic
        self.api_key = os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable not set.")
        self.client = anthropic.Anthropic(api_key=self.api_key)
        self.model = model_name
    
    def generate(self, prompt: str, **kwargs) -> str:
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=kwargs.get("max_tokens", 2000),
                temperature=kwargs.get("temperature", 0.2),
                messages=[{"role": "user", "content": prompt}]
            )
            return response.content[0].text.strip()
        except Exception as e:
            raise RuntimeError(f"Anthropic API error: {str(e)}")

class LocalLlamaClient(BaseLLMClient):
    def __init__(self, model_path: Optional[str] = None):
        from llama_cpp import Llama
        self.model_path = model_path or os.getenv("LOCAL_LLM_PATH")
        if not self.model_path or not os.path.exists(self.model_path):
            raise ValueError("LOCAL_LLM_PATH is not set or file does not exist.")
        self.model = Llama(model_path=self.model_path, n_ctx=36000)
    
    def generate(self, prompt: str, **kwargs) -> str:
        response = self.model(prompt, max_tokens=kwargs.get("max_tokens", 512))
        return response["choices"][0]["text"].strip()


def get_llm_client(llm_type: str = "openai", model_name: Optional[str] = None) -> BaseLLMClient:
    """
    Get an LLM client based on the specified type.
    
    Args:
        llm_type: Type of LLM client ("openai", "gemini", "anthropic", "local")
        model_name: Specific model name to use
    
    Returns:
        BaseLLMClient: Configured LLM client
    """
    if llm_type == "openai":
        return OpenAIClient(model_name=model_name or "gpt-4o-mini")
    elif llm_type == "gemini":
        return GeminiClient(model_name=model_name or "gemini-1.5-flash")
    elif llm_type == "anthropic":
        return AnthropicClient(model_name=model_name or "claude-3-5-haiku-20241022")
    elif llm_type == "local":
        return LocalLlamaClient(model_path=model_name)
    else:
        raise ValueError(f"Unsupported LLM type: {llm_type}. Choose from: openai, gemini, anthropic, local")


