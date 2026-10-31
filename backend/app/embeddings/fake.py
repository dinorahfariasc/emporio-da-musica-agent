"""Deterministic offline embedder: hashed character n-grams (research R3)."""

import math
import re
import unicodedata
from collections.abc import Sequence
from hashlib import blake2b

from app.embeddings import EMBEDDING_DIM, InputType
from app.text import nfc

_NON_WORD = re.compile(r"[^a-z0-9]+")


def _plain(text: str) -> str:
    decomposed = unicodedata.normalize("NFD", nfc(text).casefold())
    return "".join(c for c in decomposed if not unicodedata.combining(c))


def _vector(text: str) -> list[float]:
    vec = [0.0] * EMBEDDING_DIM
    # The first line is the title (product name, policy breadcrumb): its words weigh triple, as
    # a real model would let a short title dominate a long body.
    title, _, body = _plain(text).partition("\n")
    words = [(w, 3.0) for w in _NON_WORD.split(title)] + [(w, 1.0) for w in _NON_WORD.split(body)]
    for word, boost in words:
        if not word:
            continue
        padded = f"^{word}$"
        # The whole word counts too, so an exact token (a model number) outweighs shared n-grams.
        grams = [(padded, 2.0 * boost)] + [
            (padded[i : i + n], boost) for n in (3, 4, 5) for i in range(len(padded) - n + 1)
        ]
        for gram, weight in grams:
            h = int.from_bytes(blake2b(gram.encode(), digest_size=8).digest(), "big")
            vec[h % EMBEDDING_DIM] += weight if (h >> 63) & 1 else -weight
    norm = math.sqrt(sum(v * v for v in vec))
    return [v / norm for v in vec] if norm else vec


class FakeEmbedder:
    provider = "fake"
    model = "fake-ngram-v1"

    async def embed(self, texts: Sequence[str], input_type: InputType) -> list[list[float]]:
        return [_vector(t) for t in texts]
