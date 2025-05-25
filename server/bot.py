#
# Copyright (c) 2024–2025, Daily
#
# SPDX-License-Identifier: BSD 2-Clause License
#

"""OpenAI Bot Implementation.

This module implements a chatbot using OpenAI's GPT-4 model for natural language
processing. It includes:
- Real-time audio/video interaction through Daily
- Animated robot avatar
- Text-to-speech using ElevenLabs
- Support for both English and Spanish

The bot runs as part of a pipeline that processes audio/video frames and manages
the conversation flow.
"""

import os

from dotenv import load_dotenv
from loguru import logger
from pipecat.frames.frames import (
    EndFrame,
    Frame,
    InputImageRawFrame,
    OutputImageRawFrame,
    TextFrame,
)
from pipecat.observers.loggers.debug_log_observer import DebugLogObserver, FrameEndpoint
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineTask
from pipecat.processors.aggregators.vision_image_frame import VisionImageFrameAggregator
from pipecat.processors.frame_processor import FrameDirection, FrameProcessor
from pipecat.processors.frameworks.rtvi import (
    RTVIConfig,
    RTVIObserver,
    RTVIProcessor,
    RTVIServerMessageFrame,
)
from pipecat.processors.gstreamer.pipeline_source import GStreamerPipelineSource
from pipecat.services.moondream.vision import MoondreamService
from pipecat.transports.services.daily import DailyParams, DailyTransport
from pipecatcloud.agent import DailySessionArguments

load_dotenv(override=True)

# Check if we're running locally
IS_LOCAL_RUN = os.environ.get("LOCAL_RUN", "0") == "1"


class AlertProcessor(FrameProcessor):
    def __init__(self):
        super().__init__()

    async def process_frame(self, frame: Frame, direction: FrameDirection):
        await super().process_frame(frame, direction)

        if isinstance(frame, TextFrame):
            text = frame.text.strip().upper()
            message_frame = RTVIServerMessageFrame(data=text)
            await self.push_frame(message_frame)

        await self.push_frame(frame, direction)


class UserImageRequester(FrameProcessor):
    def __init__(self, prompt: str):
        super().__init__()
        self._prompt = prompt

    async def process_frame(self, frame: Frame, direction: FrameDirection):
        await super().process_frame(frame, direction)

        if isinstance(frame, OutputImageRawFrame):
            await self.push_frame(frame)
            # logger.info(f"UserImageRequester received image frame with size: {frame.size}")
            text_frame = TextFrame(self._prompt)
            await self.push_frame(text_frame)
            input_frame = InputImageRawFrame(
                image=frame.image,
                size=frame.size,
                format=frame.format,
            )
            await self.push_frame(input_frame)
        else:
            await self.push_frame(frame, direction)


async def main(room_url: str, token: str, config: dict):
    """Main bot execution function.

    Sets up and runs the bot pipeline including:
    - Daily video transport
    - Speech-to-text and text-to-speech services
    - Language model integration
    - Animation processing
    - RTVI event handling
    """
    default_config = {
        "location": "rtsp://rtspstream:9bGdZ6NKfRXnMbFAg71al@zephyr.rtsp.stream/people",
        "prompt": "Are there people in the bottom right corner of the image? Only answer with YES or NO.",
    }
    # Use default_config if config is empty
    if not config:
        config = default_config

    logger.info(f"Body: {config}")

    transport = DailyTransport(
        room_url,
        token,
        "Simple Chatbot",
        DailyParams(
            audio_in_enabled=True,  # Enable input audio for the bot
            audio_in_filter=None,
            audio_out_enabled=True,  # Enable output audio for the bot
            video_out_enabled=True,  # Enable the video output for the bot
            video_out_width=1024,  # Set the video output width
            video_out_height=576,  # Set the video output height
        ),
    )

    location = config.get("location", "")

    gst = GStreamerPipelineSource(
        pipeline=(f"rtspsrc location={location} ! decodebin ! autovideosink"),
        out_params=GStreamerPipelineSource.OutputParams(
            video_width=1280,
            video_height=720,
        ),
    )

    rtvi = RTVIProcessor(config=RTVIConfig(config=[]))

    # If you run into weird description, try with use_cpu=True
    moondream = MoondreamService()

    prompt = config.get("prompt", "")
    ir = UserImageRequester(prompt)
    va = VisionImageFrameAggregator()
    alert = AlertProcessor()

    pipeline = Pipeline(
        [
            gst,  # GStreamer file source
            rtvi,
            ir,
            va,
            moondream,
            alert,  # Send an email alert or something if the door is open
            transport.output(),  # Transport bot output
        ]
    )

    task = PipelineTask(
        pipeline,
        observers=[
            RTVIObserver(rtvi),
            DebugLogObserver(
                frame_types={
                    # TextFrame: None,
                    TextFrame: (MoondreamService, FrameEndpoint.SOURCE),
                    # InputImageRawFrame: None,
                    EndFrame: None,
                }
            ),
        ],
    )

    @rtvi.event_handler("on_client_ready")
    async def on_client_ready(rtvi):
        logger.info(f"Bot ready: {rtvi}")
        await rtvi.set_bot_ready()

    @transport.event_handler("on_client_connected")
    async def on_client_connected(transport, client):
        logger.info(f"Client connected: {client}")

    runner = PipelineRunner(handle_sigint=False)

    await runner.run(task)


async def bot(args: DailySessionArguments):
    """Main bot entry point compatible with Pipecat Cloud.

    Args:
        room_url: The Daily room URL
        token: The Daily room token
        body: The configuration object from the request body
        session_id: The session ID for logging
    """
    logger.info(f"Bot process initialized {args.room_url} {args.token} {args.body}")

    try:
        await main(args.room_url, args.token, args.body)
        logger.info("Bot process completed")
    except Exception as e:
        logger.exception(f"Error in bot process: {str(e)}")
        raise
