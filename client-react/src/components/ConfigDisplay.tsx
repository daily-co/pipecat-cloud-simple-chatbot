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
  const [prompt, setPrompt] = useState(
    "Is this door open? Only answer with YES or NO. (This does not work yet.)"
  );

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
        Change Prompt
      </h3>
      <textarea
        value={prompt}
        onChange={(e) => setPrompt(e.target.value)}
        style={{
          minHeight: 80,
          fontSize: "1rem",
          borderRadius: 8,
          border: "1px solid #cbd5e1",
          padding: "0.75rem 1rem",
          background: "#fff",
          color: "#334155",
          resize: "vertical",
          outline: "none",
          boxShadow: "0 1px 2px rgba(0,0,0,0.03)",
          transition: "border 0.2s",
        }}
        placeholder="Type your prompt here..."
      />
      <button
        onClick={() => {
          if (!client) {
            console.error("RTVI client is not initialized");
            return;
          }
          const message: RTVIMessage = {
            id: "custom-prompt",
            type: "custom",
            label: "Change Prompt",
            data: {
              prompt,
            },
          };
          client.sendMessage(message);
        }}
        style={{
          background: "linear-gradient(90deg, #38bdf8 0%, #6366f1 100%)",
          color: "#fff",
          border: "none",
          borderRadius: 8,
          padding: "0.7rem 1.5rem",
          fontWeight: 600,
          fontSize: "1rem",
          cursor: "pointer",
          boxShadow: "0 1px 4px rgba(56,189,248,0.08)",
          transition: "background 0.2s, box-shadow 0.2s",
        }}
        onMouseOver={(e) =>
          (e.currentTarget.style.background =
            "linear-gradient(90deg, #6366f1 0%, #38bdf8 100%)")
        }
        onMouseOut={(e) =>
          (e.currentTarget.style.background =
            "linear-gradient(90deg, #38bdf8 0%, #6366f1 100%)")
        }
      >
        Change
      </button>
    </div>
  );
}
