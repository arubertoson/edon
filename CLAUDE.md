# CLAUDE.md - Edon Python Development Guide

## Project Context
This is a Python 3.13 project using PySide6 for Qt bindings. The codebase follows strict engineering principles focused on safety, performance, and maintainability with zero technical debt tolerance.

## Core Development Philosophy (Tiger Style Inspired)

### Four Pillars (Priority Order)
1. **Safety**: Code works correctly, reduces error risk
2. **Performance**: Efficient resource use, responsive software  
3. **Developer Experience**: Readable, maintainable, collaborative code
4. **Zero Technical Debt**: Get it right the first time

## Code Standards (Mandatory)

### Type Hinting (Required for ALL code)
- **Every** function parameter, return value, class attribute, and significant variable MUST be type hinted
- Use modern Python syntax:
  ```python
  # Correct - Python 3.13 style
  def process_items(items: list[str]) -> dict[str, int] | None:
      pass
  
  # Use collections.abc for abstractions
  from collections.abc import Iterable, Callable
  def handle_data(data: Iterable[int], callback: Callable[[int], str]) -> None:
      pass
  ```

### Naming Conventions (Google Style)
- `module_name`, `function_name`, `variable_name`
- `ClassName`, `ExceptionName` 
- `CONSTANT_NAME`, `_internal_name`
- **Descriptive names**: `latency_ms_max` not `lmax`

### Error Handling Strategy (Tiger Style - CRITICAL DISTINCTION)

**Two completely different error types require different handling:**

#### 1. Programmer Errors (Internal/Our Code) → Use `assert`
These are bugs in OUR code that should NEVER happen if we coded correctly:
```python
# Function preconditions - validate our internal contracts
def process_batch(items: list[str], batch_size: int) -> list[ProcessedItem]:
    assert len(items) > 0, "process_batch called with empty list - caller bug"
    assert batch_size > 0, "process_batch called with invalid batch_size - caller bug"
    assert batch_size <= 1000, "batch_size exceeds safety limit - design bug"
    
    # Internal invariants - things that must be true if our logic is correct
    processed = []
    for i in range(0, len(items), batch_size):
        batch = items[i:i + batch_size]
        assert len(batch) > 0, "Logic error: created empty batch"
        result = _process_single_batch(batch)
        assert result is not None, "Internal processor returned None unexpectedly"
        processed.extend(result)
    
    # Postconditions - guarantee our promises to callers
    assert len(processed) >= len(items), "Lost items during processing - logic bug"
    return processed
```

#### 2. Runtime Errors (External/User Input) → Use `try/except`  
These are expected failures from external factors we can't control:
```python
# User input validation - expect bad data
def load_user_config(file_path: str) -> UserConfig:
    try:
        with open(file_path, 'r') as f:
            data = json.load(f)
    except FileNotFoundError:
        raise ConfigError(f"Config file not found: {file_path}")
    except json.JSONDecodeError as e:
        raise ConfigError(f"Invalid JSON in config: {e}")
    except PermissionError:
        raise ConfigError(f"Cannot read config file: {file_path}")
    
    # Now validate the loaded data
    if not isinstance(data, dict):
        raise ConfigError("Config must be a JSON object")
    if "version" not in data:
        raise ConfigError("Config missing required 'version' field")
    
    return UserConfig.from_dict(data)

# Network/external API calls - expect failures
def fetch_user_data(user_id: str) -> UserData:
    try:
        response = requests.get(f"/api/users/{user_id}", timeout=10)
        response.raise_for_status()
    except requests.Timeout:
        raise UserDataError("API request timed out")
    except requests.ConnectionError:
        raise UserDataError("Cannot connect to user API")
    except requests.HTTPError as e:
        if e.response.status_code == 404:
            raise UserNotFoundError(f"User {user_id} not found")
        raise UserDataError(f"API error: {e}")
    
    return UserData.from_json(response.json())
```

#### The Key Principle:
- **`assert`** = "This should be impossible if our code is correct" 
- **`try/except`** = "This might fail due to external factors"

**Never use assertions for user input or external system validation!**

