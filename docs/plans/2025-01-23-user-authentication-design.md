# User Authentication - Design Document

## Overview

Add user authentication to the Content Curator app with email/password login, open registration with email verification, and per-user data isolation.

## Goals

- Secure the app with login requirement
- Support multiple users with separate reading lists/interests
- Open registration with email verification
- Self-hosted friendly (no OAuth dependency)

## Architecture

### Database Schema

```sql
-- New users table
CREATE TABLE users (
    id INTEGER PRIMARY KEY,
    email TEXT UNIQUE NOT NULL,
    username TEXT NOT NULL,
    password_hash TEXT NOT NULL,
    verified BOOLEAN DEFAULT FALSE,
    verification_token TEXT,
    token_expires_at TIMESTAMP,
    is_admin BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Add user_id to existing tables
ALTER TABLE interests ADD COLUMN user_id INTEGER REFERENCES users(id);
ALTER TABLE saved_items ADD COLUMN user_id INTEGER REFERENCES users(id);
ALTER TABLE content ADD COLUMN user_id INTEGER REFERENCES users(id);
ALTER TABLE user_actions ADD COLUMN user_id INTEGER REFERENCES users(id);
```

### Authentication Flow

```
┌─────────────────────────────────────────────────┐
│                   App Entry                      │
│                                                  │
│  ┌─────────────┐     ┌─────────────────────┐   │
│  │ Not Logged  │────▶│ Login / Sign Up Page │   │
│  │    In       │     └─────────────────────┘   │
│  └─────────────┘              │                 │
│                               ▼                 │
│                    ┌─────────────────────┐      │
│                    │  Verify Credentials  │      │
│                    └─────────────────────┘      │
│                               │                 │
│                               ▼                 │
│  ┌─────────────┐     ┌─────────────────────┐   │
│  │  Logged In  │◀────│  Set Session State   │   │
│  └─────────────┘     └─────────────────────┘   │
│         │                                       │
│         ▼                                       │
│  ┌─────────────────────────────────────────┐   │
│  │  All queries filtered by user_id         │   │
│  │  - interests WHERE user_id = current     │   │
│  │  - saved_items WHERE user_id = current   │   │
│  └─────────────────────────────────────────┘   │
└─────────────────────────────────────────────────┘
```

### Sign Up Flow

1. User enters email + password (min 8 chars)
2. App validates email format, checks not already registered
3. Creates user with `verified=False`
4. Generates random 32-char token, stores with 24hr expiry
5. Sends verification email with link
6. User clicks link → token validated → `verified=True`
7. User can now log in

### Email Verification

**Email Template:**
```
Subject: Verify your Content Curator account

Welcome to Content Curator!

Click the link below to verify your account:
{BASE_URL}/?verify={TOKEN}

This link expires in 24 hours.

If you didn't create this account, ignore this email.
```

**SMTP Configuration (environment variables):**
```
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=app-password
SMTP_FROM=noreply@yourdomain.com
```

**Fallback:** Admin can manually verify users if SMTP not configured.

### Password Security

- Hashed with bcrypt (12 rounds)
- Never stored in plain text
- Password reset via email token (same flow as verification)

### Session Management

- Use `st.session_state['user']` for current session
- Session persists until browser closed or logout
- Optional: "Remember me" with secure signed cookie (30 days)

## UI Components

### Login Page
```
┌────────────────────────────────────────┐
│         Content Curator                │
│                                        │
│  [Login]  [Sign Up]                    │
│  ─────────────────                     │
│                                        │
│  Email:    [____________________]      │
│  Password: [____________________]      │
│                                        │
│  [ ] Remember me                       │
│                                        │
│  [Log In]                              │
│                                        │
│  Forgot password?                      │
└────────────────────────────────────────┘
```

### Sign Up Page
```
┌────────────────────────────────────────┐
│         Create Account                 │
│                                        │
│  Username: [____________________]      │
│  Email:    [____________________]      │
│  Password: [____________________]      │
│  Confirm:  [____________________]      │
│                                        │
│  [Create Account]                      │
│                                        │
│  Already have an account? Log in       │
└────────────────────────────────────────┘
```

### Logged In State
```
┌────────────────────────────────────────┐
│  Sidebar:                              │
│  ┌──────────────────────────────────┐  │
│  │ 👤 andrew@email.com              │  │
│  │ [Logout]                         │  │
│  │                                  │  │
│  │ Navigation:                      │  │
│  │ • Search                         │  │
│  │ • My Feed                        │  │
│  │ • Interests                      │  │
│  │ • Reading List                   │  │
│  │ • Settings                       │  │
│  └──────────────────────────────────┘  │
└────────────────────────────────────────┘
```

### Admin Panel (in Settings)
```
┌────────────────────────────────────────┐
│  Admin: User Management                │
│                                        │
│  Users (5)                             │
│  ┌──────────────────────────────────┐  │
│  │ andrew@email.com  ✓ Admin        │  │
│  │ user2@email.com   ✓ Verified     │  │
│  │ user3@email.com   ⏳ Pending     │  │
│  │   [Verify] [Delete]              │  │
│  └──────────────────────────────────┘  │
└────────────────────────────────────────┘
```

## Data Migration

On first run after update:
1. Check if `users` table exists
2. If not, create it
3. Create admin account (prompt for email/password on first run)
4. Migrate existing data to admin user_id
5. Add user_id columns to existing tables

## Configuration

New environment variables:
```
# Required for email verification
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=app-password

# Optional
ADMIN_EMAIL=admin@yourdomain.com
BASE_URL=https://your-app-url.com
```

## File Changes

### New Files
- `auth.py` - Authentication logic (login, signup, verify, password reset)
- `email_service.py` - SMTP email sending
- `pages/0_Login.py` - Login/signup page (loads first)

### Modified Files
- `database.py` - Add users table, add user_id to queries
- `app.py` - Add auth check, redirect to login if not authenticated
- `pages/*.py` - Filter data by current user_id
- `pages/5_Settings.py` - Add admin panel section

## Dependencies

Add to `requirements.txt`:
```
bcrypt>=4.0.0
```

## Security Considerations

- Passwords hashed with bcrypt
- Verification tokens are random, expire in 24 hours
- Session stored server-side (not in cookies)
- SQL injection prevented by parameterized queries
- Rate limiting on login attempts (future enhancement)
