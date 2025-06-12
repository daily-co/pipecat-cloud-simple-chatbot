#
# Copyright (c) 2024–2025, Daily
#
# SPDX-License-Identifier: BSD 2-Clause License
#

"""
This module contains FastAPI endpoints which can be used to start bots for local development.

It includes:
- FastAPI endpoints for starting agents and checking bot statuses.
- Dynamic loading of bot implementations.
- Use of a Daily transport for bot communication.
"""

import argparse
import json
import os
import shlex
import subprocess
from contextlib import asynccontextmanager
from typing import Any, Dict

import aiohttp
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from utils.daily_helpers import create_daily_room

# Load environment variables from .env file
load_dotenv(override=True)

# Set LOCAL_RUN environment variable for local development
os.environ["LOCAL_RUN"] = "1"

# Dictionary to track bot processes: {pid: (process, room_url)}
bot_procs = {}

# Store Daily API helpers
daily_helpers = {}


def cleanup():
    """Cleanup function to terminate all bot processes.

    Called during server shutdown.
    """
    for entry in bot_procs.values():
        proc = entry[0]
        proc.terminate()
        proc.wait()


async def create_room_and_token() -> tuple[str, str]:
    """Create a Daily room and generate an authentication token.

    This function checks for existing room URL and token in the environment variables.
    If not found, it creates a new room using the Daily API and generates a token for it.

    Returns:
        tuple[str, str]: A tuple containing the room URL and the authentication token.

    Raises:
        HTTPException: If room creation or token generation fails.
    """
    from pipecat.transports.services.helpers.daily_rest import DailyRoomParams

    room_url = os.getenv("DAILY_SAMPLE_ROOM_URL", None)
    token = os.getenv("DAILY_SAMPLE_ROOM_TOKEN", None)
    if not room_url:
        room = await daily_helpers["rest"].create_room(DailyRoomParams())
        if not room.url:
            raise HTTPException(status_code=500, detail="Failed to create room")
        room_url = room.url

        token = await daily_helpers["rest"].get_token(room_url)
        if not token:
            raise HTTPException(
                status_code=500, detail=f"Failed to get token for room: {room_url}"
            )

    return room_url, token


@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI lifespan manager that handles startup and shutdown tasks.

    - Creates aiohttp session
    - Initializes Daily API helper
    - Cleans up resources on shutdown
    """
    from pipecat.transports.services.helpers.daily_rest import DailyRESTHelper

    aiohttp_session = aiohttp.ClientSession()
    daily_helpers["rest"] = DailyRESTHelper(
        daily_api_key=os.getenv("DAILY_API_KEY", ""),
        daily_api_url=os.getenv("DAILY_API_URL", "https://api.daily.co/v1"),
        aiohttp_session=aiohttp_session,
    )
    yield
    await aiohttp_session.close()
    cleanup()


# Initialize FastAPI app with lifespan manager
app = FastAPI(lifespan=lifespan)

# Configure CORS to allow requests from any origin
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


async def start():
    """Internal method to start a bot agent and return the room URL and token.

    Returns:
        tuple[str, str]: A tuple containing the room URL and token.
    """
    room_url, token = await create_room_and_token()
    # Pass LOCAL_RUN=1 to the subprocess
    proc = subprocess.Popen(
        [f"LOCAL_RUN=1 python3 -m runner -u {room_url} -t {token}"],
        shell=True,
        bufsize=1,
        cwd=os.path.dirname(os.path.abspath(__file__)),
    )
    bot_procs[proc.pid] = (proc, room_url)

    return room_url, token


@app.get("/")
async def start_agent():
    """A user endpoint for launching a bot agent and redirecting to the created room URL.

    This function retrieves the bot implementation from the environment,
    starts the bot agent, and redirects the user to the room URL to
    interact with the bot through a Daily Prebuilt Interface.

    Returns:
        RedirectResponse: A response that redirects to the room URL.
    """
    print("Starting bot")
    room_url, token = await start()

    return RedirectResponse(room_url)


@app.post("/start")
async def handle_incoming_daily_webhook(request: Request) -> JSONResponse:
    """Handle incoming Daily call webhook."""
    print("Received webhook from Daily")

    # Get the dial-in properties from the request
    try:
        data = await request.json()
        if "test" in data:
            # Pass through any webhook checks
            return JSONResponse({"test": True})

        if not all(key in data for key in ["From", "To", "callId", "callDomain"]):
            raise HTTPException(
                status_code=400,
                detail="Missing properties 'From', 'To', 'callId', 'callDomain'",
            )

        # Extract the caller's phone number
        caller_phone = str(data.get("From"))
        print(f"Processing call from {caller_phone}")

        # Create a Daily room with dial-in capabilities
        try:
            room_details = await create_daily_room(
                request.app.state.session, caller_phone
            )
        except Exception as e:
            print(f"Error creating Daily room: {e}")
            raise HTTPException(
                status_code=500, detail=f"Failed to create Daily room: {str(e)}"
            )

        room_url = room_details["room_url"]
        token = room_details["token"]
        print(f"Created Daily room: {room_url} with token: {token}")

        body_json = json.dumps(data)

        bot_cmd = f"python3 -m bot -u {room_url} -t {token} -b {shlex.quote(body_json)}"

        try:
            # CHANGE: Keep stdout/stderr for debugging
            # Start the bot in the background but capture output
            subprocess.Popen(
                bot_cmd,
                shell=True,
                # Don't redirect output so we can see logs
                # stdout=subprocess.DEVNULL,
                # stderr=subprocess.DEVNULL
            )
            print(f"Started bot process with command: {bot_cmd}")
        except Exception as e:
            print(f"Error starting bot: {e}")
            raise HTTPException(
                status_code=500, detail=f"Failed to start bot: {str(e)}"
            )

    except HTTPException:
        raise
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Server error: {str(e)}")

    # Grab a token for the user to join with
    return JSONResponse({"room_url": room_url, "token": token})


@app.post("/connect")
async def rtvi_connect() -> Dict[Any, Any]:
    """A user endpoint for launching a bot agent and retrieving the room/token credentials.

    This function retrieves the bot implementation from the request, if provided,
    starts the bot agent, and returns the room URL and token for the bot. This allows the
    client to then connect to the bot using their own RTVI interface.

    Returns:
        Dict[Any, Any]: A dictionary containing the room URL and token.
    """
    print("Starting bot")
    room_url, token = await start()

    return {"room_url": room_url, "token": token}


if __name__ == "__main__":
    import uvicorn

    # Parse command line arguments for server configuration
    default_host = os.getenv("HOST", "0.0.0.0")
    default_port = int(os.getenv("FAST_API_PORT", "7860"))

    parser = argparse.ArgumentParser(description="Daily Simple Chatbot Server")
    parser.add_argument("--host", type=str, default=default_host, help="Host address")
    parser.add_argument("--port", type=int, default=default_port, help="Port number")
    parser.add_argument("--reload", action="store_true", help="Reload code on change")

    config = parser.parse_args()

    # Start the FastAPI server
    uvicorn.run(
        "server:app",
        host=config.host,
        port=config.port,
        reload=config.reload,
    )
