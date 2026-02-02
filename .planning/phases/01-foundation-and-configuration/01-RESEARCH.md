# Phase 1: Foundation & Configuration - Research

**Researched:** 2026-02-01
**Domain:** Python AI Systems Configuration
**Confidence:** HIGH

## Summary

This research provides a comprehensive guide for establishing a robust foundation for the Demi project, focusing on key aspects of configuration, logging, state persistence, platform integration, and error handling. The goal is to create a flexible, performant, and maintainable system architecture that can support future emotional complexity and multi-platform interactions.

**Primary recommendation:** Adopt a modular, environment-aware configuration system with graceful error handling and comprehensive logging.

## Standard Stack

### Core Libraries
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `environs` | Latest | Environment Variable Parsing | Provides type-safe, flexible configuration parsing |
| `structlog` | Latest | Structured Logging | High-performance logging with structured output |
| `sqlite3` | Python Standard Library | State Persistence | Built-in, lightweight database for local storage |
| `pydantic` | Latest | Configuration Validation | Enforces type safety and provides runtime configuration validation |

### Supporting Libraries
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `loguru` | Latest | Advanced Logging | When more complex logging features are needed |
| `dynaconf` | Latest | Multi-source Configuration | For complex, multi-environment configurations |
| `better-sqlite3` | Latest | High-performance SQLite | When advanced SQLite performance is critical |

## Architecture Patterns

### Recommended Project Structure
```
demi/
├── config/              # Configuration management
│   ├── base.yaml        # Base configuration
│   ├── development.yaml # Dev-specific overrides
│   └── production.yaml  # Prod-specific overrides
├── platforms/           # Platform-specific stubs
│   ├── minecraft.py
│   ├── twitch.py
│   ├── tiktok.py
│   └── youtube.py
├── core/                # Core system components
│   ├── logging.py       # Logging configuration
│   ├── database.py      # State persistence
│   └── error_handler.py # Centralized error management
└── emotional/           # Future emotional system
    └── placeholder.py
```

### Configuration Cascading Pattern
```python
def load_configuration():
    """
    Load configuration with priority:
    1. Environment Variables (Highest)
    2. Project-specific Config
    3. Global User Config
    4. Default Configuration (Lowest)
    """
    config = Config()
    config.load_from_env()
    config.load_from_project_file()
    config.load_from_user_config()
    config.load_defaults()
    return config
```

### Logging Configuration Pattern
```python
import structlog
import logging

def configure_logging(log_level='INFO'):
    """
    Configure structured, context-aware logging
    Supports different formats for console and file
    """
    logging.basicConfig(
        level=log_level,
        format='%(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('demi.log')
        ]
    )
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.processors.TimeStamper(fmt='iso'),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer()
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
```

### SQLite State Management Pattern
```python
import sqlite3
from contextlib import contextmanager

class StateManager:
    """
    Efficient SQLite state persistence with transaction support
    """
    def __init__(self, db_path='demi_state.sqlite'):
        self.db_path = db_path
    
    @contextmanager
    def transaction(self):
        conn = sqlite3.connect(self.db_path)
        try:
            yield conn.cursor()
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise
        finally:
            conn.close()
```

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Logging | Custom logging | `structlog` | Handles structured, contextual logging |
| Config Parsing | Manual parsing | `environs`/`dynaconf` | Handles type conversion, validation |
| State Persistence | Custom file/dict storage | SQLite with `sqlite3` | ACID transactions, indexing |
| Error Tracking | Manual error logs | Exception hooks in stdlib | Consistent error reporting |

## Common Pitfalls

### Pitfall 1: Environment-Agnostic Configuration
**What goes wrong:** Hard-coded or inflexible configurations
**Why it happens:** Developer assumes single deployment environment
**How to avoid:** Use multi-source configuration with clear precedence
**Warning signs:** 
- Configuration deeply embedded in code
- Separate config files for each environment
- Manual environment switching

### Pitfall 2: Inconsistent Logging
**What goes wrong:** Unstructured, hard-to-parse logs
**Why it happens:** Using print statements or basic logging
**How to avoid:** Adopt structured logging with context
**Warning signs:**
- Logs without timestamps
- Inconsistent log levels
- No log rotation or size management

### Pitfall 3: Inefficient State Management
**What goes wrong:** Slow or unreliable state persistence
**Why it happens:** Using inefficient storage mechanisms
**How to avoid:** Use SQLite with proper indexing and transactions
**Warning signs:**
- Frequent full-table scans
- No transaction support
- Large in-memory state objects

## Code Examples

### Platform Stub Template
```python
from abc import ABC, abstractmethod

class PlatformStub(ABC):
    """Abstract base for platform integration"""
    
    @abstractmethod
    async def authenticate(self):
        """Platform-specific authentication"""
        pass
    
    @abstractmethod
    async def generate_mock_response(self, context):
        """Generate realistic mock responses"""
        pass
```

### Robust Error Handling
```python
import functools
import logging

def handle_platform_errors(func):
    """Decorator for consistent error handling across platform stubs"""
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except ConnectionError as e:
            logging.error(f"Platform connection error: {e}")
            return None
        except Exception as e:
            logging.exception(f"Unexpected error in {func.__name__}")
            raise
    return wrapper
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Print debugging | Structured logging | 2024 | Better observability |
| Manual config | Environment-aware parsing | 2025 | More flexible deployments |
| File-based storage | SQLite with transactions | 2025 | Improved data integrity |

## Open Questions

1. **Long-term State Persistence**
   - What are the best strategies for migrating state across versions?
   - How to handle schema evolution in SQLite?

2. **Multi-Platform Error Handling**
   - How to create a unified error tracking mechanism across different platforms?
   - Best practices for error contextualization?

## Sources

### Primary (HIGH confidence)
- Python Standard Library Documentation
- `environs` library documentation
- `structlog` official documentation

### Secondary (MEDIUM confidence)
- Real-world AI agent implementation guides
- Recent conference presentations on AI system design

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - Based on current library ecosystem
- Architecture: HIGH - Follows modern Python best practices
- Pitfalls: MEDIUM - Derived from multiple sources

**Research date:** 2026-02-01
**Valid until:** 2026-03-01 (30 days from research)