## Installation

### 1. Install UV
```bash
pip install uv
```

### 2. Install Dependencies

```bash
uv sync
```

### 3. Configure Environment

Add your discord bot token to a .env file:

```env
DISCORD_TOKEN=your_discord_bot_token_here
```

## Usage

Run the script using UV:

```bash
uv run src/main.py
```

This script has multiple export formats that can be set using environment variables. **CSV is the default for now**.

## Supported Export Formats

- **JSON**: Exports all message metadata in a serializable format
- **CSV**: Exports basic message content (message_id, author, content, created_at)
- **AMQP**: Publishes messages to a message queue