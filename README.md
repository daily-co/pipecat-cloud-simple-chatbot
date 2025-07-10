# Simple Chatbot for Pipecat Cloud

This project demonstrates how to build a complete Pipecat AI agent application with both client and server components. It includes a Next.js client for interacting with a Pipecat AI bot server through Daily.co's WebRTC transport.

<img src="image.png" width="420px">

## Project Overview

- **Server**: Python-based Pipecat bot with video/audio processing capabilities
- **Client**: Next.js TypeScript web application using the Pipecat React & JS SDKs
- **Infrastructure**: Deployable to Pipecat Cloud (server) and Vercel (client)

> See the [three-participant-chatbot example](https://github.com/pipecat-ai/pipecat/tree/main/examples/three-participant-chatbot) with different client and server implementations.

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
python server.py
```

> You can join this client via Daily's Prebuilt UI at http://localhost:7860 or follow step 2 to join from the three-participant-chatbot client.

### 2. Client Setup

In a separate terminal, navigate to the client directory:

```bash
cd client-react
```

Install dependencies:

```bash
npm install
```

Create `.env.local` file and add your `PIPECAT_CLOUD_API_KEY`:

```bash
cp env.local.example .env.local
```

> Create a Pipecat Cloud API public key using the dashboard. This key is still a secret, so protect it. It's meant to launch your Pipecat apps.

Run the client app:

```bash
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) to interact with your agent through the Next.js client.

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
pcc secrets set three-participant-chatbot-secrets --file .env
```

5. Deploy to Pipecat Cloud:

```bash
pcc deploy
```

> IMPORTANT: Before deploying, you need to add your Docker Hub username

### Deploy Client to Vercel

1. Push your Next.js client to GitHub

2. Connect your GitHub repository to Vercel

3. Add your `PIPECAT_CLOUD_API_KEY` and `AGENT_NAME` environment variable in Vercel

4. Deploy with the Vercel dashboard or CLI

## Project Structure

```
three-participant-chatbot/
├── client-next/            # Next.js client application
│   ├── src/
│   │   ├── app/            # Next.js app routes
│   │   │   └── api/
│   │   │       └── connect/ # API endpoint for Daily.co connection
│   │   ├── components/     # React components
│   │   └── providers/      # React providers including RTVIProvider
│   ├── package.json
│   └── README.md          # Client-specific documentation
│
└── server/                # Pipecat bot server
    ├── assets/            # Robot animation frames
    ├── bot.py             # The Pipecat pipeline implementation
    ├── Dockerfile         # For building the container image
    ├── build.sh           # Script for building and pushing Docker image
    ├── requirements.txt   # Python dependencies
    ├── pcc-deploy.toml    # Pipecat Cloud deployment config
    ├── runner.py          # Local dev only: A runner that launches
    ├── server.py          # Local dev only: A FastAPI server to handle inbound requests
    └── README.md          # Server-specific documentation
```
