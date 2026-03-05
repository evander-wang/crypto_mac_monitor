# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Bitcoin (BTC) trading bot and monitoring system using OKX API. It provides contract information display, alerts, trading information display, and trading execution. The system has both macOS menu bar and Linux server deployments with real-time cryptocurrency market analysis, trend detection, and multi-channel notifications.

**Runtime Environment**: Uses conda environment `freqtrade` with Python 3.12.11

```bash
conda activate freqtrade
```

## Key Dependencies and Libraries

- **OKX API**: Uses `ccxt>=4.4.91` and OKX native SDK (<https://www.okx.com/docs-v5/zh/#overview>)
- **Dependency Injection**: Uses `dependency-injector` for component decoupling
- **Event System**: Uses `pyee` (Node.js-style EventEmitter) for event bus
- **Technical Analysis**: Requires **TA-Lib** (critical dependency)
- **Testing**: Uses pytest framework

## Architecture

The application uses an **event-driven architecture** with **dependency injection**:

- **Entry Points**:
  - `ok-cex-mac-bar-v2.py` - macOS menu bar application
  - `btc_linux_server.py` - Linux server daemon
  - `run_tests.py` - Test runner

**Entry Point Pattern**:
- All entry points call `load_dotenv()` before other imports
- Pattern: `from dotenv import load_dotenv` → `load_dotenv()` → other imports
- This ensures .env is loaded before any config is accessed

- **Core Architecture Components**:
  - `app/core/di_container.py` - Dependency injection container
  - `app/events/bridge.py` - Event bridge system for component communication
  - `app/core/mac_bar_container.py` - macOS-specific container

- **Major Modules**:
  - `app/data_manager/` - Data caching and scheduling
  - `app/analysis/` - Real-time and trend analysis
  - `app/trend_analysis/` - Technical indicators and models
  - `daemon_alerts/` - Alert conditions and management
  - `app/notifications_v2/` - Multi-channel notification system
  - `app/ui/` - macOS floating window UI
  - `app/config/` - Configuration management

## Development Commands

### Running the Application

**macOS Development**:

```bash
python ok-cex-mac-bar-v2.py --log-level=INFO --config=config/app_config.yaml
```

**Linux Server Deployment**:

```bash
# Set environment variable
export NOTIFICATION_EMAIL_PASSWORD=xxxxx

# Copy config and run in background
cp config/app_config.yaml config/linux_app_config.yaml
nohup /opt/mac_bar/myenv/bin/python3 btc_linux_server.py --log-level=INFO --config=/opt/mac_bar/config/linux_app_config.yaml >> ./btc.log &
```

### Testing

```bash
# Run all tests
python run_tests.py

# Run specific test modules (examples from the codebase)
python -m pytest app/notifications_v2/tests/
python -m pytest app/notifications_v2/tests/unit/test_desktop_channel.py
```

### Dependencies

```bash
# Install all dependencies
pip install -r requirements.txt
```

### Code Quality

```bash
# Format code (Ruff replaces black + isort)
ruff format .

# Check and fix linting issues (Ruff replaces flake8)
ruff check app/ tests/
ruff check --fix app/ tests/

# Clean Python cache files
make clean
```

### Git Workflow

**Branch naming**: Feature branches use `feature/` prefix
```bash
git checkout -b feature/description
```

## Key Configuration Files

- `config/app_config.yaml` - Main application configuration (trading pairs, timeframes, UI settings)
- `config/notifications_v2_config.yaml` - Notification channels and settings
- `pyproject.toml` - Ruff configuration (line-length: 138, black-compatible)
- `.env.example` - Environment variable template (DO NOT commit actual .env)

## Environment Variables

**Entry points load .env automatically**: Both `ok-cex-mac-bar-v2.py` and `btc_linux_server.py` call `load_dotenv()` on startup.

**Environment variable priority** (highest to lowest):
1. System environment variables
2. .env file (auto-loaded)
3. YAML config files

**Key environment variables**:
- OKX API: `OKX_API_KEY`, `OKX_SECRET`, `OKX_PASSPHRASE`, `OKX_SANDBOX`
- Notifications: `NOTIFICATION_ENABLED`, `NOTIFICATION_MIN_LEVEL`, `WEBHOOK_URL`
- Email: `BTC_NOTICE_SMTP_PASSWD_1`, `BTC_NOTICE_SMTP_PASSWD_2`, `BTC_NOTICE_SMTP_PASSWD_3`

## Code Style Standards

- **PEP 8**: Follow PEP 8 style guidelines
- **Line Length**: 138 characters (configured in Ruff)
- **Type Hints**: Use type hinting for all function signatures
- **Docstrings**: Include docstrings for all classes and functions
- **Constants**: Use UPPERCASE_WITH_UNDERSCORES for constants, defined in `app/consts/consts.py`
- **Return Types**: Use dataclass objects for function returns (defined in `app/models/dto.py` with `Return` prefix) for IDE autocomplete support

## Architecture Patterns

### Dependency Injection Pattern

The project uses dependency injection (`dependency-injector` library) to decouple components:

- Independent components (data manager, trend analyzer, etc.) should be designed to work standalone and be easily importable
- Ensure clear interfaces that are easy to extend and maintain
- Reference implementation: `app/notifications_v2/` module

### Event-Driven Threading Model

The system uses a sophisticated multi-threaded event architecture:

**Three Main Threads**:
1. **Data Thread** (TID shown in logs): Fetches K-line data and publishes to analysis thread
2. **Analysis Thread**: Receives K-line update events, processes trend analysis
3. **UI Thread**: Receives analysis results and updates interface

**Event Flow**:
```
Data Thread → [EVENT_KLINE_UPDATE] → Analysis Thread → [Cache Read] → Trend Analysis → [EVENT_TREND_UPDATE] → UI Thread
```

**Event Bus System** (`app/events/bridge.py`):
- **Per-thread bus**: Use `EventBusFactory.get_bus_for_current_thread()` for same-thread communication
- **UI Bridge**: `publish_to_ui(topic, data)` for other threads → main thread (queue + debouncing + timer pump)
- **Alert Bridge**: `publish_to_alerts(topic, data)` for other threads → alert thread (asyncio loop)
- **Subscription**: UI components use `get_ui_event_bus().on(event, handler)`, alert components use `get_alert_event_bus().on(event, handler)`

**Critical**: All AppKit/Cocoa operations MUST be on main thread. Use `NSOperationQueue.mainQueue().addOperationWithBlock_(...)` for UI updates to avoid `depythonifying 'SEL'` errors.

### Module Structure Reference

See `docs/architecture/README.md` for detailed architecture diagrams and `docs/events_bridge_diagrams.md` for event flow diagrams.

## Development Guidelines

### When Adding New Features

1. **Code Style**: Follow project patterns (PEP 8, type hints, docstrings)
2. **Dependencies**: Do NOT introduce new dependencies without approval from maintainers
3. **Impact**: Ensure changes don't break existing functionality or performance
4. **Simplicity**: Keep code concise and focused; avoid unnecessary complexity
5. **Testing**: Write complete test cases; modules should be runnable independently
6. **Use Third-Party Libraries**: Don't reinvent the wheel; use existing packages when available

### When Working with Events

- Define new events in `app/consts/consts.py` with clear naming
- Event naming pattern: `EVENT_<DOMAIN>_<ACTION>` (e.g., `EVENT_KLINE_UPDATE`, `EVENT_TREND_UPDATE`)
- Use appropriate bridge methods: `publish_to_ui()`, `publish_to_alerts()`, or `get_event_bus().emit()`
- Always clean up subscriptions: call appropriate cleanup methods on shutdown
- See `docs/architecture/README.md` section 5 for detailed event bus documentation

### When Working with Data Structures

- Define DTOs in `app/models/dto.py`
- DTO naming: `Return<Entity>DTO` (e.g., `ReturnTickerDTO`, `ReturnKlineUpdateDTO`)
- All DTOs must use `@dataclass` decorator and include `to_dict()` method
- This provides IDE autocomplete and better type safety
- Example: `ReturnTickerDTO`, `PriceDTO`

## Security Policy

**NEVER read the `.env` file** - It contains sensitive API keys, passwords, and secrets. The `.env` file is intentionally excluded from version control and must never be accessed by AI tools. Always use `.env.example` as the reference for environment variable structure.

When working with environment variables:
- Only read `.env.example` to understand the variable structure
- Never attempt to read the actual `.env` file
- Use `os.getenv()` in code to access environment variable values

### Security Best Practices

**Never commit sensitive data**:
- Use `.env` for local development (gitignored)
- Use environment variables in production
- Never hardcode API keys, passwords, or tokens in code
- Never use `print()` on sensitive data (API keys, secrets, passwords)
- Use example data in configs (e.g., `user@example.com` instead of real emails)

**Code security patterns**:
- Email passwords are loaded from environment variables, not config files
- See `app/notifications_v2/channels/email_channel.py` for the pattern

## Important Development Notes

### Technical Analysis System

- Uses **TA-Lib** for technical indicators (required dependency)
- Supports multiple timeframes: 1m, 5m, 1h (configurable)
- Implements trend models: breakout, channel, consolidation
- Real-time analysis with configurable confidence thresholds

### Multi-Platform Support

- **macOS**: Uses `rumps` for menu bar, floating window UI
- **Linux**: Headless operation with notification-based alerts

### Notification System v2

- Multi-channel: desktop, email, webhook, Telegram
- Configurable levels and channels
- Rate limiting and cooldown periods
- See `app/notifications_v2/README.md` for usage guide
- **This module has been refactored and is ready to use directly**

### Data Management

- Thread-safe memory caching with TTL
- Event-driven data updates
- Configurable buffer sizes and expiry times

### Alert System

- Condition-based alerts in `daemon_alerts/conditions/`
- Supports various technical indicators: ADX, Bollinger Bands, MACD, RSI, etc.
- Configurable thresholds and cooldown periods
