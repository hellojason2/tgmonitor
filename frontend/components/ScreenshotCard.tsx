'use client'

import { useState } from 'react'
import type { Screenshot } from '@/lib/api'
import { getScreenshotUrl } from '@/lib/api'

interface ScreenshotCardProps {
  screenshot: Screenshot
}

export default function ScreenshotCard({ screenshot }: ScreenshotCardProps) {
  const [imageError, setImageError] = useState(false)
  const screenshotUrl = getScreenshotUrl(screenshot.file_path)

  const riskLevel =
    screenshot.analysis_result?.risk_score ?? 0
  const riskColor =
    riskLevel >= 0.7
      ? 'border-destructive'
      : riskLevel >= 0.4
      ? 'border-yellow-500'
      : 'border-border'

  return (
    <div
      className={`rounded-lg border bg-card overflow-hidden transition-colors hover:border-primary/50 ${riskColor}`}
    >
      <div className="aspect-video w-full bg-muted">
        {!imageError && screenshotUrl ? (
          <img
            src={screenshotUrl}
            alt={`Screenshot at ${new Date(screenshot.captured_at).toLocaleTimeString()}`}
            className="h-full w-full object-cover"
            onError={() => setImageError(true)}
          />
        ) : (
          <div className="flex h-full w-full items-center justify-center bg-muted text-muted-foreground">
            <svg
              className="h-8 w-8"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={1.5}
                d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"
              />
            </svg>
          </div>
        )}
      </div>

      <div className="p-3">
        <div className="flex items-center justify-between">
          <p className="text-xs text-muted-foreground">
            {new Date(screenshot.captured_at).toLocaleTimeString()}
          </p>
          {screenshot.analysis_result && (
            <span
              className={`rounded-full px-2 py-0.5 text-xs ${
                riskLevel >= 0.7
                  ? 'bg-destructive/20 text-destructive'
                  : riskLevel >= 0.4
                  ? 'bg-yellow-500/20 text-yellow-500'
                  : 'bg-green-500/20 text-green-500'
              }`}
            >
              Risk: {Math.round(riskLevel * 100)}%
            </span>
          )}
        </div>

        <p className="mt-2 text-sm font-medium text-foreground truncate">
          {screenshot.app_name}
        </p>
        <p className="mt-0.5 text-xs text-muted-foreground truncate">
          {screenshot.window_title}
        </p>

        {screenshot.analysis_result && (
          <p className="mt-2 text-xs text-foreground/80 leading-relaxed">
            {screenshot.analysis_result.caption}
          </p>
        )}

        {screenshot.analysis_status === 'pending' && (
          <p className="mt-2 text-xs text-muted-foreground italic">
            Analysis pending...
          </p>
        )}
      </div>
    </div>
  )
}
