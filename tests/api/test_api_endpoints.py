# ABOUTME: Basic API endpoint availability tests

import pytest
from fastapi.testclient import TestClient

from voiceover_mage.api.main import app


class TestAPIEndpoints:
    """Test suite for API endpoint availability."""

    @pytest.fixture
    def client(self):
        """Create a test client."""
        return TestClient(app)

    def test_health_endpoint_exists(self, client):
        """Health endpoint should be accessible."""
        response = client.get("/api/v1/health")
        assert response.status_code == 200

    def test_health_endpoint_returns_status(self, client):
        """Health endpoint should return status information."""
        response = client.get("/api/v1/health")
        data = response.json()

        assert "status" in data
        assert "version" in data
        assert "database" in data

    def test_speak_endpoint_requires_text(self, client):
        """Speak endpoint should require text in request body."""
        response = client.post("/api/v1/npc/1/speak", json={})
        # Should fail validation (422) because text is required
        assert response.status_code == 422

    def test_speak_endpoint_validates_text(self, client):
        """Speak endpoint should validate text field."""
        response = client.post("/api/v1/npc/1/speak", json={"text": ""})
        # Empty text should fail min_length validation
        assert response.status_code == 422

    def test_openapi_schema_exists(self, client):
        """OpenAPI schema should be available."""
        response = client.get("/openapi.json")
        assert response.status_code == 200
        schema = response.json()
        assert "openapi" in schema
        assert "info" in schema
        assert "paths" in schema

    def test_api_title_and_version(self, client):
        """API should have correct title and version."""
        response = client.get("/openapi.json")
        schema = response.json()

        assert schema["info"]["title"] == "Voiceover Mage API"
        assert schema["info"]["version"] == "0.1.0"

    def test_speak_endpoint_in_schema(self, client):
        """Speak endpoint should be documented in OpenAPI schema."""
        response = client.get("/openapi.json")
        schema = response.json()

        assert "/api/v1/npc/{npc_id}/speak" in schema["paths"]
        speak_endpoint = schema["paths"]["/api/v1/npc/{npc_id}/speak"]
        assert "post" in speak_endpoint

    def test_health_endpoint_in_schema(self, client):
        """Health endpoint should be documented in OpenAPI schema."""
        response = client.get("/openapi.json")
        schema = response.json()

        assert "/api/v1/health" in schema["paths"]
        health_endpoint = schema["paths"]["/api/v1/health"]
        assert "get" in health_endpoint
