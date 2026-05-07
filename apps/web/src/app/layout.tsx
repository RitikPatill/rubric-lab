import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: 'RubricLab',
  description: 'Evaluation harness for AI agents',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  )
}
