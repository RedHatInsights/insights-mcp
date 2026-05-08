"""Custom DeepEval models (e.g. OpenAI-compatible inference endpoints)."""

from typing import Any, Optional

from deepeval.models.base_model import DeepEvalBaseLLM
from pydantic import BaseModel

from deepeval_support.http_llm import call_llm_api, make_llm_api_request


class CustomVLLMModel(DeepEvalBaseLLM):
    """Custom LLM model for deepeval that uses vLLM with OpenAI-compatible API.

    Current implementation of deepeval does not support vLLM Server with api_key yet.
    And the OpenAI class does not support custom models.
    """

    def __init__(
        self,
        api_url: Optional[str] = None,
        model_id: Optional[str] = None,
        api_key: Optional[str] = None,
        temperature: float = 0,
        **kwargs,
    ):
        if not api_url:
            raise ValueError("api_url must be provided for CustomVLLMModel")
        if not model_id:
            raise ValueError("model_id must be provided for CustomVLLMModel")

        self.api_url = api_url
        self.model_id = model_id or "default"
        self.api_key = api_key or ""

        if temperature < 0:
            raise ValueError("Temperature must be >= 0.")
        self.temperature = temperature
        super().__init__(self.model_id)

    # pylint: disable=arguments-differ
    def generate(  # type: ignore[override]
        self, prompt: str, schema: Optional[BaseModel] = None
    ) -> Any:
        if not schema:
            messages = [{"role": "user", "content": prompt}]
            return call_llm_api(self.api_url, self.model_id, self.api_key, messages, self.temperature)

        payload = {
            "model": self.model_id,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": self.temperature,
        }

        content = make_llm_api_request(self.api_url, self.api_key, payload)

        if schema:
            try:
                content = content.replace("```json", "").replace("```", "")
                return schema.model_validate_json(content)
            except Exception as exc:  # pylint: disable=broad-exception-caught
                error_message = (
                    f"The LLM {self.model_id} was expected to return a valid JSON object "
                    f"compatible with the schema {schema}. but it returned {content}. "
                    f"Error: {exc}"
                )
                raise ValueError(error_message) from exc

        return content

    # pylint: disable=arguments-differ
    async def a_generate(  # type: ignore[override]
        self, prompt: str, schema: Optional[BaseModel] = None
    ) -> str:
        return self.generate(prompt, schema)

    def load_model(self):
        return None

    def get_model_name(self):
        return f"{self.model_id} (vLLM)"


__all__ = ["CustomVLLMModel"]
