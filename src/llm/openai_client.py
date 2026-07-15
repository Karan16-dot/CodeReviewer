import os
from typing import Generator, Dict, List, Any, Union
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

    def stream_chat(self, messages: List[Dict[str, str]], tools: List[Dict[str, Any]] = None) -> Generator[Union[str, Dict[str, Any]], None, None]:
        """
        Sends the conversation history to OpenAI and yields response chunks.

        Args:
            messages: Conversation messages list in OpenAI format.
            tools: Optional list of OpenAI tool schemas.

        Yields:
            Token content chunks (str) or a tool call dictionary block (dict).
        """
        try:
            kwargs = {
                "model": self.model,
                "messages": messages,
                "stream": True
            }
            if tools:
                kwargs["tools"] = tools

            response = self.client.chat.completions.create(**kwargs)
            tool_calls_accum = {}

            for chunk in response:
                if len(chunk.choices) == 0:
                    continue
                delta = chunk.choices[0].delta

                # Accumulate delta tool call structures if they exist
                tool_calls = getattr(delta, "tool_calls", None)
                if tool_calls:
                    for tc in tool_calls:
                        idx = tc.index
                        if idx not in tool_calls_accum:
                            tool_calls_accum[idx] = {
                                "id": getattr(tc, "id", None) or "",
                                "name": getattr(tc.function, "name", None) or "",
                                "arguments": getattr(tc.function, "arguments", None) or ""
                            }
                        else:
                            if getattr(tc, "id", None):
                                tool_calls_accum[idx]["id"] = tc.id
                            if getattr(tc.function, "name", None):
                                tool_calls_accum[idx]["name"] += tc.function.name
                            if getattr(tc.function, "arguments", None):
                                tool_calls_accum[idx]["arguments"] += tc.function.arguments

                if delta.content is not None:
                    yield delta.content

            if tool_calls_accum:
                yield {
                    "type": "tool_calls",
                    "calls": list(tool_calls_accum.values())
                }

        except OpenAIError as e:
            raise LLMError(f"OpenAI API failure: {e}")
        except Exception as e:
            raise LLMError(f"Unexpected error communicating with OpenAI: {e}")
