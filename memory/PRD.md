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
- **AI**: emergentintegrations library (Emergent LLM Key)
- **Payments**: Stripe
- **Deployment**: EAS (Expo Application Services)

---

## Implementation Status

### Completed (Dec 2025)
- [x] User authentication (email/password + Google OAuth)
- [x] Business registration onboarding flow
- [x] Main app navigation and tabs
- [x] Home screen with feature links
- [x] Subscription screen with Stripe integration (test prices)
- [x] Backend API structure with FastAPI
- [x] MongoDB integration
- [x] Skeleton services for enterprise features

### In Progress
- [ ] **P0 - Android Build Fix** - AAPT icon error resolved, needs deployment verification
- [ ] **P1 - Intelligent Chatbot** - UI exists, backend logic needs implementation

### Upcoming Tasks
- Security & RBAC implementation
- Data Export functionality
- Revert subscription prices from ₹1 to original

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
│   ├── server.py           # Main FastAPI app
│   ├── models.py           # Pydantic models
│   ├── llm_service.py      # LLM integration
│   ├── chatbot_service.py  # Chatbot logic (stub)
│   ├── security_service.py # RBAC (stub)
│   ├── data_export_service.py # Export (stub)
│   └── enterprise_service.py  # Enterprise modules (stub)
├── frontend/
│   ├── app/
│   │   ├── (auth)/         # Auth screens
│   │   ├── (main)/         # Main feature screens
│   │   ├── (onboarding)/   # Onboarding flow
│   │   └── (tabs)/         # Tab navigation
│   └── assets/images/      # App icons
└── memory/
    └── PRD.md              # This file
```

---

## Key Fixes Applied (Feb 20, 2025)

### Android Build Error Resolution
**Issue**: `EAS_BUILD_UNKNOWN_GRADLE_ERROR` - AAPT: error: file failed to compile for `assets_images_icon.png`

**Root Causes Fixed**:
1. Regenerated clean AAPT-compatible PNG icons (RGBA mode, proper sizes)
2. Fixed `.env` - Quoted `EXPO_USE_FAST_RESOLVER="1"`
3. Clean reinstalled dependencies (removed stale node_modules/yarn.lock)
4. All 17 expo doctor checks now pass

**Files Modified**:
- `/app/frontend/assets/images/icon.png` - Regenerated 1024x1024 RGBA
- `/app/frontend/assets/images/adaptive-icon.png` - Regenerated 1024x1024 RGBA
- `/app/frontend/assets/images/splash-icon.png` - Regenerated 200x200 RGBA
- `/app/frontend/assets/images/favicon.png` - Regenerated 48x48 RGBA
- `/app/frontend/.env` - Fixed EXPO_USE_FAST_RESOLVER quoting
- `/app/frontend/yarn.lock` - Fresh regeneration

---

## Credentials (Secure Storage Required)
- Google Search API Key: Provided by user, needs to be stored in backend/.env
