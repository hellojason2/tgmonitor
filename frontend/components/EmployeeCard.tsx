'use client'

import Link from 'next/link'
import type { Employee } from '@/lib/api'

interface EmployeeCardProps {
  employee: Employee
}

export default function EmployeeCard({ employee }: EmployeeCardProps) {
  const latestActivity = employee.latest_activity

  return (
    <Link href={`/dashboard/employee/${employee.id}`}>
      <div className="rounded-lg border border-border bg-card p-4 transition-colors hover:border-primary/50 hover:bg-secondary/50">
        <div className="flex items-start justify-between">
          <div className="flex-1">
            <h3 className="font-semibold text-foreground">{employee.name}</h3>
            {employee.location && (
              <p className="mt-1 text-sm text-muted-foreground">
                {employee.location}
              </p>
            )}
            {employee.devices && employee.devices.length > 0 && (
              <p className="mt-1 text-xs text-muted-foreground">
                {employee.devices.length} device(s)
              </p>
            )}
          </div>
          <div
            className={`h-2 w-2 rounded-full ${
              latestActivity ? 'bg-green-500' : 'bg-gray-500'
            }`}
          />
        </div>

        {latestActivity && (
          <div className="mt-4 border-t border-border pt-3">
            <p className="text-xs text-muted-foreground">Latest Activity</p>
            <p className="mt-1 truncate text-sm text-foreground">
              {latestActivity.app_name}
            </p>
            <p className="mt-0.5 truncate text-xs text-muted-foreground">
              {latestActivity.window_title}
            </p>
            <p className="mt-1 text-xs text-muted-foreground">
              {new Date(latestActivity.captured_at).toLocaleString()}
            </p>
          </div>
        )}

        {!latestActivity && (
          <div className="mt-4 border-t border-border pt-3">
            <p className="text-sm text-muted-foreground">No recent activity</p>
          </div>
        )}
      </div>
    </Link>
  )
}
