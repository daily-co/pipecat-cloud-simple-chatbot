"use client";

import { RTVIClient } from "@pipecat-ai/client-js";
import { DailyTransport } from "@pipecat-ai/daily-transport";
import { RTVIClientProvider } from "@pipecat-ai/client-react";
import { PropsWithChildren, useEffect, useMemo, useState } from "react";

// Get the API base URL from environment variables
// Default to "/api" if not specified
// "/api" is the default for Next.js API routes and used
// for the Pipecat Cloud deployed agent
const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || "/api";

console.log("Using API base URL:", API_BASE_URL);

export function RTVIProvider({ children }: PropsWithChildren) {
  const [client, setClient] = useState<RTVIClient | null>(null);

  const MY_CUSTOM_DATA = {
    location:
      "rtsp://rtspstream:9bGdZ6NKfRXnMbFAg71al@zephyr.rtsp.stream/people",
    prompt:
      "Are there people in the bottom right corner of the image? Only answer with YES or NO.",
  };

  // Get location and prompt from URL if present
  const customData = useMemo(() => {
    if (typeof window === "undefined") return MY_CUSTOM_DATA;
    const params = new URLSearchParams(window.location.search);
    return {
      location: params.get("location") || MY_CUSTOM_DATA.location,
      prompt: params.get("prompt") || MY_CUSTOM_DATA.prompt,
    };
  }, []);

  useEffect(() => {
    console.log("Setting up Transport and Client");
    const transport = new DailyTransport();

    const rtviClient = new RTVIClient({
      transport,
      params: {
        baseUrl: API_BASE_URL,
        endpoints: {
          connect: "/connect",
        },
        requestData: customData,
      },
      enableMic: true,
      enableCam: false,
    });

    setClient(rtviClient);
  }, [customData]);

  if (!client) {
    return null;
  }

  return <RTVIClientProvider client={client}>{children}</RTVIClientProvider>;
}
