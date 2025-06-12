#
# Copyright (c) 2024–2025, Daily
#
# SPDX-License-Identifier: BSD 2-Clause License
#

"""Unified Webhook Server.

This server combines the functionality of local-server.py and webhook-server.py.
It can operate in two modes:
1. LOCAL mode: Creates Daily rooms locally and spawns bot processes
2. CLOUD mode: Uses Pipecat Cloud API for deployment

Set the IS_LOCAL environment variable to "1" for local mode, "0" for cloud mode (default: local)
"""

import base64
import hmac
import json
import os
import shlex
import subprocess
import time
from contextlib import asynccontextmanager
from typing import Optional

import aiohttp
import requests
import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from loguru import logger
from utils.daily_helpers import create_daily_room

load_dotenv(override=True)

# Configuration
IS_LOCAL = os.getenv("IS_LOCAL", "1") == "1"  # Default to local mode
SERVER_MODE = "local" if IS_LOCAL else "cloud"


# ----------------- FastAPI Setup ----------------- #

if IS_LOCAL:

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        # Create aiohttp session for Daily API calls in local mode
        app.state.session = aiohttp.ClientSession()
        yield
        await app.state.session.close()

    app = FastAPI(lifespan=lifespan)
else:
    app = FastAPI()


# ----------------- HMAC Validation ----------------- #


def validate_hmac_signature(raw_body: str, headers: dict) -> bool:
    """Validate HMAC signature for webhook security."""
    hmac_secret = os.getenv("PINLESS_HMAC_SECRET")
    timestamp = headers.get("x-pinless-timestamp")
    signature = headers.get("x-pinless-signature")

    if not hmac_secret:
        logger.debug("Skipping HMAC validation - PINLESS_HMAC_SECRET not set")
        return True

    if not timestamp or not signature:
        logger.debug("Skipping HMAC validation - no signature headers present")
        return True

    message = timestamp + "." + raw_body
    base64_decoded_secret = base64.b64decode(hmac_secret)
    computed_signature = base64.b64encode(
        hmac.new(base64_decoded_secret, message.encode(), "sha256").digest()
    ).decode()

    if computed_signature != signature:
        logger.error(
            f"Invalid signature. Expected {signature}, got {computed_signature}"
        )
        return False

    return True


# ----------------- Unified Handler ----------------- #


async def handle_request(
    data: dict, session: Optional[aiohttp.ClientSession] = None
) -> JSONResponse:
    """Handle request in both local and cloud modes."""
    mode = "LOCAL" if IS_LOCAL else "CLOUD"
    logger.info(f"Processing request in {mode} mode")

    # Extract common data
    caller_phone = str(data.get("From", "unknown"))
    logger.info(f"Processing call from {caller_phone}")

    # Prepare common bot configuration
    body_data = {
        "dialin_settings": data,
        "dialout_settings": data.get("dialout_settings", {}),
        "voicemail_detection": data.get("voicemail_detection"),
        "call_transfer": data.get("call_transfer"),
        "sip_headers": data.get("sipHeaders"),
    }

    if IS_LOCAL:
        # LOCAL MODE: Create Daily room and spawn bot process
        if not session:
            raise HTTPException(
                status_code=500, detail="Session required for local mode"
            )

        # Create a Daily room with dial-in capabilities
        try:
            room_details = await create_daily_room(session, caller_phone)
        except Exception as e:
            logger.error(f"Error creating Daily room: {e}")
            raise HTTPException(
                status_code=500, detail=f"Failed to create Daily room: {str(e)}"
            )

        room_url = room_details["room_url"]
        token = room_details["token"]
        logger.info(f"Created Daily room: {room_url} with token: {token}")

        # Start the bot process
        body_json = json.dumps(body_data)
        bot_cmd = f"python3 -m bot -u {room_url} -t {token} -b {shlex.quote(body_json)}"

        try:
            subprocess.Popen(bot_cmd, shell=True)
            logger.info(f"Started bot process with command: {bot_cmd}")
        except Exception as e:
            logger.error(f"Error starting bot: {e}")
            raise HTTPException(
                status_code=500, detail=f"Failed to start bot: {str(e)}"
            )

        return JSONResponse({"room_url": room_url, "token": token})

    else:
        # CLOUD MODE: Call Pipecat Cloud API
        # Prepare dialin settings
        dialin_settings = None
        required_fields = ["To", "From", "callId", "callDomain"]
        if all(key in data and data[key] is not None for key in required_fields):
            dialin_settings = {
                "From": data["From"],
                "To": data["To"],
                "call_id": data["callId"],
                "call_domain": data["callDomain"],
            }
            logger.debug(f"Populated dialin_settings: {dialin_settings}")

        # Configure Daily room properties
        daily_room_properties = {
            "enable_dialout": True,
            "exp": int(time.time()) + (5 * 60),  # 5 minutes from now
        }

        if dialin_settings is not None:
            sip_config = {
                "display_name": data["From"],
                "sip_mode": "dial-in",
                "num_endpoints": 2 if data.get("call_transfer") is not None else 1,
                "codecs": {"audio": ["OPUS"]},
            }
            daily_room_properties["sip"] = sip_config

        # Prepare payload for Pipecat Cloud
        payload = {
            "createDailyRoom": True,
            "dailyRoomProperties": daily_room_properties,
            "body": body_data,
        }

        # Get Pipecat Cloud credentials
        pcc_api_key = os.getenv("PIPECAT_CLOUD_API_KEY")
        agent_name = os.getenv("AGENT_NAME", "phone-bot")

        if not pcc_api_key:
            raise HTTPException(
                status_code=500,
                detail="PIPECAT_CLOUD_API_KEY environment variable is not set",
            )

        headers = {
            "Authorization": f"Bearer {pcc_api_key}",
            "Content-Type": "application/json",
        }

        url = f"https://api.pipecat.daily.co/v1/public/{agent_name}/start"
        logger.debug(f"Making API call to Pipecat Cloud: {url}")

        try:
            response = requests.post(url, json=payload, headers=headers)
            response.raise_for_status()
            response_data = response.json()
            logger.debug(f"Pipecat Cloud response: {response_data}")
            return JSONResponse(
                {
                    "status": "success",
                    "data": response_data,
                    "room_properties": daily_room_properties,
                }
            )
        except requests.exceptions.HTTPError as e:
            status_code = e.response.status_code
            error_detail = e.response.json() if e.response.content else str(e)
            logger.error(f"HTTP error: {error_detail}")
            raise HTTPException(status_code=status_code, detail=error_detail)
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))


