import { NextResponse, NextRequest } from 'next/server';

// Determine if we're running locally or in production
const IS_LOCAL = !!process.env.NEXT_PUBLIC_API_BASE_URL?.includes('localhost');

// Get the API base URL - either local development or Pipecat Cloud
const API_BASE_URL = IS_LOCAL
  ? process.env.NEXT_PUBLIC_API_BASE_URL // e.g., http://localhost:7860
  : `https://api.pipecat.daily.co/v1/public/${process.env.AGENT_NAME}`;

console.log(
  'Using API base URL:',
  API_BASE_URL,
  IS_LOCAL ? '(LOCAL)' : '(CLOUD)'
);

export async function POST(request: NextRequest) {
  try {
    // const { MY_CUSTOM_DATA } = await request.json();

    // Prepare headers - only add Authorization for cloud
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
    };

    // Only add auth header for Pipecat Cloud
    if (!IS_LOCAL && process.env.PIPECAT_CLOUD_API_KEY) {
      headers.Authorization = `Bearer ${process.env.PIPECAT_CLOUD_API_KEY}`;
    }

    const response = await fetch(`${API_BASE_URL}/connect`, {
      method: 'POST',
      headers,
      body: JSON.stringify({
        // Create Daily room
        createDailyRoom: true,
        // Optionally set Daily room properties
        dailyRoomProperties: { start_video_off: true },
        // Optionally pass custom data to the bot
        // body: { MY_CUSTOM_DATA },
      }),
    });

    if (!response.ok) {
      const errorText = await response.text();
      console.error(`API error (${response.status}):`, errorText);
      throw new Error(`API responded with status: ${response.status}`);
    }

    const data = await response.json();

    // Both local and cloud return the same format
    return NextResponse.json({
      room_url: data.room_url,
      token: data.token,
    });
  } catch (error) {
    console.error('API error:', error);
    return NextResponse.json(
      { error: 'Failed to start agent' },
      { status: 500 }
    );
  }
}
