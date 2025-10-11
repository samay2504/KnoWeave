# CRITICAL FIX: Config Attribute Names

**Issue:** `AttributeError: 'ServerConfig' object has no attribute 'COOKIE_SAMESITE'`

**Root Cause:** 
- `ServerConfig` class defines lowercase attributes (`cookie_secure`, `cookie_samesite`)
- Some have uppercase `@property` accessors (JWT_SECRET, COOKIE_SECURE) but NOT all
- Missing: `COOKIE_SAMESITE` property

**Files Fixed:**
- `server/auth/google_oauth.py`

**Changes Made:**

### Before (BROKEN):
```python
cookie_secure = False if is_dev else config.COOKIE_SECURE  # ❌ Missing property
cookie_samesite = "lax" if is_dev else config.COOKIE_SAMESITE.lower()  # ❌ Missing property
```

### After (FIXED):
```python
cookie_secure = False if is_dev else config.cookie_secure  # ✅ Use direct attribute
cookie_samesite = "lax" if is_dev else config.cookie_samesite.lower()  # ✅ Use direct attribute
```

**Server Config Properties Available:**
- ✅ `config.JWT_SECRET` (property exists)
- ✅ `config.JWT_ALGORITHM` (property exists)  
- ✅ `config.JWT_EXPIRE_SECONDS` (property exists)
- ✅ `config.COOKIE_SECURE` (property exists)
- ✅ `config.COOKIE_DOMAIN` (property exists)
- ❌ `config.COOKIE_SAMESITE` (**property DOES NOT exist**)

**Solution:** Use lowercase attributes directly:
- `config.cookie_secure` 
- `config.cookie_samesite`
- `config.cookie_domain`

**Status:** ✅ FIXED - Server needs restart to apply changes
