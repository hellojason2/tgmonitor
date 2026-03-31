import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: 'TGmonitor - Employee Monitoring Dashboard',
  description: 'Employee monitoring and activity tracking dashboard',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-background antialiased">{children}</body>
    </html>
  )
}
