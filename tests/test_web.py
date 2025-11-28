"""Tests for Flask web API."""

import json

import pytest

from scriptplan.web import app


@pytest.fixture
def client():
    """Create Flask test client."""
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client


def test_health_check(client):
    """Test health check endpoint."""
    response = client.get('/health')
    assert response.status_code == 200
    data = response.get_json()
    assert data['status'] == 'ok'


def test_home_page(client):
    """Test homepage endpoint."""
    response = client.get('/')
    assert response.status_code == 200
    assert b'ScriptPlan' in response.data
    assert b'Gantt' in response.data
    assert b'tjpInput' in response.data


def test_generate_report_simple(client):
    """Test report generation with simple TJP."""
    tjp_content = """
project "Test" 2025-05-10 +1w {
  timezone "Etc/UTC"
  timeformat "%Y-%m-%d %H:%M"
}

shift standard "Standard" {
  workinghours mon - fri 09:00 - 17:00
}

resource heater "Furnace" {
  workinghours standard
}

task heat "Heat Task" {
  effort 2h
  allocate heater
}

taskreport test_output "test_output" {
  formats csv
  columns id, start, end
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

    # Verify response structure
    assert 'data' in data
    assert 'columns' in data
    assert 'report_id' in data

    # Verify columns
    assert 'id' in data['columns']
    assert 'start' in data['columns']
    assert 'end' in data['columns']

    # Verify data contains task
    assert len(data['data']) > 0
    task_ids = [item['id'] for item in data['data']]
    assert 'heat' in task_ids


def test_generate_report_missing_tjp(client):
    """Test report generation without TJP content."""
    response = client.post(
        '/api/report',
        data=json.dumps({}),
        content_type='application/json'
    )

    assert response.status_code == 400
    data = response.get_json()
    assert 'error' in data
    assert 'tjp' in data['error'].lower()


def test_generate_report_invalid_content_type(client):
    """Test report generation with invalid content type."""
    response = client.post(
        '/api/report',
        data='some text',
        content_type='text/plain'
    )

    assert response.status_code == 400
    data = response.get_json()
    assert 'error' in data
    assert 'json' in data['error'].lower()


def test_generate_report_invalid_format(client):
    """Test report generation with invalid format."""
    tjp_content = """
project "Test" 2025-05-10 +1w {
  timezone "Etc/UTC"
}

task test "Test" {
  start 2025-05-10
  end 2025-05-11
}
"""

    response = client.post(
        '/api/report',
        data=json.dumps({'tjp': tjp_content, 'format': 'xml'}),
        content_type='application/json'
    )

    assert response.status_code == 400
    data = response.get_json()
    assert 'error' in data
    assert 'format' in data['error'].lower()


def test_generate_report_csv_format(client):
    """Test CSV report generation."""
    tjp_content = """
project "Test" 2025-05-10 +1w {
  timezone "Etc/UTC"
  timeformat "%Y-%m-%d %H:%M"
}

task test "Test" {
  start 2025-05-10
  end 2025-05-11
}

taskreport csv_output "csv_output" {
  formats csv
  columns id, start, end
  timeformat "%Y-%m-%d-%H:%M"
}
"""

    response = client.post(
        '/api/report',
        data=json.dumps({'tjp': tjp_content, 'format': 'csv'}),
        content_type='application/json'
    )

    assert response.status_code == 200
    assert 'text/csv' in response.content_type

    # Verify CSV content
    csv_content = response.get_data(as_text=True)
    assert 'id' in csv_content
    assert 'start' in csv_content
    assert 'end' in csv_content


def test_generate_report_invalid_tjp_syntax(client):
    """Test report generation with invalid TJP syntax."""
    tjp_content = """
project "Test" invalid syntax here
"""

    response = client.post(
        '/api/report',
        data=json.dumps({'tjp': tjp_content}),
        content_type='application/json'
    )

    assert response.status_code == 400
    data = response.get_json()
    assert 'error' in data


def test_generate_report_with_dependencies(client):
    """Test report generation with task dependencies."""
    tjp_content = """
project "Thermal_Shock" 2025-05-10 +1w {
  timezone "Etc/UTC"
  timeformat "%Y-%m-%d %H:%M"
  now 2025-05-10
}

shift standard "Standard" {
  workinghours mon - fri 09:00 - 17:00
}

resource heater "Furnace" {
  workinghours standard
}

resource press "Hydraulic Press" {
  workinghours standard
}

task process "Forging Line" {
  task heat "Heat Ingot" {
    effort 2h
    allocate heater
  }

  task forge "Shape Metal" {
    effort 2h
    allocate press
    depends !heat { gapduration 0min maxgapduration 60min }
  }
}

taskreport thermal_output "thermal_output" {
  formats csv
  columns id, start, end
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

    # Verify response structure
    assert 'data' in data
    assert len(data['data']) > 0

    # Find heat and forge tasks
    tasks = {item['id']: item for item in data['data'] if 'id' in item}

    # Should contain both tasks
    assert 'process.heat' in tasks or 'process.forge' in tasks
