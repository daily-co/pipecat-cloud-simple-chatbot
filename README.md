# Simple Chatbot for Pipecat Cloud

This project demonstrates how to build a complete Pipecat AI agent application with server components.

## Project Overview

- **Server**: Python-based Pipecat bot with video/audio processing capabilities
- **Infrastructure**: Deployable to Pipecat Cloud (server) and Vercel (client)

> See the [simple-chatbot example](https://github.com/pipecat-ai/pipecat/tree/main/examples/simple-chatbot) with different client and server implementations.

## Quick Start (Local run)

### 1. Server Setup

Navigate to the server directory:

```bash
cd server
```

Create and activate a virtual environment:

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

Install requirements:

```bash
pip install -r requirements.txt
```

Copy env.example to .env and add your API keys:

```bash
cp env.example .env
# Edit .env to add OPENAI_API_KEY, CARTESIA_API_KEY, and DAILY_API_KEY
```

Run the server locally to test before deploying:

```bash
python unified-server.py
```

> You can join this client via Daily's Prebuilt UI at http://localhost:7860 or follow step 2 to join from the simple-chatbot client.

## Deployment

> See the [Pipecat Cloud Quickstart](https://docs.pipecat.daily.co/quickstart) for a complete walkthrough.

### Deploy Server to Pipecat Cloud

1. Install the Pipecat Cloud CLI:

```bash
pip install pipecatcloud
```

2. Authenticate:

```bash
pcc auth login
```

3. Build and push your Docker image:

```bash
cd server
chmod +x build.sh
./build.sh
```

> IMPORTANT: Before running this build script, you need to add your DOCKER_USERNAME

4. Create a secret set for your API keys:

```bash
pcc secrets set simple-chatbot-secrets --file .env
```

5. Deploy to Pipecat Cloud:

```bash
pcc deploy
```

> IMPORTANT: Before deploying, you need to add your Docker Hub username

