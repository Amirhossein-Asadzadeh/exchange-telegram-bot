# Exchange Telegram Bot (PnL Watcher)

Telegram bot for monitoring futures positions and notifying **Profit ↔ Loss crossings** with cooldown protection.

This project is designed as a **production-grade monitoring service**, with clean separation of concerns, deterministic alerting logic, and full test coverage.

---

## Features

- Real-time futures position monitoring
- Profit → Loss and Loss → Profit crossing alerts
- Configurable PnL sensitivity (threshold)
- Cooldown mechanism to prevent alert spam
- Persistent state storage (JSON-based)
- Exchange-agnostic watcher logic
- Fully test-covered core logic
- CI with GitHub Actions (pytest)

---

## Architecture

Telegram Bot
↓
Watcher (pure business logic)
↓
Provider (SDK abstraction layer)
↓
Exchange API Client (Bitunix adapter)

yaml
Copy code

### Design principles

- **Watcher is exchange-agnostic**
- **Provider layer is mockable and replaceable**
- **Business logic has no Telegram dependency**
- Side effects (Telegram, IO, SDK) are isolated

This makes the core logic:
- Easy to test
- Safe to extend
- Suitable for backend / DevOps environments

---

## Alert Logic (How Notifications Work)

An alert is triggered **only when all conditions are met**:

- PnL crosses between **negative ↔ positive**
- Absolute PnL change exceeds the configured threshold
- Cooldown window has elapsed since the last alert

### Examples

| PnL Change        | Alert |
|------------------|-------|
| `-300 → -400`     | ❌ No |
| `+10 → -10`       | ✅ Yes |
| `-5 → +5`         | ✅ Yes |
| Repeated crossing during cooldown | ❌ No |

---

## Configuration

Create a `.env` file (see `.env.example`):

```env
BITUNIX_API_KEY=your_key
BITUNIX_API_SECRET=your_secret

ALLOWED_CHAT_IDS=123456789
ADMIN_CHAT_ID=123456789

PNL_THRESHOLD=0.5
COOLDOWN_SECONDS=600
POLL_INTERVAL_SECONDS=15
Running Locally
bash
Copy code
pip install -e .
python -m posbot.main
Commands (Telegram)
/positions – Show open positions

/status – Show current watcher state

/threshold <value> – Set PnL sensitivity

/cooldown <seconds> – Set alert cooldown

/watch on|off – Enable / disable monitoring

Tests
All critical logic is covered with unit tests.

bash
Copy code
python -m pytest -q
Test coverage includes:

PnL crossing detection

No-alert scenarios

Cooldown enforcement

Deterministic watcher behavior

CI
GitHub Actions runs tests automatically on each push:

Python

Pytest

Fast feedback loop

Why This Project Matters
This repository demonstrates:

Production-safe monitoring logic

Clean architecture and separation of concerns

Test-driven development

Practical alerting behavior used in real exchanges

It is suitable as a foundation for:

Exchange backend monitoring

Risk management tools

Trading infrastructure services

License
MIT

yaml
Copy code

---
