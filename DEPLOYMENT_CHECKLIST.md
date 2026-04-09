# Deployment Checklist - Production Hardening Phase 1

**Date:** April 9, 2026  
**System:** Attendance Management System Using Facial Recognition  
**Phase:** Security & Stability Improvements

---

## Pre-Deployment Verification

### Code Changes
- [x] All 8 improvements implemented
- [x] Dependencies added (Pillow, slowapi)
- [x] New modules created (validators.py, ratelimiter.py)
- [x] Configuration updated (config.py with env vars)
- [x] Database module enhanced (pooling, pagination)
- [x] Facial recognition model validation added
- [x] Error logging configured

### Testing Completed
- [x] validators.py imports successfully
- [x] ratelimiter.py imports successfully
- [x] config.py loads from .env correctly
- [x] database.py initializes with pooling
- [x] facial_recognition.py model validation working

---

## Deployment Steps

### 1. Environment Setup

**Task:** Create production .env file
```bash
# Copy template
cp .env.example .env

# Edit with production credentials
# Use strong passwords, real database host, etc.
```

**Verification:**
```bash
python -c "from config import DATABASE_CONFIG; \
print('✓ DB configured:', DATABASE_CONFIG['host'])"
```

### 2. Dependency Installation

**Task:** Install new packages
```bash
pip install -r requirements.txt --upgrade
```

**Verification:**
```bash
pip show Pillow slowapi python-dotenv
# Should show all three installed
```

### 3. Model Validation

**Task:** Verify facial recognition models
```bash
python -c "from facial_recognition import get_facial_recognition_system; \
fr = get_facial_recognition_system(); \
print('Model Status:', fr.validate_models())"
```

**Expected Output:**
```
[INFO] Face detector loaded successfully
[INFO] Face embedder loaded successfully
Model Status: {
  'detector_loaded': True,
  'embedder_loaded': True,
  'recognizer_loaded': True,
  'label_encoder_loaded': True,
  'all_models_ready': True
}
```

**If recognizer not loaded:**
```bash
# Retrain models
python auto_train.py
```

### 4. Database Connection Test

**Task:** Verify database connection pooling
```bash
python -c "from database import DatabaseConnection; \
from config import DATABASE_CONFIG; \
db = DatabaseConnection(**DATABASE_CONFIG); \
db.connect(); \
print('✓ Database connection successful'); \
db.disconnect()"
```

### 5. Security Configuration

**Task:** Verify security settings for production
```bash
# Check .env has these set correctly:
grep FASTAPI_DEBUG .env             # Should be False
grep DB_PASSWORD .env               # Should NOT be empty
grep RATE_LIMIT .env                # Should be set
# Don't commit .env!
git status .env                     # Should show: ignored
```

### 6. Log Directory

**Task:** Create logs directory with proper permissions
```bash
mkdir -p logs
chmod 755 logs
# Verify app can write to logs/
```

### 7. Backup Existing Data

**Task:** Database backup before deployment
```bash
# MySQL backup command
mysqldump -h localhost -u root -p school_attendance > backup_$(date +%Y%m%d).sql
```

---

## Production Configuration

### Critical Settings to Review

#### Database (config.env)
```
DB_HOST=your-db-host.example.com  # Not localhost
DB_PORT=3306
DB_USER=attendance_user            # Not root
DB_PASSWORD=strong_password_here   # At least 16 chars
```

#### Security (config.env)
```
FASTAPI_DEBUG=False                # Must be False
FASTAPI_RELOAD=False               # Must be False
CONFIDENCE_THRESHOLD=0.5           # Adjust for accuracy
IMAGE_MAX_SIZE_MB=5                # Size limit
RATE_LIMIT_CALLS=100               # Per minute per IP
```

#### Services (config.env)
```
SMS_ENABLED=False                  # Only if SMS ready
EMAIL_ENABLED=False                # Only if email ready
```

---

## Post-Deployment Verification

### Immediate (First 5 minutes)
- [ ] Application starts without errors
- [ ] Web dashboard accessible at http://localhost:5000
- [ ] Login page loads
- [ ] Database connection shows in logs

### Functional (First hour)
- [ ] Student enrollment works
- [ ] Face recognition accepts image uploads
- [ ] Pagination working (check page params)
- [ ] Rate limiting active (test with rapid requests)
- [ ] Error messages are clear (test with invalid input)

### Monitoring (First day)
- [ ] Check `logs/app.log` for errors
- [ ] Monitor database connection pool usage
- [ ] Verify no face model errors
- [ ] Confirm rate limits working (429 responses)

### Security (First week)
- [ ] .env file not accessible via web
- [ ] No credentials in error messages
- [ ] HTTPS working (if configured)
- [ ] Database backups running

---

## Rollback Plan

### If Critical Issue Found
```bash
# Stop application
Ctrl+C

# Revert to previous version
git checkout <previous-commit>  # Or previous branch

# Reinstall old dependencies
pip install -r requirements.txt

# Restore database (if needed)
mysql -u root -p school_attendance < backup_YYYYMMDD.sql

# Restart application
python app.py
```

---

## Monitoring & Alerts

### Things to Monitor
1. **logs/app.log** - Check daily for errors
   - Search for: `[ERROR]`, `[WARN]`, database issues
   
2. **Database Connection Pool**
   - Monitor: Connection acquisition time
   - Alert if: Retry count > 10/hour

3. **Rate Limiting**
   - Monitor: 429 responses per IP
   - Alert if: Single IP hits limit > 5 times/hour

4. **Model Status**
   - Monitor: Model loading during startup
   - Alert if: Any model marked `False` at startup

5. **API Response Times**
   - Should be < 500ms for most operations
   - Pagination helps reduce large response times

---

## Documentation Updates

### Required
- [ ] Update README.md with environment variable section
- [ ] Add DEPLOYMENT_GUIDE.md with production checklist
- [ ] Update API documentation with rate limits
- [ ] Add troubleshooting guide

### Recommended
- [ ] Create operational runbooks
- [ ] Document on-call procedures
- [ ] Add monitoring dashboard setup
- [ ] Create backup/restore procedures

---

## Sign-Off

### Development Team
- [ ] Code review completed
- [ ] Tests passed
- [ ] Documentation updated
- [ ] Ready for QA

### QA Team
- [ ] Functional testing passed
- [ ] Security testing passed
- [ ] Performance acceptable
- [ ] Ready for production

### Operations Team
- [ ] Infrastructure ready
- [ ] Monitoring configured
- [ ] Backup procedures ready
- [ ] Ready for deployment

---

## Deployment History

| Date | Version | Changes | Status |
|------|---------|---------|--------|
| 2026-04-09 | 2.0.1 | Phase 1: Security & Stability | Pending |
| | | - Env vars, validation, pooling | |
| | | - Pagination, rate limiting, logging | |

---

## Support Contact

**For Issues:** Development Team  
**For Emergencies:** On-call Technical Lead  
**Documentation:** See IMPROVEMENTS.md

---

**Last Updated:** April 9, 2026  
**Next Review:** May 9, 2026
