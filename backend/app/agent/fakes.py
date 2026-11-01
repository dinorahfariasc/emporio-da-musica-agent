"""Offline test doubles for the agent: a tool-calling chat model and a scripted router."""

from collections.abc import Iterator, Sequence
from typing import Any

from langchain_core.callbacks import CallbackManagerForLLMRun
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, AIMessageChunk, BaseMessage
from langchain_core.outputs import ChatGeneration, ChatGenerationChunk, ChatResult
from pydantic import Field

from app.agent.router import FakeRouter

__all__ = ["FakeRouter", "FakeToolModel"]


class FakeToolModel(BaseChatModel):
    """Replays scripted `AIMessage`s and streams their tool calls as `tool_call_chunks`.

    The stock `GenericFakeChatModel` cannot stream tool calls or `bind_tools` (research R9).
    """

    script: Sequence[Any]  # AIMessage or str; a union would make pydantic coerce strings
    cursor: list[int] = Field(default_factory=lambda: [0])
    seen: list[list[BaseMessage]] = Field(default_factory=list)

    @property
    def _llm_type(self) -> str:
        return "fake-tool-model"

    def bind_tools(self, tools: Any, **kwargs: Any) -> "FakeToolModel":
        return self

    def _next(self, messages: list[BaseMessage]) -> AIMessage:
        self.seen.append(list(messages))
        if self.cursor[0] >= len(self.script):
            raise AssertionError("FakeToolModel script exhausted")
        item = self.script[self.cursor[0]]
        self.cursor[0] += 1
        return AIMessage(content=item) if isinstance(item, str) else item

    def _generate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: CallbackManagerForLLMRun | None = None,
        **kwargs: Any,
    ) -> ChatResult:
        return ChatResult(generations=[ChatGeneration(message=self._next(messages))])

    def _stream(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: CallbackManagerForLLMRun | None = None,
        **kwargs: Any,
    ) -> Iterator[ChatGenerationChunk]:
        message = self._next(messages)
        usage = {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}
        if message.tool_calls:
            for index, call in enumerate(message.tool_calls):
                import json

                chunk = AIMessageChunk(
                    content="",
                    id=message.id,
                    tool_call_chunks=[
                        {
                            "name": call["name"],
                            "args": json.dumps(call["args"]),
                            "id": call["id"],
                            "index": index,
                        }
                    ],
                )
                yield ChatGenerationChunk(message=chunk)
        else:
            text = message.content if isinstance(message.content, str) else ""
            words = text.split(" ")
            for i, word in enumerate(words):
                token = word if i == len(words) - 1 else word + " "
                chunk = AIMessageChunk(content=token, id=message.id)
                if run_manager:
                    run_manager.on_llm_new_token(token, chunk=ChatGenerationChunk(message=chunk))
                yield ChatGenerationChunk(message=chunk)
        yield ChatGenerationChunk(
            message=AIMessageChunk(content="", id=message.id, usage_metadata=usage)
        )
