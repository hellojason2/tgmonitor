'use client'

import useSWR from 'swr'
import { fetchAlerts } from '@/lib/api'
import AlertRow from '@/components/AlertRow'
import type { Alert } from '@/lib/api'

const REFRESH_INTERVAL = 60000

export default function AlertsPage() {
  const { data: alerts, error, isLoading, mutate } = useSWR<Alert[]>(
    'alerts',
    () => fetchAlerts(false),
    {
      refreshInterval: REFRESH_INTERVAL,
      revalidateOnFocus: true,
    }
  )

  function handleAcknowledge(alertId: string) {
    mutate(
      (current) => current?.filter((a) => a.id !== alertId),
      false
    )
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="animate-pulse text-muted-foreground">
          Loading alerts...
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="rounded-lg border border-destructive bg-destructive/10 p-4 text-destructive">
        Failed to load alerts. Please check your connection.
      </div>
    )
  }

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-foreground">Alerts</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          High-risk activities flagged for review
        </p>
      </div>

      {alerts && alerts.length > 0 ? (
        <div className="space-y-4">
          {alerts.map((alert) => (
            <AlertRow
              key={alert.id}
              alert={alert}
              onAcknowledge={handleAcknowledge}
            />
          ))}
        </div>
      ) : (
        <div className="rounded-lg border border-border bg-card p-8 text-center">
          <p className="text-muted-foreground">No unacknowledged alerts.</p>
        </div>
      )}

      <div className="mt-4 text-xs text-muted-foreground">
        Auto-refresh every 60 seconds
      </div>
    </div>
  )
}
