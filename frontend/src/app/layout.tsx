import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: 'Team Dereve - Coaching IA',
  description: 'Plateforme de coaching IA avec Max, Forge et Myriam',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="fr">
      <body>{children}</body>
    </html>
  )
}
