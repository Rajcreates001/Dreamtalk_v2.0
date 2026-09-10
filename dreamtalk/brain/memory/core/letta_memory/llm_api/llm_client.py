# Adapted from Letta (MemGPT) - Apache 2.0 License
from typing import TYPE_CHECKING, Optional

from dreamtalk.brain.memory.core.letta_memory.llm_api.llm_client_base import LLMClientBase
from dreamtalk.brain.memory.core.letta_memory.schemas.enums import ProviderType

if TYPE_CHECKING:
    from dreamtalk.brain.memory.core.letta_memory.orm import User


class LLMClient:
    """Factory class for creating LLM clients based on the model endpoint type."""

    @staticmethod
    def create(
        provider_type: ProviderType,
        put_inner_thoughts_first: bool = True,
        actor: Optional["User"] = None,
    ) -> Optional[LLMClientBase]:
        """
        Create an LLM client based on the model endpoint type.

        Args:
            provider: The model endpoint type
            put_inner_thoughts_first: Whether to put inner thoughts first in the response

        Returns:
            An instance of LLMClientBase subclass

        Raises:
            ValueError: If the model endpoint type is not supported
        """
        match provider_type:
            case ProviderType.google_ai:
                from dreamtalk.brain.memory.core.letta_memory.llm_api.google_ai_client import GoogleAIClient

                return GoogleAIClient(
                    put_inner_thoughts_first=put_inner_thoughts_first,
                    actor=actor,
                )
            case ProviderType.google_vertex:
                from dreamtalk.brain.memory.core.letta_memory.llm_api.google_vertex_client import GoogleVertexClient

                return GoogleVertexClient(
                    put_inner_thoughts_first=put_inner_thoughts_first,
                    actor=actor,
                )
            case ProviderType.anthropic:
                from dreamtalk.brain.memory.core.letta_memory.llm_api.anthropic_client import AnthropicClient

                return AnthropicClient(
                    put_inner_thoughts_first=put_inner_thoughts_first,
                    actor=actor,
                )
            case ProviderType.bedrock:
                from dreamtalk.brain.memory.core.letta_memory.llm_api.bedrock_client import BedrockClient

                return BedrockClient(
                    put_inner_thoughts_first=put_inner_thoughts_first,
                    actor=actor,
                )
            case ProviderType.together:
                from dreamtalk.brain.memory.core.letta_memory.llm_api.together_client import TogetherClient

                return TogetherClient(
                    put_inner_thoughts_first=put_inner_thoughts_first,
                    actor=actor,
                )
            case ProviderType.azure:
                from dreamtalk.brain.memory.core.letta_memory.llm_api.azure_client import AzureClient

                return AzureClient(
                    put_inner_thoughts_first=put_inner_thoughts_first,
                    actor=actor,
                )
            case ProviderType.xai:
                from dreamtalk.brain.memory.core.letta_memory.llm_api.xai_client import XAIClient

                return XAIClient(
                    put_inner_thoughts_first=put_inner_thoughts_first,
                    actor=actor,
                )
            case ProviderType.zai | ProviderType.zai_coding:
                from dreamtalk.brain.memory.core.letta_memory.llm_api.zai_client import ZAIClient

                return ZAIClient(
                    put_inner_thoughts_first=put_inner_thoughts_first,
                    actor=actor,
                )
            case ProviderType.groq:
                from dreamtalk.brain.memory.core.letta_memory.llm_api.groq_client import GroqClient

                return GroqClient(
                    put_inner_thoughts_first=put_inner_thoughts_first,
                    actor=actor,
                )
            case ProviderType.minimax:
                from dreamtalk.brain.memory.core.letta_memory.llm_api.minimax_client import MiniMaxClient

                return MiniMaxClient(
                    put_inner_thoughts_first=put_inner_thoughts_first,
                    actor=actor,
                )
            case ProviderType.openrouter:
                # OpenRouter uses OpenAI-compatible API, so we can use the OpenAI client directly
                from dreamtalk.brain.memory.core.letta_memory.llm_api.openai_client import OpenAIClient

                return OpenAIClient(
                    put_inner_thoughts_first=put_inner_thoughts_first,
                    actor=actor,
                )
            case ProviderType.deepseek:
                from dreamtalk.brain.memory.core.letta_memory.llm_api.deepseek_client import DeepseekClient

                return DeepseekClient(
                    put_inner_thoughts_first=put_inner_thoughts_first,
                    actor=actor,
                )
            case ProviderType.baseten:
                from dreamtalk.brain.memory.core.letta_memory.llm_api.baseten_client import BasetenClient

                return BasetenClient(
                    put_inner_thoughts_first=put_inner_thoughts_first,
                    actor=actor,
                )
            case ProviderType.fireworks:
                from dreamtalk.brain.memory.core.letta_memory.llm_api.fireworks_client import FireworksClient

                return FireworksClient(
                    put_inner_thoughts_first=put_inner_thoughts_first,
                    actor=actor,
                )
            case ProviderType.chatgpt_oauth:
                from dreamtalk.brain.memory.core.letta_memory.llm_api.chatgpt_oauth_client import ChatGPTOAuthClient

                return ChatGPTOAuthClient(
                    put_inner_thoughts_first=put_inner_thoughts_first,
                    actor=actor,
                )
            case _:
                from dreamtalk.brain.memory.core.letta_memory.llm_api.openai_client import OpenAIClient

                return OpenAIClient(
                    put_inner_thoughts_first=put_inner_thoughts_first,
                    actor=actor,
                )
