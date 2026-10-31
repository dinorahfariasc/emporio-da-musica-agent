import math

from app.embeddings import EMBEDDING_DIM
from app.embeddings.fake import FakeEmbedder


def _cos(a, b):
    return sum(x * y for x, y in zip(a, b, strict=True))


async def test_vectors_are_unit_length_and_deterministic():
    embedder = FakeEmbedder()
    (a,) = await embedder.embed(["devolver"], "query")
    (b,) = await embedder.embed(["devolver"], "document")
    assert len(a) == EMBEDDING_DIM
    assert math.isclose(math.sqrt(sum(x * x for x in a)), 1.0, abs_tol=1e-9)
    assert a == b


async def test_lexically_close_words_are_closer():
    devolver, devolucao, garantia = await FakeEmbedder().embed(
        ["devolver", "devolução", "garantia"], "query"
    )
    assert _cos(devolver, devolucao) > _cos(devolver, garantia)
