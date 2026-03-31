'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { removeAuthToken } from '@/lib/auth'
import { useRouter } from 'next/navigation'

export default function NavBar() {
  const pathname = usePathname()
  const router = useRouter()

  function handleLogout() {
    removeAuthToken()
    document.cookie = 'auth_token=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT'
    router.replace('/login')
  }

  const navItems = [
    { href: '/dashboard', label: 'Employees' },
    { href: '/dashboard/alerts', label: 'Alerts' },
  ]

  return (
    <nav className="border-b border-border bg-card">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="flex h-16 items-center justify-between">
          <div className="flex items-center">
            <Link href="/dashboard" className="text-xl font-bold text-foreground">
              TGmonitor
            </Link>
            <div className="ml-10 flex space-x-4">
              {navItems.map((item) => (
                <Link
                  key={item.href}
                  href={item.href}
                  className={`rounded-md px-3 py-2 text-sm font-medium transition-colors ${
                    pathname === item.href
                      ? 'bg-primary text-primary-foreground'
                      : 'text-muted-foreground hover:bg-secondary hover:text-foreground'
                  }`}
                >
                  {item.label}
                </Link>
              ))}
            </div>
          </div>
          <button
            onClick={handleLogout}
            className="rounded-md px-3 py-2 text-sm font-medium text-muted-foreground hover:bg-secondary hover:text-foreground"
          >
            Logout
          </button>
        </div>
      </div>
    </nav>
  )
}
