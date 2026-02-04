# Demi Pre-Release Checklist

This checklist ensures Demi is ready for release. Complete all items before tagging v1.0.

## Code Quality Checks

### Linting & Formatting
- [ ] Run ruff linter: `ruff check src/`
- [ ] Run ruff formatter: `ruff format src/`
- [ ] Fix all linting errors
- [ ] Ensure consistent import ordering
- [ ] Remove unused imports

### Type Checking
- [ ] Run mypy: `mypy src/ --ignore-missing-imports`
- [ ] Fix all type errors
- [ ] Add type hints to public APIs where missing

### Security Scan
- [ ] Run bandit: `bandit -r src/`
- [ ] Review all security warnings
- [ ] Verify no hardcoded secrets in code
- [ ] Check for SQL injection vulnerabilities
- [ ] Verify JWT token validation
- [ ] Confirm CORS is properly restricted

### Code Review
- [ ] All TODOs are resolved or documented as issues
- [ ] No debug code left in production paths
- [ ] Error messages are user-friendly
- [ ] Logging doesn't expose sensitive data
- [ ] Consistent naming conventions throughout
- [ ] Docstrings for all public functions/classes

## Testing

### Unit Tests
- [ ] All tests pass: `pytest -v`
- [ ] Test coverage > 90%: `pytest --cov=src --cov-report=html`
- [ ] Review coverage report for gaps
- [ ] Edge cases are tested
- [ ] Error paths are tested

### Integration Tests
- [ ] Discord integration tests pass
- [ ] Android API tests pass
- [ ] LLM inference tests pass
- [ ] Database tests pass
- [ ] Voice processing tests pass

### End-to-End Tests
- [ ] Full conversation flow works
- [ ] Emotional state persists correctly
- [ ] Discord bot responds to mentions
- [ ] Rambles trigger appropriately
- [ ] Android app connects and messages
- [ ] Voice commands work (if implemented)

### Stability Tests
- [ ] Long-running stability test (24+ hours)
- [ ] Memory leak check
- [ ] Resource cleanup verification
- [ ] Recovery from errors
- [ ] Graceful shutdown

## Documentation

### User Documentation
- [ ] README.md is comprehensive and up-to-date
- [ ] Installation guide is tested on clean systems
- [ ] First run guide is clear and complete
- [ ] User guide covers all features
- [ ] Troubleshooting guide resolves common issues
- [ ] API documentation is complete

### Developer Documentation
- [ ] CONTRIBUTING.md exists and is clear
- [ ] Architecture is documented
- [ ] Code comments explain "why" not "what"
- [ ] Database schema is documented
- [ ] Environment variables are documented

### Deployment Documentation
- [ ] Installation scripts work on target platforms
- [ ] Docker setup is tested
- [ ] Backup/restore procedures are tested
- [ ] Maintenance guide is complete
- [ ] System requirements are accurate

## Configuration

### Environment Variables
- [ ] .env.example is complete and accurate
- [ ] All required variables are documented
- [ ] Default values are sensible
- [ ] Sensitive variables have no defaults

### Configuration Files
- [ ] src/core/defaults.yaml is complete
- [ ] All configuration options are documented
- [ ] No hardcoded paths
- [ ] Platform-specific defaults are appropriate

## Security Review

### Authentication & Authorization
- [ ] JWT secrets must be set (no defaults)
- [ ] Token expiration is appropriate
- [ ] Refresh token rotation works
- [ ] Password requirements are enforced
- [ ] Session management is secure

### Data Protection
- [ ] Database files have appropriate permissions
- [ ] No sensitive data in logs
- [ ] API doesn't leak internal errors
- [ ] Input validation on all endpoints
- [ ] Rate limiting consideration (documented if not implemented)

### Network Security
- [ ] CORS origins are restricted
- [ ] API binding is secure by default (127.0.0.1)
- [ ] WebSocket connections are validated
- [ ] Discord webhooks use HTTPS

## Performance Benchmarks

### Response Times
- [ ] API response time < 200ms (local)
- [ ] LLM inference time acceptable
- [ ] Discord message processing < 5s
- [ ] Database queries are optimized

### Resource Usage
- [ ] Memory usage with 1B model is acceptable
- [ ] CPU usage is reasonable
- [ ] Disk usage is tracked and manageable
- [ ] Log rotation is configured

### Scalability
- [ ] Emotional state scales with conversation history
- [ ] Database handles expected data volume
- [ ] Memory doesn't grow unbounded
- [ ] File handles are properly managed

## Release Preparation

### Version & Tagging
- [ ] Version is set in code
- [ ] CHANGELOG.md is updated
- [ ] Git tag v1.0.0 is ready to create
- [ ] Release notes are drafted

### Dependencies
- [ ] requirements.txt is up to date
- [ ] All dependencies are pinned to specific versions
- [ ] Security vulnerabilities checked (safety check)
- [ ] License compatibility verified

### Assets
- [ ] Demi.png is included
- [ ] Logo/icon assets are ready
- [ ] Android APK is built (if applicable)
- [ ] Docker image is built and tested

### Repository
- [ ] .gitignore is complete
- [ ] No large files in repository
- [ ] No secrets in git history (checked with git-secrets or similar)
- [ ] README badges are working
- [ ] All links in documentation are valid

## Final Testing

### Clean Install Test
- [ ] Fresh Ubuntu 22.04 install works
- [ ] Fresh macOS install works
- [ ] WSL2 install works
- [ ] Docker deployment works

### Feature Verification
- [ ] Emotional system works end-to-end
- [ ] Personality responses are consistent
- [ ] Discord bot functions correctly
- [ ] Android integration works
- [ ] Ramble mode triggers appropriately
- [ ] Self-awareness/codebase reading works
- [ ] Refusal capability functions
- [ ] Voice I/O works (if implemented)

### Edge Cases
- [ ] Empty database startup works
- [ ] Recovery from corrupted database
- [ ] Ollama connection failure handling
- [ ] Discord disconnection handling
- [ ] Low memory conditions
- [ ] Concurrent access handling

## Sign-Off

- [ ] All checklist items complete
- [ ] Final code review completed
- [ ] Documentation reviewed
- [ ] Tests pass on CI/CD
- [ ] Security review complete
- [ ] Performance acceptable
- [ ] Known issues documented

## Release Commands

```bash
# Final verification
pytest -v
ruff check src/
bandit -r src/

# Create release
git tag -a v1.0.0 -m "Demi v1.0.0 - Initial Release"
git push origin v1.0.0

# Build and publish (if applicable)
# docker build -t demi:v1.0.0 .
# docker push ...
```

---

**Notes:**
- This checklist should be completed before each major release
- For minor releases, focus on changed components
- Document any waived items with justification
- Keep this checklist updated as the project evolves
