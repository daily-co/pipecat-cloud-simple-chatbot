'use client';

import { PipecatClient } from '@pipecat-ai/client-js';
import { DailyTransport } from '@pipecat-ai/daily-transport';
import { PipecatClientProvider } from '@pipecat-ai/client-react';
import { PropsWithChildren, useEffect, useState } from 'react';

// const MY_CUSTOM_DATA = { foo: 'bar' };

export function PipecatProvider({ children }: PropsWithChildren) {
  const [client, setClient] = useState<PipecatClient | null>(null);

  useEffect(() => {
    console.log('Setting up Transport and Client');
    const transport = new DailyTransport();

    const pipecatClient = new PipecatClient({
      transport,
      enableMic: true,
      enableCam: false,
    });

    setClient(pipecatClient);
  }, []);

  if (!client) {
    return null;
  }

  return (
    <PipecatClientProvider client={client}>{children}</PipecatClientProvider>
  );
}