### Function Design Rules
- **Max 70 lines per function** 
- **Single responsibility principle**
- **Parent functions control flow**, helpers do calculations
- **Simple signatures** - minimize parameters
- **Clear return types** - prefer `None`, `bool`, or simple types

### Performance Guidelines (Optimization Priority)
1. **Network** - minimize transfers, reduce latency, batch requests
2. **Disk** - buffer I/O, avoid redundant writes  
3. **Memory** - use generators, avoid large copies, efficient data structures
4. **CPU** - leverage built-ins, efficient algorithms

### Import Organization
```python
# Standard library
import os
from pathlib import Path
from typing import TYPE_CHECKING

# Third-party
from loguru import logger
from PySide6.QtWidgets import QWidget

# Local imports (absolute paths)
from edon_ui.widgets import CustomWidget
from edon_core.models import DataModel

# Type-only imports
if TYPE_CHECKING:
    from edon_core.interfaces import ProcessorProtocol
```

## Project-Specific Patterns

### Logging with Loguru
```python
from loguru import logger

# Never log sensitive data (passwords, PII) at INFO+ levels
logger.trace("Detailed step-by-step debugging")      # Dev only
logger.debug("Function entry, state changes")        # Dev/temp prod  
logger.info("Major operations, lifecycle events")    # Production overview
logger.warning("Recoverable issues, deprecated use") # Continues running
logger.error("Operation failed, degraded mode")      # Serious problems
logger.critical("App instability, may not continue") # Severe errors
```

### Resource Management
```python
# Always use context managers
with open(file_path) as f:
    data = f.read()

# Or explicit cleanup  
connection = create_connection()
try:
    result = connection.execute(query)
finally:
    connection.close()
```

### Control Flow Patterns
```python
# Prefer guard clauses over deep nesting
def process_user_data(user_data: dict[str, str]) -> ProcessResult | None:
    if not user_data:
        logger.warning("Empty user data provided")
        return None
        
    if "email" not in user_data:
        logger.error("Missing required email field")
        return None
    
    # Main logic here - no nesting
    return ProcessResult(...)

# Centralize branching in parent functions
def handle_request(request_type: str, data: dict) -> Response:
    match request_type:
        case "create":
            return _create_handler(data)  # Pure logic, no branching
        case "update": 
            return _update_handler(data)  # Pure logic, no branching
        case _:
            raise ValueError(f"Unknown request type: {request_type}")
```

## Code Organization

### File Structure Expectations
- High-level logic before implementation details
- Related functions grouped together with blank line separation
- Clear logical "paragraphs" of code
- One class per file (generally)

### Variable Scope
- Declare variables in smallest possible scope
- Near point of use
- Avoid global state where possible

## Dependencies & Tooling

### Package Management
- Uses `pyproject.toml` + `uv` (`uv.lock`)
- Justify all new dependencies
- Keep dependencies updated

### Code Quality
- No purely stylistic changes in feature PRs
- Separate refactoring commits
- Consistency with existing codebase patterns

## Quick Performance Estimation (Napkin Math)
When designing features, do quick back-of-envelope calculations:
```
Example: Log storage needs
- 1k requests/sec × 1KB/log × 86400 sec/day = ~86GB/day
- Monthly: 86GB × 30 = ~2.6TB
- Cost estimate: 2600GB × $0.02 = ~$52/month
```
Aim for 10x accuracy to inform early design decisions.

## When Writing Code for This Project

1. **Start with type hints** - define interfaces first
2. **Consider performance early** - don't optimize prematurely but design efficiently  
3. **Write assertions** - fail fast on programmer errors
4. **Handle runtime errors explicitly** - no silent failures
5. **Keep functions focused** - single responsibility, <70 lines
6. **Use descriptive names** - code should read like documentation
7. **Minimize scope** - variables, imports, dependencies
8. **Test edge cases** - especially around limits and boundaries

## Red Flags to Avoid
- Missing type hints
- Functions >70 lines  
- Deep nesting (>3 levels)
- **Using `try/except` for internal validation** (should be `assert`)
- **Using `assert` for user input validation** (should be `try/except`)
- Silent error handling (`except: pass`)
- Vague variable names (`data`, `result`, `item`)
- Unnecessary dependencies
- Global state mutations
- Manual resource management without cleanup
