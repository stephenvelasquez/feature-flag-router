# Feature Flag Router

Ship with confidence. A lightweight feature flag system with user targeting, percentage rollouts, and kill switches.

## Why this exists

Feature flags are the difference between "deploying" and "releasing." You deploy code to production. You release features to users. They shouldn't be the same event.

Every team I've worked with either (a) uses a $50K/year vendor or (b) has `if user_id in [123, 456]` scattered through the codebase. This is a middle ground: a proper flag system you can understand in an afternoon.

## Quick start

```python
from flag_router import FlagRouter

router = FlagRouter()

# Define flags
router.add_flag("new_checkout", enabled=True, rollout_percent=25)
router.add_flag("dark_mode", enabled=True, target_users=["user_42", "user_88"])
router.add_flag("beta_search", enabled=False)  # kill switch — off for everyone

# Evaluate
if router.is_enabled("new_checkout", user_id="user_123"):
    show_new_checkout()
else:
    show_old_checkout()
```

## Features

- **Boolean flags** — Simple on/off for features
- **Percentage rollout** — Roll out to N% of users deterministically
- **User targeting** — Enable for specific user IDs
- **Attribute targeting** — Enable based on user attributes (plan, country, etc.)
- **Kill switch** — Instantly disable any flag
- **Flag dependencies** — Flag B only active if Flag A is active
- **Audit log** — Who changed what flag, when
- **JSON config** — Load flags from a config file or environment

## Targeting rules

```python
# Percentage rollout — deterministic by user_id hash
router.add_flag("redesign", enabled=True, rollout_percent=10)

# User targeting — specific users
router.add_flag("beta", enabled=True, target_users=["user_42"])

# Attribute targeting — users matching rules
router.add_flag("enterprise_feature", enabled=True, target_rules={
    "plan": ["enterprise", "business"],
    "country": ["US", "CA"],
})

# Dependency — only if parent flag is on
router.add_flag("checkout_v3", enabled=True, depends_on="checkout_v2")
```

## Deterministic rollouts

Percentage rollouts are deterministic: the same user always gets the same result. No randomness, no cookies, no state.

```python
# Uses consistent hashing: hash(flag_name + user_id) % 100 < rollout_percent
# user_123 always sees the same variant for "new_checkout"
router.is_enabled("new_checkout", user_id="user_123")  # Always True or always False
```

## Config file

```json
{
  "flags": {
    "new_checkout": {
      "enabled": true,
      "rollout_percent": 25,
      "description": "Redesigned checkout flow — Q1 2026"
    },
    "dark_mode": {
      "enabled": true,
      "target_users": ["user_42", "user_88"],
      "description": "Dark mode beta for internal testers"
    },
    "legacy_api": {
      "enabled": false,
      "description": "Kill switch for deprecated v1 API"
    }
  }
}
```

```python
router = FlagRouter.from_config("flags.json")
```

## Project structure

```
feature-flag-router/
├── flag_router.py        # Core library
├── flags.json            # Example config
├── tests/
│   └── test_flags.py
├── requirements.txt
└── README.md
```

## License

MIT
