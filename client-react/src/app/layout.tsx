import './globals.css';
import { PipecatProvider } from '@/providers/PipecatProvider';

export const metadata = {
  title: 'Pipecat React Client',
  description: 'Pipecat RTVI Client using Next.js',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>
        <PipecatProvider>{children}</PipecatProvider>
      </body>
    </html>
  );
}