# ----------------- API Endpoints ----------------- #


@app.get("/")
async def read_root():
    """Root endpoint with server mode information."""
    return {
        "message": "Unified Pipecat Webhook Server",
        "mode": SERVER_MODE.upper(),
        "version": "1.0",
    }


@app.post("/start")
async def handle_webhook_request(request: Request) -> JSONResponse:
    """Main webhook endpoint that handles both local and cloud modes."""
    logger.info(f"Received webhook request (mode: {SERVER_MODE.upper()})")

    # Get raw request data
    raw_body = await request.body()
    raw_body_str = raw_body.decode()
    logger.debug(f"Raw body: {raw_body_str}")
    logger.debug(f"Headers: {dict(request.headers)}")

    try:
        # Parse JSON data
        data = json.loads(raw_body_str)

        # Handle test requests
        if "test" in data:
            logger.debug("Test request received")
            return JSONResponse({"test": True, "mode": SERVER_MODE})

        # Validate HMAC signature if in cloud mode
        if not IS_LOCAL:
            if not validate_hmac_signature(raw_body_str, dict(request.headers)):
                raise HTTPException(status_code=401, detail="Invalid signature")

        # Validate required fields
        required_fields = ["From", "To", "callId", "callDomain"]
        if not all(key in data for key in required_fields):
            raise HTTPException(
                status_code=400,
                detail=f"Missing required properties: {required_fields}",
            )

        # Route to appropriate handler based on mode
        if IS_LOCAL:
            return await handle_request(data, request.app.state.session)
        else:  # cloud mode
            return await handle_request(data)

    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON: {e}")
        raise HTTPException(status_code=400, detail="Invalid JSON format")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Server error: {str(e)}")


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "mode": SERVER_MODE.upper(),
        "timestamp": int(time.time()),
    }


@app.get("/mode")
async def get_mode():
    """Get current server mode."""
    return {
        "mode": SERVER_MODE.upper(),
        "description": "LOCAL: Creates rooms locally and spawns bot processes | CLOUD: Uses Pipecat Cloud API",
    }


# ----------------- Main ----------------- #

if __name__ == "__main__":
    port = int(os.getenv("PORT", "7860"))
    logger.info(f"Starting Unified Pipecat Webhook Server on port {port}")
    logger.info(f"Server mode: {SERVER_MODE.upper()} (IS_LOCAL={IS_LOCAL})")

    try:
        if IS_LOCAL:
            uvicorn.run("unified-server:app", host="0.0.0.0", port=port, reload=True)
        else:
            uvicorn.run(app, host="0.0.0.0", port=port)
    except KeyboardInterrupt:
        logger.info("Server stopped manually")
