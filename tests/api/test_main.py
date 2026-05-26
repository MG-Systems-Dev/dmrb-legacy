import asyncio
import importlib
import json

import pytest
from fastapi import HTTPException
from starlette.requests import Request
from starlette.responses import FileResponse, JSONResponse


@pytest.fixture
def main_module(monkeypatch):
    monkeypatch.setenv("SETUP_KEY", "test-setup-key")
    monkeypatch.setenv("SECRET_KEY", "test-secret-key")
    module = importlib.import_module("api.main")
    return importlib.reload(module)


def test_root_returns_diagnostics_when_frontend_missing(main_module, monkeypatch, tmp_path):
    missing_dist = tmp_path / "missing-dist"
    monkeypatch.setattr(main_module, "frontend_dist", missing_dist)
    monkeypatch.setattr(main_module, "FRONTEND_INDEX", missing_dist / "index.html")

    response = main_module.serve_spa_index()

    assert isinstance(response, JSONResponse)
    assert json.loads(response.body) == {
        "status": "ok",
        "frontend_dist_exists": False,
        "index_html_exists": False,
    }


def test_root_serves_index_when_frontend_exists(main_module, monkeypatch, tmp_path):
    frontend_dist = tmp_path / "dist"
    frontend_dist.mkdir()
    index_html = frontend_dist / "index.html"
    index_html.write_text("<html></html>", encoding="utf-8")
    monkeypatch.setattr(main_module, "frontend_dist", frontend_dist)
    monkeypatch.setattr(main_module, "FRONTEND_INDEX", index_html)

    response = main_module.serve_spa_index()

    assert isinstance(response, FileResponse)
    assert response.path == index_html


def test_spa_route_404s_when_frontend_missing(main_module, monkeypatch, tmp_path):
    missing_dist = tmp_path / "missing-dist"
    monkeypatch.setattr(main_module, "frontend_dist", missing_dist)
    monkeypatch.setattr(main_module, "FRONTEND_INDEX", missing_dist / "index.html")

    with pytest.raises(HTTPException, match="Frontend build not available"):
        main_module.serve_spa_routes("dashboard")


def test_non_api_404_returns_json_when_frontend_missing(main_module, monkeypatch, tmp_path):
    missing_dist = tmp_path / "missing-dist"
    monkeypatch.setattr(main_module, "frontend_dist", missing_dist)
    monkeypatch.setattr(main_module, "FRONTEND_INDEX", missing_dist / "index.html")
    request = Request({"type": "http", "method": "GET", "path": "/dashboard", "headers": []})

    response = asyncio.run(main_module._404_handler(request, HTTPException(status_code=404)))

    assert isinstance(response, JSONResponse)
    assert response.status_code == 404
    assert json.loads(response.body) == {"detail": "Frontend build not available"}
