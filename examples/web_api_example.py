"""Example usage of ScriptPlan Flask Web API."""

import json
import requests

# Example 1: Simple report generation
def example_simple():
    """Generate a simple report via the web API."""
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

    response = requests.post(
        'http://localhost:5000/api/report',
        json={'tjp': tjp_content},
        headers={'Content-Type': 'application/json'}
    )

    if response.status_code == 200:
        data = response.json()
        print("Report generated successfully!")
        print(f"Report ID: {data['report_id']}")
        print(f"Columns: {data['columns']}")
        print(f"Tasks: {len(data['data'])}")
        print("\nData:")
        print(json.dumps(data, indent=2))
    else:
        print(f"Error: {response.json()}")


# Example 2: CSV output
def example_csv():
    """Generate a CSV report via the web API."""
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

    response = requests.post(
        'http://localhost:5000/api/report',
        json={'tjp': tjp_content, 'format': 'csv'},
        headers={'Content-Type': 'application/json'}
    )

    if response.status_code == 200:
        print("CSV Report generated successfully!")
        print(response.text)
    else:
        print(f"Error: {response.json()}")


# Example 3: Using with curl
def example_curl():
    """Show how to use the API with curl."""
    print("Example curl command:")
    print("""
curl -X POST http://localhost:5000/api/report \\
  -H "Content-Type: application/json" \\
  -d '{
    "tjp": "project \\"Test\\" 2025-05-10 +1w { timezone \\"UTC\\" } task test \\"Test\\" { start 2025-05-10 end 2025-05-11 } taskreport output \\"output\\" { formats csv columns id, start, end }",
    "format": "json"
  }'
""")


if __name__ == '__main__':
    print("=" * 60)
    print("ScriptPlan Web API Examples")
    print("=" * 60)
    print("\nMake sure the web server is running:")
    print("  plan web 5000")
    print("\nOr with custom port:")
    print("  plan web 8777")
    print("\n" + "=" * 60 + "\n")

    # Uncomment to run examples (requires Flask server running)
    # example_simple()
    # example_csv()
    example_curl()
