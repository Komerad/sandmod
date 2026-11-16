"""Display known mod compatibility issues without accessing mod.io."""

from ...known_issues import list_known_issues, match_known_issue


def print_issue_warning(mod_id: int, version: str | None) -> None:
    issue = match_known_issue(mod_id, version)

    if issue is None:
        return

    print(f"WARNING: Known issue with {issue.name} " f"{issue.version} (observed {issue.observed_on})")
    print(f"  {issue.symptom}")
    print(f"  Workaround: {issue.workaround}")
    print(f"  {issue.confidence}")


def sandmod_issues(mod_id: int | None = None) -> int:
    issues = list_known_issues(mod_id)

    if not issues:
        print("No known issues recorded.")
        return 0

    for issue in issues:
        print(f"{issue.name} ({issue.mod_id}) / version {issue.version}")
        print(f"  Observed: {issue.observed_on}")
        print(f"  Maps: {', '.join(issue.affected_maps)}")
        print(f"  Signature: {issue.signature}")
        print(f"  Symptom: {issue.symptom}")
        print(f"  Workaround: {issue.workaround}")
        print(f"  Confidence: {issue.confidence}")

    return 0
