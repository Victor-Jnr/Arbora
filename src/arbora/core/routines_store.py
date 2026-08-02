"""Serialize trusted routines to/from local memory."""

from __future__ import annotations

from typing import Any

from arbora.core.types import ScopeGrant, TrustedRoutine


def routines_to_dicts(routines: list[TrustedRoutine]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for routine in routines:
        rows.append(
            {
                "id": routine.id,
                "name": routine.name,
                "plan_fingerprint": routine.plan_fingerprint,
                "version": routine.version,
                "enabled": routine.enabled,
                "goal_norm": routine.goal_norm,
                "scopes": [
                    {
                        "id": grant.id,
                        "adapter": grant.adapter,
                        "actions": sorted(grant.actions),
                        "paths": sorted(grant.paths),
                        "apps": sorted(grant.apps),
                        "commands": sorted(grant.commands),
                    }
                    for grant in routine.scopes
                ],
            }
        )
    return rows


def routines_from_dicts(rows: list[dict[str, Any]] | None) -> list[TrustedRoutine]:
    if not rows:
        return []
    routines: list[TrustedRoutine] = []
    for row in rows:
        scopes = [
            ScopeGrant(
                id=str(scope.get("id", "")),
                adapter=str(scope.get("adapter", "")),
                actions=frozenset(scope.get("actions") or []),
                paths=frozenset(scope.get("paths") or []),
                apps=frozenset(scope.get("apps") or []),
                commands=frozenset(scope.get("commands") or []),
            )
            for scope in row.get("scopes") or []
        ]
        routines.append(
            TrustedRoutine(
                id=str(row["id"]),
                name=str(row["name"]),
                plan_fingerprint=str(row["plan_fingerprint"]),
                scopes=scopes,
                version=int(row.get("version", 1)),
                enabled=bool(row.get("enabled", True)),
                goal_norm=str(row.get("goal_norm", "")),
            )
        )
    return routines
