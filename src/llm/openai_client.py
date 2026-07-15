import os
from typing import Generator, Dict, List
from openai import OpenAI, OpenAIError
from dotenv import load_dotenv
from .client import LLMClient, LLMError

class OpenAIClient(LLMClient):
    """Client for interacting with OpenAI's Chat Completions API with streaming support."""

    def __init__(self, api_key: str = None, model: str = "gpt-4o-mini"):
        load_dotenv()
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise LLMError("OpenAI API key not found. Please set OPENAI_API_KEY in your environment or .env file.")

        self.model = model
        try:
            self.client = OpenAI(api_key=self.api_key)
        except Exception as e:
            raise LLMError(f"Failed to initialize OpenAI client library: {e}")

    def stream_chat(self, messages: List[Dict[str, str]]) -> Generator[str, None, None]:
        """
        Sends the conversation history to OpenAI and yields response chunks.

        Args:
            messages: Conversation messages list in OpenAI format.

        Yields:
            Token content chunks.
        """
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                stream=True
            )
            for chunk in response:
                if len(chunk.choices) > 0:
                    content = chunk.choices[0].delta.content
                    if content is not None:
                        yield content
        except OpenAIError as e:
            raise LLMError(f"OpenAI API failure: {e}")
        except Exception as e:
            raise LLMError(f"Unexpected error communicating with OpenAI: {e}")
