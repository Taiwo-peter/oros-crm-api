"""
Tests for Oros CRM API
Run with: python -m pytest tests/ -v
"""
import json
import pytest
import sys
import os

# Add src to path so we can import app
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from app import app


@pytest.fixture
def client():
    """Create a test client."""
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client


class TestHealthEndpoint:
    """Tests for the /health endpoint."""

    def test_health_returns_200(self, client):
        """Health endpoint should return 200."""
        response = client.get('/health')
        assert response.status_code in [200, 503]

    def test_health_returns_json(self, client):
        """Health endpoint should return JSON."""
        response = client.get('/health')
        data = json.loads(response.data)
        assert 'service' in data
        assert 'status' in data
        assert 'timestamp' in data

    def test_health_service_name(self, client):
        """Health should report the correct service name."""
        response = client.get('/health')
        data = json.loads(response.data)
        assert data['service'] == 'crm-api'


class TestIndexEndpoint:
    """Tests for the / endpoint."""

    def test_index_returns_200(self, client):
        """Root endpoint should return 200."""
        response = client.get('/')
        assert response.status_code == 200

    def test_index_returns_service_info(self, client):
        """Root endpoint should return service info."""
        response = client.get('/')
        data = json.loads(response.data)
        assert data['service'] == 'crm-api'
        assert 'version' in data
        assert 'endpoints' in data


class TestContactsEndpoint:
    """Tests for the /api/v1/contacts endpoint."""

    def test_create_contact_missing_fields(self, client):
        """Creating a contact without required fields should return 400."""
        response = client.post('/api/v1/contacts',
                               data=json.dumps({"phone": "08012345678"}),
                               content_type='application/json')
        assert response.status_code == 400

    def test_create_contact_empty_body(self, client):
        """Creating a contact with empty body should return 400."""
        response = client.post('/api/v1/contacts',
                               data=json.dumps({}),
                               content_type='application/json')
        assert response.status_code == 400

    def test_get_nonexistent_contact(self, client):
        """Getting a contact that doesn't exist should return 404."""
        response = client.get('/api/v1/contacts/99999')
        assert response.status_code == 404

    def test_delete_nonexistent_contact(self, client):
        """Deleting a contact that doesn't exist should return 404."""
        response = client.delete('/api/v1/contacts/99999')
        assert response.status_code == 404
