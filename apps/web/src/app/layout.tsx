import type { Metadata, Viewport } from 'next';
import { Inter, JetBrains_Mono } from 'next/font/google';
import '@/styles/globals.css';
import { Providers } from '@/components/providers';

const inter = Inter({
  subsets: ['latin'],
  variable: '--font-sans',
  display: 'swap',
});

const jetbrainsMono = JetBrains_Mono({
  subsets: ['latin'],
  variable: '--font-mono',
  display: 'swap',
});

export const metadata: Metadata = {
  title: {
    default: 'SOVRN - AI Website Builder',
    template: '%s | SOVRN',
  },
  description:
    '100% offline, self-hosted AI website builder. Generate production-ready websites with cultural intelligence and business optimization.',
  keywords: [
    'AI website builder',
    'self-hosted',
    'offline',
    'website generator',
    'Next.js',
    'business intelligence',
  ],
  authors: [{ name: 'SOVRN' }],
  creator: 'SOVRN',
  openGraph: {
    type: 'website',
    locale: 'en_US',
    title: 'SOVRN - AI Website Builder',
    description: '100% offline, self-hosted AI website builder',
    siteName: 'SOVRN',
  },
  twitter: {
    card: 'summary_large_image',
    title: 'SOVRN - AI Website Builder',
    description: '100% offline, self-hosted AI website builder',
  },
  robots: {
    index: true,
    follow: true,
  },
};

export const viewport: Viewport = {
  width: 'device-width',
  initialScale: 1,
  themeColor: [
    { media: '(prefers-color-scheme: light)', color: '#ffffff' },
    { media: '(prefers-color-scheme: dark)', color: '#0c0a09' },
  ],
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className={`${inter.variable} ${jetbrainsMono.variable} font-sans antialiased`}>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
