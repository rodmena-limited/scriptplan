from scriptplan.parser.tjp_parser import ProjectFileParser

content = """project "E-Commerce Platform" 2025-01-06 +4m {
  timezone "Etc/UTC"
  timeformat "%Y-%m-%d %H:%M"
  now 2025-01-15
}

shift standard "Standard" { workinghours mon-fri 9:00-17:00 }

resource dev "Developers" { workinghours standard }
resource pm "Management" { workinghours standard }

task project "E-Commerce" {
  task planning "Phase 1: Planning" {
    task req "Requirements" {
      start 2025-01-06
      effort 5d
      allocate pm
    }
    task arch "Architecture" {
      depends !req
      effort 1w
      allocate dev
    }
  }
}

taskreport gantt "gantt" {
  formats csv
  columns id, name, start, end
  timeformat "%Y-%m-%d"
}
"""

parser = ProjectFileParser()
project = parser.parse(content)
project.schedule()

for report in project.reports:
    report.generate_intermediate_format()
    if report.content and hasattr(report.content, 'table'):
        data = report.content.table.to_json()
        for item in data.get('data', []):
            print(item)
