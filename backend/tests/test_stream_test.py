from app.api import stream_test


def test_stream_emits_sse_chunks_then_done(make_client, monkeypatch):
    monkeypatch.setattr(stream_test, "INTERVAL_SECONDS", 0)

    with make_client().stream("GET", "/api/stream-test") as response:
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/event-stream")
        assert response.headers["cache-control"] == "no-cache"
        events = [line for line in response.iter_lines() if line.startswith("data: ")]

    assert events[0] == "data: chunk 1/10"
    assert len(events) == stream_test.CHUNKS + 1
    assert events[-1] == "data: [DONE]"
