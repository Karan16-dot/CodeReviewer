import pytest
from unittest.mock import patch, MagicMock
from llm.client import LLMError
from llm.openai_client import OpenAIClient

def test_missing_api_key():
    """Verify that initialization fails with LLMError if OPENAI_API_KEY is not set."""
    with patch.dict("os.environ", {}, clear=True), patch("os.getenv", return_value=None):
        with pytest.raises(LLMError) as exc_info:
            OpenAIClient(api_key=None)
        assert "OpenAI API key not found" in str(exc_info.value)

def test_client_initialization():
    """Verify initialization is successful when API key is provided."""
    with patch("llm.openai_client.OpenAI") as mock_openai:
        client = OpenAIClient(api_key="test-key")
        assert client.api_key == "test-key"
        mock_openai.assert_called_once_with(api_key="test-key")

class MockDelta:
    def __init__(self, content):
        self.content = content

class MockChoice:
    def __init__(self, content):
        self.delta = MockDelta(content)

class MockChunk:
    def __init__(self, content):
        self.choices = [MockChoice(content)]

def test_stream_chat_success():
    """Verify stream_chat successfully streams and yields response chunks."""
    with patch("llm.openai_client.OpenAI") as mock_openai_class:
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client

        # Instantiate client
        client = OpenAIClient(api_key="test-key")

        # Configure mocked response stream
        mock_stream = [
            MockChunk("Hello"),
            MockChunk(" there,"),
            MockChunk(" human!"),
        ]
        mock_client.chat.completions.create.return_value = mock_stream

        messages = [{"role": "user", "content": "hi"}]
        chunks = list(client.stream_chat(messages))

        assert chunks == ["Hello", " there,", " human!"]
        mock_client.chat.completions.create.assert_called_once_with(
            model="gpt-4o-mini",
            messages=messages,
            stream=True
        )

def test_stream_chat_api_error():
    """Verify stream_chat wraps OpenAI API errors in LLMError."""
    from openai import APIError
    with patch("llm.openai_client.OpenAI") as mock_openai_class:
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client

        client = OpenAIClient(api_key="test-key")

        # Mock completions.create to raise an APIError
        # APIError in OpenAI SDK requires (message, request, body)
        mock_request = MagicMock()
        mock_error = APIError("API Rate limit exceeded", request=mock_request, body=None)
        mock_client.chat.completions.create.side_effect = mock_error

        with pytest.raises(LLMError) as exc_info:
            list(client.stream_chat([{"role": "user", "content": "hi"}]))
        assert "OpenAI API failure" in str(exc_info.value)
