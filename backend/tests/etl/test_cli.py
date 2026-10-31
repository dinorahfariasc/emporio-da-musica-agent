import psycopg
import pytest

from app.config import Settings
from etl import __main__ as cli

REMOTE = "postgresql://user:s3cret@ep-example.neon.tech/neondb"


def _settings(**values) -> Settings:
    return Settings(_env_file=None, **values)


@pytest.fixture
def no_seed(monkeypatch):
    calls = []

    async def fake_seed(url, *args, **kwargs):
        calls.append(url)

    monkeypatch.setattr(cli, "seed", fake_seed)
    return calls


LOCAL = "postgresql://emporio:s3cret@localhost:5434/emporio"


def test_missing_database_url_is_refused(no_seed, monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("DATABASE_URL_UNPOOLED", raising=False)

    assert cli.main([], _settings()) == 1
    assert no_seed == []


def test_remote_target_needs_yes(no_seed, capsys):
    assert cli.main([], _settings(database_url=REMOTE)) == 1

    out = capsys.readouterr().out
    assert "target: ep-example.neon.tech/neondb (remote)" in out
    assert "s3cret" not in out
    assert no_seed == []


def test_remote_target_with_yes_passes_the_guard(no_seed, capsys):
    assert cli.main(["--yes"], _settings(database_url=REMOTE)) == 0
    assert no_seed == [REMOTE]


def test_unpooled_url_is_preferred(no_seed):
    unpooled = REMOTE.replace("neondb", "direct")
    settings = _settings(database_url=REMOTE, database_url_unpooled=unpooled)

    assert cli.main(["--yes"], settings) == 0
    assert no_seed == [unpooled]


def test_fake_embedder_is_refused_in_production(no_seed):
    settings = _settings(database_url=REMOTE, environment="production")

    assert cli.main(["--yes"], settings) == 1
    assert no_seed == []


def test_local_target_needs_no_confirmation(no_seed, capsys):
    assert cli.main([], _settings(database_url=LOCAL)) == 0

    out = capsys.readouterr().out
    assert "target: localhost/emporio (local)" in out
    assert "s3cret" not in out
    assert no_seed == [LOCAL]


def test_refusals_print_the_target_without_the_password(no_seed, capsys):
    production = _settings(database_url=REMOTE, environment="production")

    assert cli.main(["--yes"], production) == 1

    out = capsys.readouterr().out
    assert "target: ep-example.neon.tech/neondb (remote)" in out
    assert "s3cret" not in out


def test_production_with_the_real_embedder_is_allowed(no_seed):
    settings = _settings(
        database_url=REMOTE, environment="production", embeddings_provider="gemini"
    )

    assert cli.main(["--yes"], settings) == 0
    assert no_seed == [REMOTE]


def test_neon_pooler_url_is_refused_without_unpooled(no_seed, capsys):
    pooled = "postgresql://user:s3cret@ep-example-pooler.neon.tech/neondb"

    assert cli.main(["--yes"], _settings(database_url=pooled)) == 1
    assert no_seed == []
    assert "s3cret" not in capsys.readouterr().out


def test_connection_errors_do_not_echo_the_url(monkeypatch, caplog):
    async def failing_seed(url, *args, **kwargs):
        raise psycopg.OperationalError(f"connection to {url} failed")

    monkeypatch.setattr(cli, "seed", failing_seed)

    assert cli.main(["--yes"], _settings(database_url=REMOTE)) == 1
    assert "OperationalError connecting to ep-example.neon.tech/neondb (remote)" in caplog.text
    assert "s3cret" not in caplog.text
    assert "user" not in caplog.text
