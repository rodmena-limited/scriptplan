# The CLI schedules every project twice and labels scheduling exceptions as parse errors

**Ticket**: issuedb #26  
**Status**: open  
**Priority**: medium  
**Release**: 0.10.2

This file is the in-repo copy of the ticket's EARS spec and synthesis record.
Keep it in sync with `issuedb-cli context 26` whenever the spec or the chosen
alternative changes.

---

Found via trace defect 12. scriptplan/cli/main.py parse_files() called ProjectFileParser().parse(content), which schedules by default, then schedule() called project.schedule() again: every 'plan' run scheduled twice (doubling CLI time and making idempotency defects visible only through the CLI), and any exception raised while scheduling was printed as 'Error parsing project file: ...'. EARS: R1 (ubiquitous) The CLI shall schedule a project once per run. R2 (unwanted) If scheduling raises, then the CLI shall report it as a scheduling error. FIX: parse(content, schedule=False); schedule() schedules once and already labels its exceptions 'Error during scheduling'. Verified: 102 CLI-based tests (test_cli, test_plan_cli, test_examples, test_stated_dates, test_dependency_check) pass; main.py kept at 544 lines.
