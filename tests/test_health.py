from app.main import index, health


def test_health_returns_ok() -> None:
    assert health() == {"status": "ok"}


def test_index_serves_frontend() -> None:
    response = index()

    assert response.path.name == "index.html"
    assert response.path.parent.name == "static"
