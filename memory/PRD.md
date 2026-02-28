# TOMI - The Owner Mind
## Product Requirements Document

### Original Problem Statement
Build a complete mobile-first application named "TOMI - The Owner Mind," a decision-learning business operating system.

### Core Features
1. **Mandatory Onboarding**: Owner account creation and business registration
2. **Optional Knowledge Import**: For documents like PDFs, CSVs, images
3. **Main App Sections**: Home Feed, Conversations, Decisions, Insights, Control Center
4. **AI & Automation**: System learns from owner behavior, requires explicit approval
5. **Stripe Subscription**: Prices temporarily set to ₹1 for testing

### Expansion Features (Planned)
- **Intelligent Knowledge Chatbot**: Business data + internet search
- **Enterprise Modules**: Accounting, Payroll, Vendor management, Multi-branch
- **Security & Data**: RBAC, Audit logs, Data export, Local backup
- **Website Builder**: Create/deploy business site from app
- **Advertising System**: Create/publish campaigns

### Technology Stack
- **Frontend**: Expo (React Native) with Expo Router
- **Backend**: FastAPI (Python)
- **Database**: MongoDB
- **AI**: emergentintegrations library (Emergent LLM Key) — OpenAI gpt-5.1
- **Web Search**: DuckDuckGo HTML lite (no API key needed)
- **Payments**: Stripe
- **Deployment**: EAS (Expo Application Services)

---

## Implementation Status

### Completed (Feb 20, 2025)
- [x] User authentication (email/password + Google OAuth)
- [x] Business registration onboarding flow
- [x] Main app navigation and tabs
- [x] Home screen with feature links
- [x] Subscription screen with Stripe integration (production prices)
- [x] Backend API structure with FastAPI
- [x] MongoDB integration
- [x] Skeleton services for enterprise features

### Completed (Feb 24, 2026)
- [x] **P0: Android Build — Static Icons Removed** — Deleted all bundled icon/adaptive-icon/favicon PNGs, removed `icon`, `adaptiveIcon`, `favicon` from app.json, replaced `require(icon.png)` in index.tsx with styled text mark, cleared all caches. Deployment system now handles logo injection.
- [x] **P1: Intelligent Knowledge Chatbot** — Full hybrid search implementation
  - Real-time internal business data search (documents, conversations, customers, finances, decisions)
  - Live web search via DuckDuckGo HTML lite endpoint
  - Source attribution in responses ([Business Data], [Web: url])
  - Rate limiting (20 requests/minute per user)
  - Chat history persistence in MongoDB
  - Frontend UI with web search toggle, source tags, clickable web source links
  - Tested: 13/13 backend tests passed, frontend verified
- [x] **Auth Bug Fixes (3 critical issues, Feb 28):**
  - Login: Google-only users now get `400` with "use Google Sign-In" message instead of 500 crash
  - Registration: Google-only users can register to merge accounts (sets password on existing account)
  - Google OAuth: Deep link uses `?session_id=` query param for Android compatibility

### In Progress
- [ ] **Google Sign-In** — Full-stack deep linking fix applied; awaiting user verification on mobile after rebuild

### Upcoming Tasks (Priority Order)
1. Security & RBAC implementation
2. Data Export functionality

### Future/Backlog
- Website Builder & Deployment module
- Ads Publishing system
- Full Enterprise modules (Accounting, Payroll, Procurement)
- Local Safety Backup
- Replace mocked communication channels

---

## Architecture

```
/app
├── backend/
│   ├── server.py              # Main FastAPI app (all endpoints)
│   ├── llm_service.py         # Multi-provider LLM service
│   ├── chatbot_service.py     # Hybrid search chatbot (REAL web search)
│   ├── security_service.py    # RBAC & audit (stub)
│   ├── data_export_service.py # Export & backup (stub)
│   ├── enterprise_service.py  # Enterprise modules (stub)
│   ├── document_processor.py  # Document text extraction
│   ├── channels.py            # Communication channel simulator
│   ├── subscription_service.py# Stripe subscription
│   └── requirements.txt
├── frontend/
│   ├── app/
│   │   ├── (auth)/            # Auth screens (login, signup)
│   │   ├── (tabs)/            # Tab navigation
│   │   ├── chatbot.tsx        # Chatbot UI (COMPLETE)
│   │   ├── subscription.tsx   # Subscription screen
│   │   └── auth-callback.tsx  # Google OAuth callback
│   ├── assets/images/         # App icons (4 clean PNGs)
│   ├── app.json               # Expo config (FIXED)
│   ├── eas.json               # EAS build config
│   └── package.json
└── memory/
    └── PRD.md
```

---

## Key API Endpoints

| Endpoint | Method | Description |
|---|---|---|
| `/api/health` | GET | Health check |
| `/api/auth/register` | POST | Register user |
| `/api/auth/login` | POST | Login user |
| `/api/auth/google` | POST | Google OAuth |
| `/api/auth-callback` | GET | OAuth redirect handler |
| `/api/business/setup` | POST | Create business |
| `/api/chatbot/ask` | POST | Ask chatbot (hybrid search) |
| `/api/chatbot/history` | GET | Get chat history |
| `/api/conversations` | GET/POST | Manage conversations |
| `/api/ai/suggest-reply` | POST | AI reply suggestion |
| `/api/documents/upload` | POST | Upload documents |
| `/api/subscription/plans` | GET | Get subscription plans |

---

## Test Credentials
- Email: test@tomi.com
- Password: test123
- Business: Test Corp (Technology / Software Development)
