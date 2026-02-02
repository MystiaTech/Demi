# Security Fixes and Guidelines

## Overview
This document outlines critical security vulnerabilities that were identified and fixed in the Demi codebase on 2026-02-02.

## Fixed Vulnerabilities

### 1. ⚠️ CRITICAL: Hardcoded JWT Secrets (FIXED)
**Severity**: CRITICAL
**File**: `src/api/auth.py` (lines 28-42)

**Issue**: JWT secrets were hardcoded with default values, allowing authentication bypass if environment variables were not set.

**Fix**:
- Removed all default values for `JWT_SECRET_KEY` and `JWT_REFRESH_SECRET_KEY`
- Added validation to ensure both environment variables are set at startup
- Application will fail fast with clear error message if secrets are missing

**Action Required**:
```bash
# Generate secure random keys
python -c "import secrets; print('JWT_SECRET_KEY=' + secrets.token_urlsafe(32))"
python -c "import secrets; print('JWT_REFRESH_SECRET_KEY=' + secrets.token_urlsafe(32))"
```
Add these to your `.env` file.

---

### 2. ⚠️ CRITICAL: Overly Permissive CORS (FIXED)
**Severity**: CRITICAL
**File**: `src/api/__init__.py` (lines 21-28)

**Issue**:
- `allow_origins=["*"]` allowed ANY website to make requests to the API
- `allow_credentials=True` with wildcard origins enabled CSRF attacks
- `allow_methods=["*"]` and `allow_headers=["*"]` exposed all endpoints

**Fix**:
- Restricted CORS to specific allowed origins via `ALLOWED_ORIGINS` env var
- Changed `allow_credentials=False` (use bearer tokens instead)
- Limited methods to: GET, POST, DELETE only
- Limited headers to: Content-Type, Authorization only

**Action Required**:
Set `ALLOWED_ORIGINS` in `.env`:
```
ALLOWED_ORIGINS=https://yourdomain.com,https://app.yourdomain.com
```

---

### 3. ⚠️ HIGH: Subprocess String Injection (FIXED)
**Severity**: HIGH
**File**: `src/conductor/isolation.py` (lines 138-216)

**Issue**:
- JSON request data was interpolated directly into Python code strings
- Special characters (quotes, newlines) could break out of the string and execute arbitrary code
- Example vulnerable code: `request = json.loads('{request_json}')`

**Fix**:
- Changed to pass request JSON via subprocess stdin instead of string interpolation
- Subprocess reads from stdin: `sys.stdin.read()` and parses safely with `json.loads()`
- No user data is interpolated into code strings

**Impact**: Prevents code injection attacks via malicious JSON payloads.

---

### 4. ⚠️ HIGH: Unsafe Dynamic Module Import (FIXED)
**Severity**: HIGH
**File**: `src/conductor/isolation.py` (line 207)

**Issue**: Used `resource = __import__("resource")` which could be exploited if import paths are controllable.

**Fix**:
- Added `import resource` at module level (line 16)
- Removed dynamic `__import__()` call
- Now uses standard import, which is safe

---

### 5. 🟡 MEDIUM: Sensitive Data in Logs (FIXED)
**Severity**: MEDIUM
**File**: `src/api/auth.py` (lines 182, 266, 323, 401)

**Issue**: Logs contained user emails, full session IDs, and user IDs, which could leak sensitive info if logs are exposed.

**Fixes**:
- Removed full email logging: `f"Session created for user {user_id}"`
- Truncated session IDs: `session_id[-8:]` (logs last 8 chars only)
- Removed email from refresh logging
- Truncated user IDs in session revoke logging

---

### 6. 🟡 MEDIUM: Subprocess Error Leakage (FIXED)
**Severity**: MEDIUM
**File**: `src/conductor/isolation.py` (lines 243-246)

**Issue**: Full stderr output was logged, which could leak file paths, system details, or sensitive error messages.

**Fix**:
- Sanitized stderr output: only log first 100 characters of first line
- Prevents leaking of absolute paths, system details, and full stack traces

---

## Remaining High-Priority Recommendations

### Rate Limiting (Not yet implemented)
**Impact**: Prevents brute force attacks on login and API endpoints

Implement using:
```python
from slowapi import Limiter
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
```

Add to auth endpoints:
```python
@limiter.limit("5/minute")
@router.post("/login")
```

