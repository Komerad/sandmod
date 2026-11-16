from dataclasses import dataclass
from typing import Literal

from .game import get_installation_health
from .types import ModDictType

AuditStatus = Literal[
    "current",
    "missing",
    "outdated",
    "unknown",
    "unavailable",
    "no_release",
]


@dataclass(frozen=True)
class AuditResult:
    mod_id: int
    name: str
    installed_file_id: int | None
    available_file_id: int | None
    installed_version: str | None
    available_version: str | None
    status: AuditStatus


def compare_mods(
    installed: list[ModDictType],
    remote: dict[int, dict],
    mods_root: Path,
) -> list[AuditResult]:
    results = []

    for mod in installed:
        mod_id = mod["ID"]

        profile = mod.get("Profile") or {}
        local_file = profile.get("modfile") or {}

        remote_mod = remote.get(mod_id)
        remote_file = remote_mod.get("modfile") or {} if remote_mod is not None else {}

        installed_id = local_file.get("id")
        available_id = remote_file.get("id")

        health = get_installation_health(mod, mods_root)

        if health == "missing":
            status = "missing"
        elif health == "unknown":
            status = "unknown"
        elif remote_mod is None:
            status = "unavailable"
        elif available_id is None:
            status = "no_release"
        elif installed_id is None:
            status = "unknown"
        elif installed_id == available_id:
            status = "current"
        else:
            status = "outdated"

        results.append(
            AuditResult(
                mod_id=mod_id,
                name=profile.get("name", "Unknown"),
                installed_file_id=installed_id,
                available_file_id=available_id,
                installed_version=local_file.get("version"),
                available_version=remote_file.get("version"),
                status=status,
            )
        )

    return results
