# Contributing to Demi

Thank you for your interest in contributing to Demi! This document provides guidelines for contributing to the project.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Code Style](#code-style)
- [Testing](#testing)
- [Pull Request Process](#pull-request-process)
- [Documentation](#documentation)
- [Commit Messages](#commit-messages)

## Code of Conduct

This project and everyone participating in it is governed by our commitment to:

- Be respectful and inclusive
- Welcome newcomers and help them learn
- Focus on constructive feedback
- Accept responsibility and apologize when mistakes happen

## Getting Started

### Prerequisites

- Python 3.10+
- Git
- Ollama (for LLM features)
- FFmpeg and espeak (for voice features)

### Fork and Clone

```bash
# Fork the repository on GitHub, then clone your fork
git clone https://github.com/YOUR_USERNAME/demi.git
cd demi

# Add upstream remote
git remote add upstream https://github.com/original_owner/demi.git
```

## Development Setup

### 1. Create Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

### 2. Install Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 3. Install Development Tools

```bash
# Linting and formatting
pip install ruff mypy bandit

# Testing
pip install pytest pytest-asyncio pytest-cov

# Pre-commit hooks (optional but recommended)
pip install pre-commit
pre-commit install
```

### 4. Configure Environment

```bash
cp .env.example .env
# Edit .env with your settings
```

### 5. Verify Setup

```bash
# Run tests
pytest -v

# Check linting
ruff check src/

# Run application
python main.py --dry-run
```

## Code Style

We use automated tools to maintain code quality:

### Linting with ruff

```bash
# Check code
ruff check src/

# Fix auto-fixable issues
ruff check src/ --fix

# Format code
ruff format src/
```

### Type Hints

Use type hints for function signatures and important variables:

```python
from typing import Optional, Dict, List

async def process_message(
    content: str,
    user_id: int,
    context: Optional[Dict] = None
) -> str:
    """Process a user message and return a response."""
    ...
```

### Docstrings

Use Google-style docstrings:

```python
def calculate_emotional_decay(
    current_value: float,
    decay_rate: float,
    time_delta: float
) -> float:
    """Calculate emotional decay over time.
    
    Args:
        current_value: Current emotional intensity (0.0 to 1.0)
        decay_rate: Rate of decay per hour
        time_delta: Time elapsed in hours
        
    Returns:
        New emotional intensity after decay
        
    Example:
        >>> calculate_emotional_decay(0.8, 0.1, 2.0)
        0.64
    """
    return current_value * (1 - decay_rate) ** time_delta
```

### Naming Conventions

- **Modules**: lowercase with underscores (`emotion_engine.py`)
- **Classes**: PascalCase (`EmotionalState`)
- **Functions/Variables**: lowercase with underscores (`process_input`)
- **Constants**: UPPER_CASE (`MAX_HISTORY_LENGTH`)
- **Private**: leading underscore (`_internal_helper`)

### Code Organization

```python
# Standard library imports
import asyncio
import json
from typing import Optional

# Third-party imports
import discord
from fastapi import FastAPI

# Local imports
from src.core.config import DemiConfig
from src.emotion.models import EmotionalState

# Constants
DEFAULT_TIMEOUT = 30

# Classes
class MyClass:
    """Class docstring."""
    pass

# Functions
def public_function():
    """Function docstring."""
    pass

def _private_function():
    """Private function docstring."""
    pass
```

## Testing

### Running Tests

```bash
# Run all tests
pytest -v

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test file
pytest tests/test_emotion_models.py -v

# Run with debug output
pytest -v --log-cli-level=DEBUG
```

### Writing Tests

```python
import pytest
from src.emotion.models import EmotionalState

@pytest.fixture
def neutral_state():
    """Create a neutral emotional state for testing."""
    return EmotionalState()

class TestEmotionalState:
    """Test suite for EmotionalState."""
    
    def test_initial_state_is_neutral(self, neutral_state):
        """Test that new states start neutral."""
        assert neutral_state.valence == 0.0
        assert neutral_state.arousal == 0.0
    
    def test_decay_reduces_intensity(self, neutral_state):
        """Test that emotional decay works correctly."""
        neutral_state.affection = 0.8
        neutral_state.decay(hours=1.0)
        assert neutral_state.affection < 0.8
```

### Test Coverage

Aim for >90% test coverage. Focus on:

- Critical business logic
- Edge cases
- Error handling
- Public APIs

## Pull Request Process

### Before Submitting

1. **Sync with upstream:**
   ```bash
   git fetch upstream
   git rebase upstream/main
   ```

2. **Run quality checks:**
   ```bash
   ruff check src/
   ruff format --check src/
   pytest -v
   mypy src/ --ignore-missing-imports
   bandit -r src/
   ```

3. **Update documentation:**
   - Add docstrings to new functions
   - Update relevant .md files
   - Add/update tests

### Creating the PR

1. **Push to your fork:**
   ```bash
   git push origin feature/my-feature
   ```

2. **Create PR on GitHub:**
   - Use a clear title
   - Fill out the PR template
   - Link related issues
   - Add screenshots for UI changes

3. **PR Checklist:**
   - [ ] Code follows style guidelines
   - [ ] Tests pass
   - [ ] Documentation updated
   - [ ] CHANGELOG.md updated (if applicable)
   - [ ] No merge conflicts

### Review Process

- Maintainers will review within 48 hours
- Address review feedback promptly
- Be open to suggestions
- Ask questions if unclear

### After Merge

- Delete your feature branch
- Update your local main branch
- Celebrate! 🎉

## Documentation

### Code Documentation

- Every public function/class needs a docstring
- Explain the "why", not just the "what"
- Include examples for complex functions
- Document exceptions that may be raised

### Markdown Documentation

- Use clear, concise language
- Include code examples
- Keep line length reasonable (<100 chars)
- Use proper markdown formatting

### Architecture Decisions

Document significant decisions in `.planning/decisions/`:

```markdown
# Decision: [Title]

**Date:** YYYY-MM-DD
**Status:** Accepted / Proposed / Deprecated

## Context
What is the issue we're solving?

## Decision
What did we decide?

## Consequences
What are the trade-offs?
```

## Commit Messages

Use conventional commits format:

```
<type>(<scope>): <description>

[optional body]

[optional footer]
```

### Types

- **feat:** New feature
- **fix:** Bug fix
- **docs:** Documentation changes
- **style:** Code style (formatting, no logic change)
- **refactor:** Code refactoring
- **test:** Test changes
- **chore:** Build/process changes

### Examples

```
feat(emotion): add jealousy calculation

Implements emotional jealousy based on interaction gaps.
Jealousy increases when user interacts with other projects.

Closes #123
```

```
fix(discord): handle missing permissions gracefully

Previously crashed when bot lacked channel permissions.
Now logs warning and continues operation.
```

```
docs(api): add authentication examples

Added curl examples for login and token refresh.
```

## Areas for Contribution

### High Priority

- Performance optimizations
- Security improvements
- Test coverage
- Documentation

### Good First Issues

Look for issues labeled:
- `good first issue`
- `help wanted`
- `documentation`

### Feature Areas

- **Emotional System:** Mood modeling, personality traits
- **Discord Integration:** New commands, better responses
- **Android API:** New endpoints, optimizations
- **Voice I/O:** STT/TTS improvements
- **Testing:** More comprehensive test coverage

## Getting Help

- **Discord:** Join our community server
- **Issues:** Open a GitHub issue
- **Discussions:** Use GitHub Discussions for questions

## Recognition

Contributors will be:
- Listed in CONTRIBUTORS.md
- Mentioned in release notes
- Given credit in relevant documentation

---

Thank you for contributing to Demi! 💕✨
