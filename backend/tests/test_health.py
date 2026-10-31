from app import db


def test_health_without_database_configured(make_client):
    response = make_client(database_url=None).get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "db": "not_configured"}


def test_health_reports_unavailable_database(make_client, monkeypatch):
    async def failing_ping(_url: str) -> None:
        raise OSError("connection refused")

    monkeypatch.setattr(db, "ping", failing_ping)

    response = make_client(database_url="postgresql://nowhere/db").get("/api/health")

    assert response.status_code == 503
    assert response.json() == {"status": "degraded", "db": "unavailable"}


def test_health_with_real_database(make_client, database_url):
    response = make_client(database_url=database_url).get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "db": "ok"}
