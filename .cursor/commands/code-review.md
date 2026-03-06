# Code Review Checklist

Review the current changes for quality and consistency.

## Checklist

### TDD & Architecture
- [ ] Clean Architecture respected (domain → application → infrastructure)
- [ ] Tests written first; no production code without a test
- [ ] All tests pass

### Functionality
- [ ] Code does what it's supposed to do
- [ ] Edge cases handled (None, empty, invalid input)
- [ ] Error handling appropriate

### Architecture
- [ ] Domain has no external dependencies
- [ ] Use cases receive ports via constructor
- [ ] New dependencies wired in container.py

### Code Quality
- [ ] Code and comments in English
- [ ] User-facing text in Portuguese
- [ ] Type hints present
- [ ] No hardcoded secrets

### Frontend
- [ ] Labels in Portuguese
- [ ] Uses CSS variables from theme
