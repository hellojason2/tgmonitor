'use client'

import { useState } from 'react'
import Link from 'next/link'
import type { Alert } from '@/lib/api'
import { acknowledgeAlert as ackAlert } from '@/lib/api'

interface AlertRowProps {
  alert: Alert
  onAcknowledge?: (alertId: string) => void
}

export default function AlertRow({ alert, onAcknowledge }: AlertRowProps) {
  const [isAcknowledging, setIsAcknowledging] = useState(false)
  const [isAcknowledged, setIsAcknowledged] = useState(alert.acknowledged)

  async function handleAcknowledge() {
    if (isAcknowledging || isAcknowledged) return
    setIsAcknowledging(true)
    try {
      await ackAlert(alert.id)
      setIsAcknowledged(true)
      onAcknowledge?.(alert.id)
    } catch (error) {
      console.error('Failed to acknowledge alert:', error)
    } finally {
      setIsAcknowledging(false)
    }
  }

  const riskLevel = alert.risk_score
  const riskColor =
    riskLevel >= 0.8
      ? 'bg-destructive'
      : riskLevel >= 0.6
      ? 'bg-orange-500'
      : 'bg-yellow-500'

  return (
    <div className="flex items-start gap-4 rounded-lg border border-destructive/50 bg-destructive/10 p-4">
      <div className={`mt-1 h-3 w-3 flex-shrink-0 rounded-full ${riskColor}`} />

      <div className="flex-1 min-w-0">
        <div className="flex items-start justify-between gap-2">
          <div>
            {alert.employee && (
              <Link
                href={`/dashboard/employee/${alert.employee.id}`}
                className="font-medium text-foreground hover:text-primary"
              >
                {alert.employee.name}
              </Link>
            )}
            <span className="ml-2 text-xs text-muted-foreground">
              {alert.alert_type}
            </span>
          </div>
          <span className="flex-shrink-0 text-xs text-muted-foreground">
            {new Date(alert.created_at).toLocaleString()}
          </span>
        </div>

        <p className="mt-2 text-sm text-foreground">{alert.caption}</p>

        <div className="mt-2 flex items-center gap-2">
          <span className="text-xs text-muted-foreground">
            Risk Score: {Math.round(riskLevel * 100)}%
          </span>
        </div>

        {alert.screenshot && (
          <Link
            href={`/dashboard/employee/${alert.screenshot.employee_id}`}
            className="mt-2 inline-block text-xs text-primary hover:underline"
          >
            View screenshots
          </Link>
        )}
      </div>

      {!isAcknowledged && (
        <button
          onClick={handleAcknowledge}
          disabled={isAcknowledging}
          className="flex-shrink-0 rounded-md border border-border bg-card px-3 py-1.5 text-sm font-medium text-foreground hover:bg-secondary disabled:opacity-50"
        >
          {isAcknowledging ? 'Acknowledging...' : 'Acknowledge'}
        </button>
      )}

      {isAcknowledged && (
        <span className="flex-shrink-0 rounded-md bg-green-500/20 px-3 py-1.5 text-sm font-medium text-green-500">
          Acknowledged
        </span>
      )}
    </div>
  )
}
