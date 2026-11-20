# Hamroh

Post-discharge patient monitoring platform. A doctor and a patient stay connected after
discharge: daily check-ins, risk alerts, shared medication/diagnosis records, one-time
doctor consultations, voice-call reminders, and Web Push notifications.

Full architecture rules: [`CLAUDE.md`](CLAUDE.md). Full spec: [`PLAN.md`](PLAN.md) (Uzbek).
Phase 10+ (auth, profiles, consultations) spec: [`PHASE10_EXECUTION_PROMPT.md`](PHASE10_EXECUTION_PROMPT.md) (Uzbek).

**Stack:** Flask + Jinja2 + SQLite + Tailwind (CDN) + vanilla JS, 3s polling, no build step.

---

## 1. Quick start

```bash
# 1. Unzip and enter the project
unzip hamroh-backend-full.zip -d hamroh
cd hamroh

# 2. Virtual environment
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

# 3. Dependencies
pip install -r requirements.txt

# 4. Configure environment
cp .env.example .env
# edit .env — see section 3 below for what's required vs optional

# 5. Run
python app.py
```

Open `http://localhost:5000`. The database (`hamroh.db`) and migrations run automatically
on first start — no manual setup needed. Demo data (3 seeded patients + 1 doctor) is ready
immediately at `/`.

Run the test suite before you rely on anything:

```bash
pytest -q
```

All 81 tests should pass out of the box — none of them need real credentials (every
external integration is mocked in tests).

---

## 2. Two parallel entry points

The app has **two separate ways in**, and they never interfere with each other:

- **Legacy demo** (`/`, `/patient/<id>/chat`, `/doctor/<id>/dashboard`, …) — no login,
  click a seeded patient/doctor card. This is the original hackathon demo and stays fully
  intact.
- **Real accounts** (`/auth/login`) — Google or Telegram login, role selection, and
  everything built in Phase 10 (doctor profiles, patient self-signup, shared
  medication/diagnosis records, consultations). New patients/doctors created this way get
  a real `user_id`; the legacy demo rows don't and never will.

You can use either without setting up any credentials — the legacy demo needs nothing at
all, and the login screen simply shows Google/Telegram as "not configured" until you fill
in their keys (see below).

---

## 3. Environment variables (`.env`)

Nothing is required to run the legacy demo. Everything below is **optional** and only
needed for the feature it enables — the app degrades gracefully (clear "not configured"
messages) when a section is left blank.

