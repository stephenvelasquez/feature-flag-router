#!/usr/bin/env python3
"""Feature Flag Router — Lightweight feature flags with targeting and rollouts."""

import hashlib
import json
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set


@dataclass
class Flag:
    name: str
    enabled: bool = False
    rollout_percent: int = 100
    target_users: List[str] = field(default_factory=list)
    target_rules: Dict[str, List[str]] = field(default_factory=dict)
    depends_on: Optional[str] = None
    description: str = ""


@dataclass
class AuditEntry:
    timestamp: float
    flag_name: str
    action: str
    details: str


class FlagRouter:
    def __init__(self):
        self._flags: Dict[str, Flag] = {}
        self._audit_log: List[AuditEntry] = []

    def add_flag(
        self,
        name: str,
        enabled: bool = True,
        rollout_percent: int = 100,
        target_users: Optional[List[str]] = None,
        target_rules: Optional[Dict[str, List[str]]] = None,
        depends_on: Optional[str] = None,
        description: str = "",
    ):
        flag = Flag(
            name=name,
            enabled=enabled,
            rollout_percent=rollout_percent,
            target_users=target_users or [],
            target_rules=target_rules or {},
            depends_on=depends_on,
            description=description,
        )
        self._flags[name] = flag
        self._log(name, "created", f"enabled={enabled}, rollout={rollout_percent}%")

    def is_enabled(
        self,
        flag_name: str,
        user_id: Optional[str] = None,
        attributes: Optional[Dict[str, str]] = None,
    ) -> bool:
        flag = self._flags.get(flag_name)
        if not flag:
            return False

        if not flag.enabled:
            return False

        # Check dependency
        if flag.depends_on:
            parent = self._flags.get(flag.depends_on)
            if not parent or not parent.enabled:
                return False

        # Check user targeting
        if flag.target_users and user_id:
            if user_id in flag.target_users:
                return True

        # Check attribute targeting
        if flag.target_rules and attributes:
            match = all(
                attributes.get(key) in values
                for key, values in flag.target_rules.items()
            )
            if match:
                return True
            if flag.target_users or flag.target_rules:
                # If targeting rules exist but didn't match, check rollout
                pass

        # Check percentage rollout
        if user_id and flag.rollout_percent < 100:
            bucket = self._hash_bucket(flag_name, user_id)
            return bucket < flag.rollout_percent

        # No user_id provided — return enabled status
        if not flag.target_users and not flag.target_rules:
            return flag.enabled

        return False

    def disable(self, flag_name: str):
        flag = self._flags.get(flag_name)
        if flag:
            flag.enabled = False
            self._log(flag_name, "disabled", "kill switch activated")

    def enable(self, flag_name: str):
        flag = self._flags.get(flag_name)
        if flag:
            flag.enabled = True
            self._log(flag_name, "enabled", "reactivated")

    def set_rollout(self, flag_name: str, percent: int):
        flag = self._flags.get(flag_name)
        if flag:
            old = flag.rollout_percent
            flag.rollout_percent = max(0, min(100, percent))
            self._log(flag_name, "rollout_changed", f"{old}% -> {flag.rollout_percent}%")

    def list_flags(self) -> List[Dict]:
        results = []
        for f in self._flags.values():
            results.append({
                "name": f.name,
                "enabled": f.enabled,
                "rollout_percent": f.rollout_percent,
                "target_users": len(f.target_users),
                "description": f.description,
            })
        return results

    def audit_log(self) -> List[Dict]:
        return [
            {"time": e.timestamp, "flag": e.flag_name, "action": e.action, "details": e.details}
            for e in self._audit_log
        ]

    @classmethod
    def from_config(cls, path: str) -> "FlagRouter":
        with open(path) as f:
            config = json.load(f)

        router = cls()
        for name, props in config.get("flags", {}).items():
            router.add_flag(
                name=name,
                enabled=props.get("enabled", False),
                rollout_percent=props.get("rollout_percent", 100),
                target_users=props.get("target_users", []),
                target_rules=props.get("target_rules", {}),
                depends_on=props.get("depends_on"),
                description=props.get("description", ""),
            )
        return router

    @staticmethod
    def _hash_bucket(flag_name: str, user_id: str) -> int:
        h = hashlib.sha256(f"{flag_name}:{user_id}".encode()).hexdigest()
        return int(h[:8], 16) % 100

    def _log(self, flag_name: str, action: str, details: str):
        self._audit_log.append(
            AuditEntry(timestamp=time.time(), flag_name=flag_name, action=action, details=details)
        )

    def print_dashboard(self):
        print(f"\n  Feature Flags")
        print(f"  {'=' * 60}")
        for f in self._flags.values():
            status = "ON " if f.enabled else "OFF"
            rollout = f"{f.rollout_percent}%" if f.rollout_percent < 100 else "all"
            targets = f"{len(f.target_users)} users" if f.target_users else ""
            print(f"  [{status}]  {f.name:<30} rollout: {rollout:<6} {targets}")
            if f.description:
                print(f"         {f.description}")
        print()


def demo():
    router = FlagRouter()

    router.add_flag("new_checkout", enabled=True, rollout_percent=25,
                     description="Redesigned checkout — Q1 2026")
    router.add_flag("dark_mode", enabled=True, target_users=["user_42", "user_88"],
                     description="Dark mode beta")
    router.add_flag("legacy_api", enabled=False, description="Kill switch for v1 API")
    router.add_flag("enterprise_search", enabled=True,
                     target_rules={"plan": ["enterprise", "business"]},
                     description="Advanced search for paid plans")

    router.print_dashboard()

    # Test evaluations
    test_cases = [
        ("new_checkout", "user_001", None),
        ("new_checkout", "user_050", None),
        ("dark_mode", "user_42", None),
        ("dark_mode", "user_99", None),
        ("legacy_api", "user_001", None),
        ("enterprise_search", "user_001", {"plan": "enterprise"}),
        ("enterprise_search", "user_001", {"plan": "free"}),
    ]

    print("  Evaluation Results:")
    print(f"  {'─' * 60}")
    for flag, uid, attrs in test_cases:
        result = router.is_enabled(flag, user_id=uid, attributes=attrs)
        attr_str = f" attrs={attrs}" if attrs else ""
        print(f"  {flag:<25} {uid:<12}{attr_str:<30} -> {result}")
    print()


if __name__ == "__main__":
    demo()
