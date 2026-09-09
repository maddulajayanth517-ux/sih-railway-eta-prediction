import type { Metadata } from 'next';
import React from 'react';

export const metadata: Metadata = {
  title: 'Station Master Command Center',
  description: 'Railway ETA monitoring and platform management dashboard',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
