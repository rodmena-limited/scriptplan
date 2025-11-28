"""Flask web API for ScriptPlan."""

import hashlib
import json
import shutil
import tempfile
from pathlib import Path
from typing import Optional

from flask import Flask, jsonify, request, render_template

from scriptplan.cli.main import run_scriptplan

app = Flask(__name__, static_folder='static', template_folder='templates')


@app.route('/', methods=['GET'])
def home():
    """Homepage with interactive Gantt chart."""
    return render_template('index.html')


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint."""
    return jsonify({'status': 'ok'})


@app.route('/api/report', methods=['POST'])
def generate_report():
    """
    Generate a report from TJP content.

    Request body:
    {
        "tjp": "project ... { ... }",
        "format": "json"  // optional, defaults to "json"
    }

    Response:
    {
        "data": [...],
        "columns": [...],
        "report_id": "sha256hash"
    }
    """
    if not request.is_json:
        return jsonify({'error': 'Content-Type must be application/json'}), 400

    data = request.get_json()
    tjp_content = data.get('tjp')
    output_format = data.get('format', 'json')

    if not tjp_content:
        return jsonify({'error': 'Missing required field: tjp'}), 400

    if output_format not in ['json', 'csv']:
        return jsonify({'error': 'Invalid format. Must be json or csv'}), 400

    # Create temp file for TJP content
    temp_file = None
    temp_output_dir = None

    try:
        # Auto-add taskreport if missing
        tjp_to_process = tjp_content
        if 'taskreport' not in tjp_content.lower():
            # Add a default taskreport
            tjp_to_process += '\n\ntaskreport auto_report "auto_report" {\n'
            tjp_to_process += '  formats csv\n'
            tjp_to_process += '  columns id, name, start, end\n'
            tjp_to_process += '  timeformat "%Y-%m-%d-%H:%M"\n'
            tjp_to_process += '}\n'

        # Write TJP to temp file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.tjp', delete=False) as f:
            f.write(tjp_to_process)
            temp_file = Path(f.name)

        # Create temp output directory
        temp_output_dir = Path(tempfile.mkdtemp(prefix='scriptplan_web_'))

        # Calculate content hash
        file_hash = hashlib.sha256(tjp_content.encode('utf-8')).hexdigest()

        # Run scriptplan
        success, error_msg = run_scriptplan(str(temp_file), str(temp_output_dir))

        if not success:
            return jsonify({'error': error_msg or 'Report generation failed'}), 400

        # Find generated output files - look for both JSON and CSV
        json_files = list(temp_output_dir.glob('*.json'))
        csv_files = list(temp_output_dir.glob('*.csv'))

        if not json_files and not csv_files:
            return jsonify({
                'error': 'Report generation completed but no output files found'
            }), 500

        # Prefer the requested format, fallback to whatever exists
        if output_format == 'json':
            if json_files:
                primary_output = json_files[0]
                actual_format = 'json'
            elif csv_files:
                # Convert CSV to JSON
                primary_output = csv_files[0]
                actual_format = 'csv'
            else:
                return jsonify({'error': 'No output files generated'}), 500
        else:  # csv
            if csv_files:
                primary_output = csv_files[0]
                actual_format = 'csv'
            elif json_files:
                # We could convert JSON to CSV, but for now just error
                return jsonify({
                    'error': 'Requested CSV but only JSON was generated'
                }), 400
            else:
                return jsonify({'error': 'No output files generated'}), 500

        # Read the file content
        with open(primary_output) as f:
            report_content = f.read()

        # Return based on actual format found
        if actual_format == 'json':
            try:
                report_data = json.loads(report_content)
                report_data['report_id'] = file_hash
                return jsonify(report_data)
            except json.JSONDecodeError as e:
                return jsonify({'error': f'Failed to parse generated JSON: {e}'}), 500
        else:  # csv
            # Convert CSV to JSON if JSON was requested
            if output_format == 'json':
                import csv
                import io

                reader = csv.DictReader(io.StringIO(report_content))
                raw_data = list(reader)

                # Normalize column names to lowercase
                columns = [col.lower() for col in (reader.fieldnames or [])]

                # Normalize keys in data to lowercase
                data = [{k.lower(): v for k, v in row.items()} for row in raw_data]

                return jsonify({
                    'data': data,
                    'columns': columns,
                    'report_id': file_hash
                })
            else:
                # Return CSV as text with normalized lowercase headers
                import csv
                import io

                reader = csv.reader(io.StringIO(report_content))
                rows = list(reader)

                if rows:
                    # Lowercase the header row
                    rows[0] = [col.lower() for col in rows[0]]

                # Convert back to CSV
                output = io.StringIO()
                writer = csv.writer(output)
                writer.writerows(rows)
                normalized_csv = output.getvalue()

                return normalized_csv, 200, {'Content-Type': 'text/csv'}

    except Exception as e:
        return jsonify({'error': str(e)}), 500

    finally:
        # Cleanup
        if temp_file and temp_file.exists():
            temp_file.unlink()
        if temp_output_dir and temp_output_dir.exists():
            shutil.rmtree(temp_output_dir)


if __name__ == '__main__':
    app.run(debug=True)
