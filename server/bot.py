#
# Copyright (c) 2024–2025, Daily
#
# SPDX-License-Identifier: BSD 2-Clause License
#

"""OpenAI Bot Implementation."""

import os
import sys
from dataclasses import dataclass
from typing import Any, Dict

from dotenv import load_dotenv
from loguru import logger
from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.frames.frames import (
    BotInterruptionFrame,
    Frame,
    LLMMessagesFrame,
    SystemFrame,
)
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineParams, PipelineTask
from pipecat.processors.aggregators.openai_llm_context import (
    OpenAILLMContext,
    OpenAILLMContextFrame,
)
from pipecat.processors.frame_processor import FrameDirection, FrameProcessor
from pipecat.processors.frameworks.rtvi import RTVIConfig, RTVIObserver, RTVIProcessor
from pipecat.services.cartesia.tts import CartesiaTTSService
from pipecat.services.openai.llm import OpenAILLMService
from pipecat.transports.services.daily import DailyParams, DailyTransport
from pipecatcloud.agent import DailySessionArguments

load_dotenv(override=True)

# Check if we're running locally
IS_LOCAL_RUN = os.environ.get("LOCAL_RUN", "0") == "1"

# Logger for local dev
logger.add(sys.stderr, level="DEBUG")


@dataclass
class BotMuteFrame(SystemFrame):
    """System frame to mute/unmute the bot service."""

    mute: bool


class BotMuteProcessor(FrameProcessor):
    """Processor to mute the bot when a participant's mic is off."""

    def __init__(self):
        """Initialize the BotMuteProcessor."""
        super().__init__()
        self.is_muted = False

    async def process_frame(self, frame: Frame, direction) -> Frame:
        await super().process_frame(frame, direction)

        """Process the frame and mute the bot if necessary."""
        if isinstance(frame, BotMuteFrame):
            self.is_muted = frame.mute
            logger.info(f"Bot muted: {self.is_muted}")
            if self.is_muted:
                # If the bot is muted, we push a BotInterruptionFrame upstream
                await self.push_frame(BotInterruptionFrame(), FrameDirection.UPSTREAM)

        if (
            isinstance(frame, LLMMessagesFrame)
            or isinstance(frame, OpenAILLMContextFrame)
        ) and self.is_muted:
            # If the bot is muted, we skip processing LLM messages
            logger.info("Bot is muted, skipping LLM message processing.")
            return

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
    logger.info(f"Body: {config}")

    if not IS_LOCAL_RUN:
        from pipecat.audio.filters.krisp_filter import KrispFilter

    transport = DailyTransport(
        room_url,
        token,
        "Simple Chatbot",
        DailyParams(
            audio_in_enabled=True,  # Enable input audio for the bot
            audio_in_filter=None
            if IS_LOCAL_RUN
            else KrispFilter(),  # Only use Krisp in production
            audio_out_enabled=True,  # Enable output audio for the bot
            video_out_enabled=True,  # Enable the video output for the bot
            video_out_width=1024,  # Set the video output width
            video_out_height=576,  # Set the video output height
            transcription_enabled=True,  # Enable transcription for the user
            vad_analyzer=SileroVADAnalyzer(),  # Use the Silero VAD analyzer
        ),
    )

    # Initialize text-to-speech service
    tts = CartesiaTTSService(
        api_key=os.getenv("CARTESIA_API_KEY"),
        voice_id="c45bc5ec-dc68-4feb-8829-6e6b2748095d",  # Movieman
    )

    # Initialize LLM service
    llm = OpenAILLMService(api_key=os.getenv("OPENAI_API_KEY"), model="gpt-4o")

    # Set up initial messages for the bot
    messages = [
        {
            "role": "system",
            "content": "You are Chatbot, a friendly, helpful robot. Your goal is to demonstrate your capabilities in a succinct way. Your output will be converted to audio so don't include special characters in your answers. Respond to what the user said in a creative and helpful way, but keep your responses brief. Start by introducing yourself.",
        },
    ]

    # Set up conversation context and management
    # The context_aggregator will automatically collect conversation context
    # Pass your initial messages and tools to the context to initialize the context
    context = OpenAILLMContext(messages)
    context_aggregator = llm.create_context_aggregator(context)

    # RTVI events for Pipecat client UI
    rtvi = RTVIProcessor(config=RTVIConfig(config=[]))

    bot_mute_processor = BotMuteProcessor()

    # Add your processors to the pipeline
    pipeline = Pipeline(
        [
            transport.input(),
            rtvi,
            context_aggregator.user(),
            bot_mute_processor,
            llm,
            tts,
            transport.output(),
            context_aggregator.assistant(),
        ]
    )

    # Create a PipelineTask to manage the pipeline
    task = PipelineTask(
        pipeline,
        params=PipelineParams(
            allow_interruptions=True,
            enable_metrics=True,
            enable_usage_metrics=True,
        ),
        observers=[RTVIObserver(rtvi)],
    )

    @rtvi.event_handler("on_client_ready")
    async def on_client_ready(rtvi):
        # Notify the client that the bot is ready
        await rtvi.set_bot_ready()
        # Kick off the conversation by pushing a context frame to the pipeline
        await task.queue_frames([context_aggregator.user().get_context_frame()])

    @transport.event_handler("on_first_participant_joined")
    async def on_first_participant_joined(transport, participant):
        # Push a static frame to show the bot is listening
        # logger.debug(f"First participant joined: {participant}")
        participant_id = participant["id"]
        # Capture the first participant's transcription
        await transport.capture_participant_transcription(participant_id)

    @transport.event_handler("on_participant_joined")
    async def on_participant_joined(transport, participant):
        participant_count = transport.participant_counts()["present"]
        if participant_count == 3:
            await transport.capture_participant_transcription(participant["id"])

    @transport.event_handler("on_participant_left")
    async def on_participant_left(transport, participant, reason):
        logger.debug(f"Participant left: {participant}")
        participant_count = transport.participant_counts()["present"]
        if participant_count == 1:
            # Cancel the PipelineTask to stop processing
            await task.cancel()

    @transport.event_handler("on_participant_updated")
    async def on_participant_updated(transport, participant: Dict[str, Any]):
        # logger.info(f"Participant updated: {participant}")

        user_name = participant.get("info", {}).get("userName", "")

        if user_name != "manager":
            logger.debug(f"Skipping {user_name}")
            return

        mic_state = (
            participant.get("media", {}).get("microphone", {}).get("state", "off")
        )

        if mic_state == "off":
            # If the manager's mic is off we unmute the bot
            logger.info(
                f"Participant {participant['id']} microphone is off, unmute the bot."
            )
            # Push a BotInterruptionFrame to the pipeline to stop processing
            await task.queue_frame(BotMuteFrame(mute=False))
        else:
            logger.info(
                f"Participant {participant['id']} microphone is on, mute the bot."
            )
            # Push a BotInterruptionFrame to the pipeline to resume processing
            await task.queue_frame(BotMuteFrame(mute=True))

    runner = PipelineRunner()

    await runner.run(task)


async def bot(args: DailySessionArguments):
    """Main bot entry point compatible with Pipecat Cloud.

    Args:
        room_url: The Daily room URL
        token: The Daily room token
        body: The configuration object from the request body
        session_id: The session ID for logging
    """
    logger.info(f"Bot process initialized {args.room_url} {args.token}")

    try:
        await main(args.room_url, args.token, args.body)
        logger.info("Bot process completed")
    except Exception as e:
        logger.exception(f"Error in bot process: {str(e)}")
        raise
