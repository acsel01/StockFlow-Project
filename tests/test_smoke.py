from app import create_app


def test_health_endpoint(tmp_path):
    app = create_app({
        "TESTING": True,
        "DATABASE": str(tmp_path / "test.db"),
    })

    response = app.test_client().get("/health")

    assert response.status_code == 200
    assert response.get_json()["status"] == "ok"
