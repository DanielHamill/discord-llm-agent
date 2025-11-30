# Discord Agent

Collect/archive messages from your discord server, create your own custom agent using the messages.

## Overview

This project consists of these main components:

1. **fly-on-the-wall** - Discord bot that listens to messages and publishes them to a pub/sub server
2. **RabbitMQ** - Message broker for message distribution

Planned features:

3. **Relational Database** - For long term storage
4. **Custom agent** - Respond to querys in server, act as an API to backend, etc.

## Project Structure

```
discord-llm-agent/
├── fly-on-the-wall/ # discord bot message publisher
├── compose.yaml # docker compose for local development
├── examples/
│ └── subscriber/ # example script for subscribing to messages
├── infra/
│ └── k8s/
│   └── manifests/ # kubernetes manifests for deployments
```