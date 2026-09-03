import tempfile
import os
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import pytest

from main import app
import database
from models import MonitoringTarget


@pytest.fixture
def client_with_temp_db():
    # Create temporary SQLite file
    temp_fd, temp_db_path = tempfile.mkstemp(suffix=".db")
    os.close(temp_fd)
    db_url = f"sqlite:///{temp_db_path}"

    # Patch database engine and SessionLocal
    engine = create_engine(db_url, connect_args={"check_same_thread": False})
    TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    # Replace in module
    database.engine.dispose()
    database.engine = engine
    database.SessionLocal = TestSessionLocal

    # Initialize tables
    database.init_db()

    client = TestClient(app)

    yield client

    client.close()
    try:
        os.unlink(temp_db_path)
    except OSError:
        pass


def test_create_target(client_with_temp_db):
    client = client_with_temp_db

    response = client.post("/targets", json={"url": "https://example.com"})
    assert response.status_code == 201
    data = response.json()
    assert data["url"] == "https://example.com"
    assert "id" in data
    assert "created_at" in data


def test_list_targets(client_with_temp_db):
    client = client_with_temp_db
    # Create two targets
    client.post("/targets", json={"url": "https://one.example.com"})
    client.post("/targets", json={"url": "https://two.example.com"})

    response = client.get("/targets")
    assert response.status_code == 200
    data = response.json()
    urls = {t["url"] for t in data}
    assert "https://one.example.com" in urls
    assert "https://two.example.com" in urls


def test_duplicate_url_rejected(client_with_temp_db):
    client = client_with_temp_db
    response1 = client.post("/targets", json={"url": "https://dup.example.com"})
    assert response1.status_code == 201

    response2 = client.post("/targets", json={"url": "https://dup.example.com"})
    assert response2.status_code == 409


def test_invalid_url_rejected(client_with_temp_db):
    client = client_with_temp_db
    response = client.post("/targets", json={"url": "ftp://invalid.example.com"})
    assert response.status_code == 422


def test_delete_target(client_with_temp_db):
    client = client_with_temp_db
    create = client.post("/targets", json={"url": "https://delete.example.com"})
    assert create.status_code == 201
    tid = create.json()["id"]

    del_resp = client.delete(f"/targets/{tid}")
    assert del_resp.status_code == 200

    # Ensure gone
    list_resp = client.get("/targets")
    urls = {t["url"] for t in list_resp.json()}
    assert "https://delete.example.com" not in urls


def test_delete_nonexistent_target_returns_404(client_with_temp_db):
    client = client_with_temp_db
    resp = client.delete("/targets/99999")
    assert resp.status_code == 404