---

### Input Validation
Add Pydantic validators to all models:

**File**: `src/api/models.py`
```python
from pydantic import BaseModel, Field, validator

class LoginRequest(BaseModel):
    email: str = Field(..., min_length=5, max_length=255)
    password: str = Field(..., min_length=8, max_length=256)
    device_name: str = Field(..., max_length=100)

    @validator('email')
    def validate_email(cls, v):
        if not ('@' in v and '.' in v.split('@')[-1]):
            raise ValueError('Invalid email format')
        return v.lower()
```

---

### Dependency Pinning
**File**: `requirements.txt`

Change from flexible versions to pinned versions:
```
# BEFORE (vulnerable to auto-updates)
fastapi>=0.115.0
discord.py>=2.6.0

# AFTER (locked versions)
fastapi==0.115.5
discord.py==2.6.1
```

---

### Device Fingerprint Validation
Add device fingerprint validation to prevent unauthorized session use:

```python
# In auth.py
def verify_session_device(current_user: dict, request: Request):
    """Verify session is from same device"""
    current_fingerprint = request.headers.get("X-Device-Fingerprint")
    stored_fingerprint = get_session_fingerprint(current_user["session_id"])

    if current_fingerprint != stored_fingerprint:
        raise HTTPException(status_code=401, detail="Device mismatch")
```

---

### HTTPS Enforcement
Add to FastAPI startup:
```python
@app.middleware("http")
async def https_redirect(request, call_next):
    if request.url.scheme != "https" and ENVIRONMENT == "production":
        return RedirectResponse(url=request.url.replace(scheme="https"), status_code=301)
    return await call_next(request)
```

---

## Configuration Best Practices

### .env File Setup
1. Never commit `.env` to version control (already in .gitignore)
2. Generate strong keys for production:
   ```bash
   python -c "import secrets; print(secrets.token_urlsafe(32))"
   ```
3. Rotate JWT secrets periodically in production
4. Use different secrets for different environments (dev, staging, prod)

### Environment-Specific Configs
```bash
# Development
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:5173

# Production
ALLOWED_ORIGINS=https://app.example.com
JWT_SECRET_KEY=<secure-random-key>
```

### API Host Binding
```bash
# Development (localhost only)
ANDROID_API_HOST=127.0.0.1

# Production (behind reverse proxy/Docker)
ANDROID_API_HOST=0.0.0.0  # Only if behind trusted network boundary
```

---

## Testing Security Fixes

### 1. Test Missing JWT Secret
```bash
# Clear env vars and start server
unset JWT_SECRET_KEY JWT_REFRESH_SECRET_KEY
python -m src.api.main  # Should fail with ValueError
```

### 2. Test CORS Restrictions
```bash
# Request from blocked origin should fail
curl -H "Origin: https://evil.com" \
     -H "Content-Type: application/json" \
     https://your-api/api/v1/login
# Should return 400 or be blocked
```

### 3. Test Subprocess Code Injection Protection
Try login with malicious JSON in device_fingerprint:
```bash
curl -X POST https://your-api/api/v1/login \
  -H "Content-Type: application/json" \
  -d '{
    "email":"user@example.com",
    "password":"password",
    "device_name":"iPhone",
    "device_fingerprint":"\u0027; print(\"pwned\"); #"
  }'
# Should not execute injected code
```

---

## Security Audit Checklist

- [x] Remove hardcoded secrets
- [x] Restrict CORS origins
- [x] Fix subprocess code injection
- [x] Remove unsafe dynamic imports
- [x] Sanitize logs
- [ ] Implement rate limiting
- [ ] Add input validation to all endpoints
- [ ] Pin dependency versions
- [ ] Add device fingerprint validation
- [ ] Enforce HTTPS in production
- [ ] Implement rate limiting on password reset/registration
- [ ] Add account lockout monitoring
- [ ] Regular security scanning (OWASP, dependency audits)

---

## Security Contact
If you find a security vulnerability, please report it privately rather than creating a public issue. Contact: [security contact info]

---

## References
- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [JWT Best Practices](https://tools.ietf.org/html/rfc8725)
- [CORS Security](https://developer.mozilla.org/en-US/docs/Web/HTTP/CORS)
- [Subprocess Security](https://docs.python.org/3/library/subprocess.html#security-considerations)
