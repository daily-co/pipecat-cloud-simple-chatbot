import { useRef, useCallback, useState } from "react";
import {
  Participant,
  RTVIEvent,
  TransportState,
  TranscriptData,
  BotLLMTextData,
  RTVIMessage,
} from "@pipecat-ai/client-js";
import { useRTVIClient, useRTVIClientEvent } from "@pipecat-ai/client-react";
// import './DebugDisplay.css';

export function ConfigDislay() {
  const debugLogRef = useRef<HTMLDivElement>(null);
  const client = useRTVIClient();
  const [isDoorOpen, setIsDoorOpen] = useState("NO");

  const log = useCallback((message: string) => {
    if (!debugLogRef.current) return;

    const entry = document.createElement("div");
    entry.textContent = `${new Date().toISOString()} - ${message}`;

    // Add styling based on message type
    if (message.startsWith("User: ")) {
      entry.style.color = "#2196F3"; // blue for user
    } else if (message.startsWith("Bot: ")) {
      entry.style.color = "#4CAF50"; // green for bot
    }

    debugLogRef.current.appendChild(entry);
    debugLogRef.current.scrollTop = debugLogRef.current.scrollHeight;
  }, []);

  // Log transport state changes
  useRTVIClientEvent(
    RTVIEvent.TransportStateChanged,
    useCallback(
      (state: TransportState) => {
        log(`Transport state changed: ${state}`);
      },
      [log]
    )
  );

  // Log bot connection events
  useRTVIClientEvent(
    RTVIEvent.BotConnected,
    useCallback(
      (participant?: Participant) => {
        log(`Bot connected: ${JSON.stringify(participant)}`);
      },
      [log]
    )
  );

  useRTVIClientEvent(
    RTVIEvent.BotDisconnected,
    useCallback(
      (participant?: Participant) => {
        log(`Bot disconnected: ${JSON.stringify(participant)}`);
      },
      [log]
    )
  );

  // Log track events
  useRTVIClientEvent(
    RTVIEvent.TrackStarted,
    useCallback(
      (track: MediaStreamTrack, participant?: Participant) => {
        log(
          `Track started: ${track.kind} from ${participant?.name || "unknown"}`
        );
      },
      [log]
    )
  );

  useRTVIClientEvent(
    RTVIEvent.TrackStopped,
    useCallback(
      (track: MediaStreamTrack, participant?: Participant) => {
        log(
          `Track stopped: ${track.kind} from ${participant?.name || "unknown"}`
        );
      },
      [log]
    )
  );

  // Log bot ready state and check tracks
  useRTVIClientEvent(
    RTVIEvent.BotReady,
    useCallback(() => {
      log(`Bot ready`);

      if (!client) return;

      const tracks = client.tracks();
      log(
        `Available tracks: ${JSON.stringify({
          local: {
            audio: !!tracks.local.audio,
            video: !!tracks.local.video,
          },
          bot: {
            audio: !!tracks.bot?.audio,
            video: !!tracks.bot?.video,
          },
        })}`
      );
    }, [client, log])
  );

  // Log transcripts
  useRTVIClientEvent(
    RTVIEvent.UserTranscript,
    useCallback(
      (data: TranscriptData) => {
        // Only log final transcripts
        if (data.final) {
          log(`User: ${data.text}`);
        }
      },
      [log]
    )
  );

  useRTVIClientEvent(
    RTVIEvent.BotTranscript,
    useCallback(
      (data: BotLLMTextData) => {
        log(`Bot: ${data.text}`);
      },
      [log]
    )
  );

  useRTVIClientEvent(
    RTVIEvent.ServerMessage,
    useCallback(
      (data: unknown) => {
        setIsDoorOpen(String(data));
      },
      [setIsDoorOpen]
    )
  );

  return (
    <div
      className="config-panel"
      style={{
        background: "#f8fafc",
        borderRadius: "12px",
        boxShadow: "0 2px 12px rgba(0,0,0,0.07)",
        padding: "2rem",
        maxWidth: 480,
        margin: "2rem auto",
        border: "1px solid #e2e8f0",
        display: "flex",
        flexDirection: "column",
        gap: "1.2rem",
      }}
    >
      <h3
        style={{
          margin: 0,
          fontSize: "1.3rem",
          fontWeight: 600,
          color: "#1e293b",
          letterSpacing: "0.01em",
        }}
      >
        Is the door open? {isDoorOpen}
      </h3>
    </div>
  );
}
