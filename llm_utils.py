"""LLM factory — ensures all agents and chains use consistent configuration.

Centralizes ChatOpenAI creation so base_url, api_key, and model are
always passed correctly, especially for compatible APIs (opencode/GLM/etc.).
"""

from typing import Optional

from langchain_core.language_models import BaseChatModel
from langchain_openai import ChatOpenAI

from config import config


def get_llm(
    model: Optional[str] = None,
    temperature: Optional[float] = None,
    **kwargs,
) -> BaseChatModel:
    """Build a configured ChatOpenAI instance.

    Automatically injects base_url from config for compatible API support.
    """
    return ChatOpenAI(
        model=model or config.llm.model,
        temperature=temperature if temperature is not None else config.llm.temperature,
        api_key=config.llm.openai_api_key,
        base_url=config.llm.base_url or None,  # None = default OpenAI
        **kwargs,
    )
