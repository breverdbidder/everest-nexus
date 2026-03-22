import type { Metadata } from 'next'
import './globals.css'
import Sidebar from '@/components/Sidebar'

export const metadata: Metadata = {
  title: 'Everest Nexus',
  description: 'Ecosystem Intelligence Platform',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body style={{ background: '#020617' }}>
        <Sidebar />
        <main className="ml-56 min-h-screen" style={{ background: '#020617' }}>
          {children}
        </main>
      </body>
    </html>
  )
}
