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
from PIL import Image
from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.frames.frames import (
    BotStartedSpeakingFrame,
    BotStoppedSpeakingFrame,
    Frame,
    OutputImageRawFrame,
    SpriteFrame,
)
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineParams, PipelineTask
from pipecat.processors.aggregators.openai_llm_context import OpenAILLMContext
from pipecat.processors.frame_processor import FrameDirection, FrameProcessor
from pipecat.processors.frameworks.rtvi import RTVIConfig, RTVIObserver, RTVIProcessor
from pipecat.services.azure.tts import AzureTTSService
from pipecat.services.openai.llm import OpenAILLMService
from pipecat.transports.services.daily import (
    DailyParams,
    DailyTranscriptionSettings,
    DailyTransport,
)
from pipecatcloud.agent import DailySessionArguments

load_dotenv(override=True)

# Check if we're running locally
IS_LOCAL_RUN = os.environ.get("LOCAL_RUN", "0") == "1"

# Logger for local dev
# logger.add(sys.stderr, level="DEBUG")

sprites = []
script_dir = os.path.dirname(__file__)

# Load sequential animation frames
for i in range(1, 26):
    # Build the full path to the image file
    full_path = os.path.join(script_dir, f"assets/robot0{i}.png")
    # Get the filename without the extension to use as the dictionary key
    # Open the image and convert it to bytes
    with Image.open(full_path) as img:
        sprites.append(
            OutputImageRawFrame(image=img.tobytes(), size=img.size, format=img.format)
        )

# Create a smooth animation by adding reversed frames
flipped = sprites[::-1]
sprites.extend(flipped)

# Define static and animated states
quiet_frame = sprites[0]  # Static frame for when bot is listening
talking_frame = SpriteFrame(
    images=sprites
)  # Animation sequence for when bot is talking


class TalkingAnimation(FrameProcessor):
    """Manages the bot's visual animation states.

    Switches between static (listening) and animated (talking) states based on
    the bot's current speaking status.
    """

    def __init__(self):
        super().__init__()
        self._is_talking = False

    async def process_frame(self, frame: Frame, direction: FrameDirection):
        """Process incoming frames and update animation state.

        Args:
            frame: The incoming frame to process
            direction: The direction of frame flow in the pipeline
        """
        await super().process_frame(frame, direction)

        # Switch to talking animation when bot starts speaking
        if isinstance(frame, BotStartedSpeakingFrame):
            if not self._is_talking:
                await self.push_frame(talking_frame)
                self._is_talking = True
        # Return to static frame when bot stops speaking
        elif isinstance(frame, BotStoppedSpeakingFrame):
            await self.push_frame(quiet_frame)
            self._is_talking = False

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
            vad_analyzer=SileroVADAnalyzer(),
            transcription_enabled=True,
            #
            # Chinese
            #
            transcription_settings=DailyTranscriptionSettings(
                language="zh-TW", model="nova-2-general"
            ),
        ),
    )

    # Initialize text-to-speech service
    tts = AzureTTSService(
        api_key=os.getenv("AZURE_SPEECH_API_KEY"),
        region=os.getenv("AZURE_SPEECH_REGION"),
        language="zh-TW",
        voice="zh-TW-YunJheNeural",
    )

    # tts = ElevenLabsTTSService(
    #     api_key=os.getenv("ELEVENLABS_API_KEY"),
    #     # English
    #     voice_id="cgSgspJ2msm6clMCkdW9",
    #     # Chinese
    #     # voice_id="fQj4gJSexpu8RDE2Ii5m",
    #     # model="eleven_turbo_v2_5",
    # )

    # Initialize LLM service
    llm = OpenAILLMService(api_key=os.getenv("OPENAI_API_KEY"), model="gpt-4o")

    # Set up initial messages for the bot
    messages = [
        {
            "role": "system",
            #
            # Chinese
            #
            "content": """
            你是一位有耐心，溫柔又熱情的漢語老師。
            先和學習者講講我自己的情況。如果學習者使用漢語有偏誤時，你需要糾正他，並鼓勵學習者。
            請你先和學習者介紹一下自己，只能使用初級的詞彙，
            例如：你好，我是你的漢語老師，我叫小明。我喜歡和朋友聊天，你呢？
            """,
        },
    ]

    # Set up conversation context and management
    # The context_aggregator will automatically collect conversation context
    # Pass your initial messages and tools to the context to initialize the context
    context = OpenAILLMContext(messages)
    context_aggregator = llm.create_context_aggregator(context)

    ta = TalkingAnimation()

    # RTVI events for Pipecat client UI
    rtvi = RTVIProcessor(config=RTVIConfig(config=[]))

    # Add your processors to the pipeline
    pipeline = Pipeline(
        [
            transport.input(),
            rtvi,
            context_aggregator.user(),
            llm,
            tts,
            ta,
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
        await task.queue_frame(quiet_frame)
        # Capture the first participant's transcription
        await transport.capture_participant_transcription(participant["id"])

    @transport.event_handler("on_participant_left")
    async def on_participant_left(transport, participant, reason):
        logger.debug(f"Participant left: {participant}")
        # Cancel the PipelineTask to stop processing
        await task.cancel()

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
