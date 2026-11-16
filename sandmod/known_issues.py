"""Version-specific mod compatibility findings."""

from dataclasses import dataclass


@dataclass(frozen=True)
class KnownIssue:
    mod_id: int
    name: str
    version: str
    observed_on: str
    affected_maps: tuple[str, ...]
    signature: str
    symptom: str
    workaround: str
    confidence: str


KNOWN_ISSUES = (
    KnownIssue(
        mod_id=448415,
        name="Mud Village",
        version="1.9",
        observed_on="2026-11-15",
        affected_maps=("Hydro", "Assault"),
        signature="EXCEPTION_ACCESS_VIOLATION on FAsyncLoadingThread",
        symptom="Reproducible map-load crashes, including when loading Assault offline.",
        workaround="Quarantine Mud Village on the affected client; restart and retest.",
        confidence="High confidence in the observed conflict; underlying cause not isolated.",
    ),
)


def list_known_issues(mod_id: int | None = None) -> tuple[KnownIssue, ...]:
    return tuple(issue for issue in KNOWN_ISSUES if mod_id is None or issue.mod_id == mod_id)


def match_known_issue(mod_id: int, version: str | None) -> KnownIssue | None:
    if not isinstance(version, str):
        return None

    for issue in KNOWN_ISSUES:
        if issue.mod_id == mod_id and issue.version == version:
            return issue

    return None
