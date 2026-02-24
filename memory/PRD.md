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

### Completed (Feb 20, 2025)
- [x] User authentication (email/password + Google OAuth)
- [x] Business registration onboarding flow
- [x] Main app navigation and tabs
- [x] Home screen with feature links
- [x] Subscription screen with Stripe integration (test prices)
- [x] Backend API structure with FastAPI
- [x] MongoDB integration
- [x] Skeleton services for enterprise features
- [x] **Android Build Configuration Fixed** - All AAPT errors resolved

### In Progress
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

## Google Sign-In Fix (Feb 20, 2025)

**Issue**: Google Sign-In was returning `{"detail":"Not Found"}` after authentication.

**Root Cause**: OAuth callback URL `/auth-callback` was routing to frontend instead of backend.

**Fixes Applied**:
1. Added `/api/auth-callback` endpoint in backend for OAuth redirect handling
2. Updated login.tsx to use `/api/auth-callback` as redirect URL
3. Backend returns HTML page that redirects to mobile app via deep link (`tomi://`)
4. Fixed token response - backend now returns both `token` and `session_token`
5. Added Android intent filters for `tomi://` scheme deep linking

---

## Android Build Fixes Applied (Feb 20, 2025)

### Issues Fixed:
1. **AAPT Icon Compilation Error**
   - Created minimal PNG icons with pure RGB encoding (no alpha channel)
   - File sizes reduced to prevent AAPT processing issues
   - Icons: icon.png (4.5KB), adaptive-icon.png (4.5KB), splash-icon.png (430B), favicon.png (112B)

2. **@types/react Dependency**
   - Fixed version mismatch: now using `~19.1.10` compatible with Expo SDK 54

3. **Missing Configuration Files**
   - Created `eas.json` for EAS Build configuration
   - Configured for both preview (APK) and production (AAB) builds

4. **App Configuration (app.json)**
   - Added Android package: `com.tomi.ownermind`
   - Added iOS bundleIdentifier: `com.tomi.ownermind`
   - Added versionCode for Play Store
   - Configured permissions: INTERNET, ACCESS_NETWORK_STATE
   - Updated app name: "TOMI - The Owner Mind"

5. **Environment Configuration**
   - Fixed `EXPO_USE_FAST_RESOLVER="1"` quoting in .env

### Expo Doctor Results:
- **17/17 checks passed** ✅

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
│   ├── assets/images/      # App icons (regenerated)
│   ├── app.json            # Expo config (updated)
│   ├── eas.json            # EAS build config (created)
│   └── package.json        # Dependencies (fixed)
└── memory/
    └── PRD.md              # This file
```

---

## Play Store Deployment Checklist

### Ready:
- [x] App name: "TOMI - The Owner Mind"
- [x] Package name: com.tomi.ownermind
- [x] Version: 1.0.0, versionCode: 1
- [x] Icons: All valid PNG format
- [x] EAS configuration: Production builds as AAB
- [x] Dependencies: All compatible with Expo SDK 54

### Required Before Publishing:
- [ ] Play Store developer account
- [ ] Play Store listing assets (screenshots, descriptions)
- [ ] Privacy policy URL
- [ ] Service Account Key for automated submission (play-store-key.json)

---

## Credentials (Secure Storage Required)
- Google Search API Key: Provided by user, needs to be stored in backend/.env
