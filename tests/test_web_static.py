"""Tests for static file serving."""

import pytest

from scriptplan.web import app


@pytest.fixture
def client():
    """Create Flask test client."""
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client


def test_serve_gantt_js(client):
    """Test serving frappe-gantt JavaScript."""
    response = client.get('/static/js/frappe-gantt.umd.js')
    assert response.status_code == 200
    assert b'Gantt' in response.data or b'gantt' in response.data


def test_serve_gantt_css(client):
    """Test serving frappe-gantt CSS."""
    response = client.get('/static/css/frappe-gantt.css')
    assert response.status_code == 200
    assert b'gantt' in response.data or b'bar' in response.data
