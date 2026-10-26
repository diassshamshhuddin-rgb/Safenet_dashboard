"""
Тесты для FastAPI REST API (SafeNet KZ).
"""

from fastapi.testclient import TestClient
from src.api.app import app


def test_health():
    with TestClient(app) as client:
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "не выносит вердиктов" in data["disclaimer"]


def test_analyze_endpoint():
    with TestClient(app) as client:
        payload = {
            "id": "case_test_api_01",
            "text": "Вложи 5000 тг забери 15000 тг уже завтра на Kaspi. Места ограничены!",
            "channel_or_account": "@test_channel",
            "platform": "telegram",
        }
        response = client.post("/api/v1/analyze", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["score"] >= 50.0
        assert data["primary_track"] == "pyramid"
        assert "признаки" in data["disclaimer"].lower()
        assert len(data["triggered_features"]) > 0


def test_cases_queue_and_feedback():
    with TestClient(app) as client:
        response = client.get("/api/v1/cases")
        assert response.status_code == 200
        cases = response.json()
        assert len(cases) > 0

        target_case_id = cases[0]["case"]["id"]
        feedback_payload = {
            "case_id": target_case_id,
            "decision": "Подтвердить наличие признаков",
            "comment": "Проверено аналитиком, явная схема"
        }
        fb_response = client.post("/api/v1/feedback", json=feedback_payload)
        assert fb_response.status_code == 200
        assert fb_response.json()["status"] == "success"


def test_graph_and_metrics_endpoints():
    with TestClient(app) as client:
        graph_res = client.get("/api/v1/graph")
        assert graph_res.status_code == 200
        assert "graph" in graph_res.json()
        assert "top_clusters" in graph_res.json()

        metrics_res = client.get("/api/v1/metrics")
        assert metrics_res.status_code == 200
        assert "test_results_full_pipeline" in metrics_res.json()