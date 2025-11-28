"""Tests for auto-report injection in web API."""

import json

import pytest

from scriptplan.web import app


@pytest.fixture
def client():
    """Create Flask test client."""
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client


def test_auto_report_injection(client):
    """Test that taskreport is auto-injected when missing."""
    tjp_content = """
project "Test" 2025-05-10 +1w {
  timezone "Etc/UTC"
  timeformat "%Y-%m-%d %H:%M"
}

task test "Test Task" {
  start 2025-05-10
  duration 2d
}
"""

    response = client.post(
        '/api/report',
        data=json.dumps({'tjp': tjp_content}),
        content_type='application/json'
    )

    assert response.status_code == 200
    data = response.get_json()

    # Verify response structure
    assert 'data' in data
    assert 'columns' in data
    assert 'report_id' in data

    # Verify task data
    assert len(data['data']) > 0
    task = data['data'][0]
    assert task['id'] == 'test'
    assert task['name'] == 'Test Task'
    assert 'start' in task
    assert 'end' in task


def test_existing_taskreport_not_modified(client):
    """Test that existing taskreport is not modified."""
    tjp_content = """
project "Test" 2025-05-10 +1w {
  timezone "Etc/UTC"
  timeformat "%Y-%m-%d %H:%M"
}

task test "Test Task" {
  start 2025-05-10
  duration 2d
}

taskreport custom "custom" {
  formats csv
  columns id, start
  timeformat "%Y-%m-%d-%H:%M"
}
"""

    response = client.post(
        '/api/report',
        data=json.dumps({'tjp': tjp_content}),
        content_type='application/json'
    )

    assert response.status_code == 200
    data = response.get_json()

    # Should only have columns specified in custom report
    assert 'id' in data['columns']
    assert 'start' in data['columns']
    # 'end' and 'name' should not be present since custom report only has id, start
    assert len(data['columns']) == 2
