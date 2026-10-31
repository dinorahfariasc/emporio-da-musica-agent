import pytest

from app.db import connect
from app.embeddings import EmbeddingsUnavailable
from app.embeddings.fake import FakeEmbedder
from app.retrieval.hybrid import reset_index_cache
from etl.__main__ import seed


class CountingEmbedder(FakeEmbedder):
    def __init__(self):
        self.calls: list[tuple[int, str]] = []

    async def embed(self, texts, input_type):
        self.calls.append((len(texts), input_type))
        return await super().embed(texts, input_type)


class BrokenEmbedder(FakeEmbedder):
    async def embed(self, texts, input_type):
        raise EmbeddingsUnavailable("down")


@pytest.fixture
async def conn(local_database_url, tmp_path):
    reset_index_cache()
    await seed(local_database_url, report_path=tmp_path / "report.md")
    async with await connect(local_database_url) as connection:
        await connection.execute("TRUNCATE embedding_cache")  # cold query cache per test
        await connection.commit()
    async with await connect(local_database_url) as connection:
        yield connection
    reset_index_cache()


@pytest.fixture
def embedder():
    return CountingEmbedder()
