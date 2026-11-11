"""Read-only aggregation inside the existing bot; never imports bot configuration."""
from collections import Counter
import json
from pathlib import Path
class RegistryReader:
    def __init__(self, root=Path("/app/data")):
        self.root = root
    def read(self, name):
        with (self.root / name).open("rb") as source:
            data = source.read(2 * 1024 * 1024 + 1)
        if len(data) > 2 * 1024 * 1024:
            raise ValueError("bounded registry size exceeded")
        return json.loads(data)
    def collect(self):
        users = self.read("db_users.json")
        if not isinstance(users, dict):
            raise ValueError("invalid users schema")
        role_counts = Counter()
        chat_ids = set()
        user_count = unknown = 0
        for key, entry in users.items():
            if not isinstance(key, str) or not isinstance(entry, dict):
                raise ValueError("invalid user record")
            level = entry.get("level", 0)
            if type(level) is not int or not 0 <= level <= 100000:
                raise ValueError("invalid level")
            try:
                number = int(key)
            except ValueError:
                unknown += 1
                continue
            if number > 0:
                user_count += 1
                role_counts[level] += 1
            elif number < 0:
                chat_ids.add(key)
            else:
                unknown += 1
        managed = role_definitions = None
        types = Counter()
        chats_state = rules_state = "unavailable"
        try:
            chats = self.read("db_chats.json")["chat_tracking"]
            if not isinstance(chats, dict):
                raise ValueError("invalid chats schema")
            for key, entry in chats.items():
                if not isinstance(entry, dict) or not isinstance(key, str):
                    raise ValueError("invalid chat record")
                chat_ids.add(key)
                kind = entry.get("type", "unknown")
                types[kind if kind in ("private", "group", "supergroup", "channel") else "unknown"] += 1
            managed = len(chats)
            chats_state = "available"
        except (OSError, ValueError, KeyError, TypeError):
            pass
        try:
            roles = self.read("db_rules.json")["roles"]
            if not isinstance(roles, list) or any(not isinstance(role, dict) or type(role.get("level")) is not int or not 0 <= role["level"] <= 100000 for role in roles):
                raise ValueError("invalid role definitions")
            role_definitions = len({role["level"] for role in roles})
            rules_state = "available"
        except (OSError, ValueError, KeyError, TypeError):
            pass
        if len(role_counts) > 64:
            raise ValueError("role cardinality exceeded")
        return {"user_identities": user_count, "chat_identities": len(chat_ids),
            "managed_chats": managed, "role_definitions": role_definitions,
            "role_counts": [{"level": k, "count": v} for k, v in sorted(role_counts.items())],
            "unknown_entries": unknown, "chat_types": dict(types), "users_state": "available",
            "chats_state": chats_state, "rules_state": rules_state}

if __name__ == "__main__":
    try:
        print(json.dumps(RegistryReader().collect(), indent=2))
    except Exception:
        raise SystemExit(1)
