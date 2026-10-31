"""Vercel AI SDK UI message stream (v1) — the subset of chunks this backend emits.

Contract: docs/contracts/chat-stream.md. Fixtures: contracts/chat-stream/fixtures/.
"""

import json
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter
from pydantic.alias_generators import to_camel

STREAM_HEADERS = {
    "x-vercel-ai-ui-message-stream": "v1",
    "Cache-Control": "no-cache",
    "X-Accel-Buffering": "no",
}
DONE = "data: [DONE]\n\n"


class _Model(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, extra="forbid")


class Start(_Model):
    type: Literal["start"] = "start"
    message_id: str | None = None


class StartStep(_Model):
    type: Literal["start-step"] = "start-step"


class FinishStep(_Model):
    type: Literal["finish-step"] = "finish-step"


class TextStart(_Model):
    type: Literal["text-start"] = "text-start"
    id: str


class TextDelta(_Model):
    type: Literal["text-delta"] = "text-delta"
    id: str
    delta: str


class TextEnd(_Model):
    type: Literal["text-end"] = "text-end"
    id: str


class ToolInputAvailable(_Model):
    type: Literal["tool-input-available"] = "tool-input-available"
    tool_call_id: str
    tool_name: str
    input: dict[str, Any]


class ToolOutputAvailable(_Model):
    type: Literal["tool-output-available"] = "tool-output-available"
    tool_call_id: str
    output: Any


class ToolOutputError(_Model):
    type: Literal["tool-output-error"] = "tool-output-error"
    tool_call_id: str
    error_text: str


Availability = Literal["in_stock", "out_of_stock", "coming_soon", "discontinued"]


class ProductCard(_Model):
    id: int
    name: str
    category_id: int
    price_brl: float
    promo_price_brl: float | None
    discount_percent: int | None
    availability: Availability


class ProductsData(_Model):
    products: list[ProductCard]


class DataProducts(_Model):
    type: Literal["data-products"] = "data-products"
    id: str
    data: ProductsData


class Route(_Model):
    intent: str
    confidence: float
    router: Literal["jev", "haiku", "fake"]


class Usage(_Model):
    input_tokens: int
    output_tokens: int


class MessageMetadata(_Model):
    route: Route
    model: str
    usage: Usage


class MessageMetadataChunk(_Model):
    type: Literal["message-metadata"] = "message-metadata"
    message_metadata: MessageMetadata


class Finish(_Model):
    type: Literal["finish"] = "finish"
    finish_reason: Literal["stop", "length", "error", "other"] | None = None


class Error(_Model):
    type: Literal["error"] = "error"
    error_text: str


Chunk = Annotated[
    Start
    | StartStep
    | FinishStep
    | TextStart
    | TextDelta
    | TextEnd
    | ToolInputAvailable
    | ToolOutputAvailable
    | ToolOutputError
    | DataProducts
    | MessageMetadataChunk
    | Finish
    | Error,
    Field(discriminator="type"),
]
chunk_adapter: TypeAdapter[Chunk] = TypeAdapter(Chunk)


def encode(chunk: _Model) -> str:
    """Serialize one chunk as an SSE event, exactly as the fixtures are written.

    Unset optional fields are omitted, while fields explicitly set to None are kept as null
    (e.g. a product without promotion), so the frontend always sees a stable shape.
    """
    data = {"type": chunk.type, **chunk.model_dump(mode="json", by_alias=True, exclude_unset=True)}
    return f"data: {json.dumps(data, ensure_ascii=False, separators=(',', ':'))}\n\n"


class ErrorBody(_Model):
    code: Literal[
        "unauthorized", "rate_limited", "budget_exhausted", "invalid_request", "internal_error"
    ]
    message: str
    retry_after_seconds: int | None = None


class ErrorResponse(_Model):
    error: ErrorBody


class TextUIPart(_Model):
    model_config = ConfigDict(extra="ignore")
    type: Literal["text"]
    text: str


class UIMessage(_Model):
    model_config = ConfigDict(extra="ignore")
    id: str
    role: Literal["user", "assistant", "system"]
    # Non-text parts (tool calls, data) are kept as raw dicts; the agent only reads text.
    parts: list[TextUIPart | dict[str, Any]]


class ChatRequest(_Model):
    model_config = ConfigDict(extra="ignore")
    id: str
    messages: list[UIMessage] = Field(min_length=1)
    trigger: Literal["submit-message", "regenerate-message"]
    message_id: str | None = None