| Section | Needed for | Where to get it |
|---|---|---|
| `ANTHROPIC_API_KEY` | AI-based risk triage (`llm_analyzer`) | [console.anthropic.com](https://console.anthropic.com). Leave blank + `FEATURE_LLM_ANALYZER=0` and the rule-based analyzer still fully drives the demo. |
| `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` / `GOOGLE_REDIRECT_URI` | "Continue with Google" login | Google Cloud Console → APIs & Services → Credentials → OAuth client ID (type: Web application). Redirect URI must be exactly `https://your-domain/auth/google/callback`. |
| `TELEGRAM_BOT_TOKEN` / `TELEGRAM_BOT_USERNAME` | "Continue with Telegram" login | [@BotFather](https://t.me/BotFather) → `/newbot`, then `/setdomain` pointing at your host (Telegram Login Widget requires this). |
| `VAPID_PUBLIC_KEY` / `VAPID_PRIVATE_KEY` | Real Web Push notifications | Self-generated, no account needed: `python scripts/generate_vapid_keys.py` and paste the two output lines in. |
| `SMARTCALL_API_KEY` / `SMARTCALL_GROUP_ID` | Automated voice-call reminders | [smartcall.uz](https://smartcall.uz) account; `groupID` comes from its Statistika page. **Keep `FEATURE_CALL_NOTIFIER=0` until this is a real account you control** — the seeded demo patients have made-up phone numbers, and turning this on would dial whoever actually owns them. |
| `ADMIN_EMAILS` | Doctor verification panel (`/admin/doctors`) | Comma-separated list of emails. Whichever Google account logs in with a matching email becomes admin automatically. Telegram accounts can't become admin (no email). |
| `UPLOAD_DIR` / `MAX_UPLOAD_SIZE_MB` | Doctor documents & diagnosis file uploads | Defaults are fine (`uploads/`, 10 MB); change only if you need a different disk location or limit. |

Everything else in `.env.example` (Flask config, feature flags) has a sane default and
rarely needs touching.

---

## 4. Feature flags

Set any of these to `0`/`1` in `.env` (as `FEATURE_<NAME>`, uppercase) to turn a piece of
the app off without touching code — useful for demos where you want to hide something
half-configured.

| Flag | Default | What it gates |
|---|---|---|
| `llm_analyzer` | on | Claude-based risk triage (falls back to rules if off or unconfigured) |
| `doctor_reply` | on | Doctor → patient messaging in the legacy chat |
| `trend_chart` | **off** | Risk-score trend graph (doctor + patient views) |
| `sms_notifier` | off | Reserved, unimplemented |
| `multi_question` | off | Multiple check-in questions per day |
| `call_notifier` | **off** | Auto-dial via SmartCall on a red alert + manual "call now" button |
| `push_notifications` | on | Web Push channel (needs VAPID keys to actually deliver) |
| `dmed_auth` | off | Third login provider — intentionally an empty stub |
| `medication_reminders` | on | Background scheduler pushing "time for your dose" |
| `motivation_messages` | on | Congratulatory push when a patient's trend genuinely improves |
| `consultation` | on | One-time "ask any available doctor" feature |

---

## 5. Project structure

```
app.py                    # application factory — wires everything below together
config.py                 # env vars + FEATURES flags
core/                     # infrastructure: db.py, auth.py, events.py, errors.py, files.py
migrations/                # numbered .sql files, applied automatically on startup
repos/                    # SQL only — one file per table/concern
services/                 # business logic
analyzers/                # risk-triage pipeline (rule-based + LLM)
identity_providers/       # Google / Telegram / dmed login — one file per provider
notifiers/                 # push / call / in-app channels
hooks/                    # event reactions (alerts, push, reminders, motivation, consultations)
routes/                   # HTTP only — pages (HTML) and *_api (JSON) blueprints
templates/                # Jinja2
static/js/                # vanilla JS, one file per page
tests/                    # pytest — 81 tests, all self-contained (mocked network)
scripts/generate_vapid_keys.py
```

Adding something new almost always means **adding a file**, not editing an existing one —
see `CLAUDE.md` and `PLAN.md` §12 for the extension points (`analyzers/`, `hooks/`,
`notifiers/`, `identity_providers/`) and why they're shaped this way.

---

## 6. What's in Phase 10 (A–G)

| Module | Entry points |
|---|---|
| A — Auth | `/auth/login`, `/auth/role`, `/auth/app` |
| B — Doctor profile + verification | `/doctor/profile`, `/admin/doctors` |
| C — Doctor adds a patient (one-time code) | `/doctor/patients`, `/doctor/patients/add` |
| D — Patient self-signup + doctor connect code | `/patient/profile` |
| E — Shared medication/diagnosis records | `/care/patients/<id>` |
| F — Patient-visible trend + motivation | part of `/care/patients/<id>` |
| G — One-time doctor consultation | `/patient/consultations`, `/doctor/consultations` |

Known scope boundary (see `PLAN.md` §12.4): patients created through C/D use a generic
`persona_key` with no scripted daily questions — they use the new medication/diagnosis
system (E) instead of the original scripted check-in bot. Only the three original seeded
demo patients (Bobur/Sardor/Nodira) go through that scripted flow.

---

## 7. Troubleshooting

- **"sozlanmagan" (not configured) on the login page** — expected until you fill in the
  relevant `.env` section (§3). The app is designed to degrade gracefully, not crash.
- **Port already in use** — change `PORT` in `.env`.
- **Reset the demo data** — `POST /api/v1/demo/reset`, or just delete `hamroh.db` and
  restart (migrations reseed it).
- **Uploaded files disappear after a fresh clone** — `uploads/` is gitignored on purpose
  (user-generated content); it's created automatically on first upload.
