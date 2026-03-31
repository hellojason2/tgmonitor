'use client'

import { format, subDays } from 'date-fns'

interface DateRangePickerProps {
  startDate: string
  endDate: string
  onStartDateChange: (date: string) => void
  onEndDateChange: (date: string) => void
}

export default function DateRangePicker({
  startDate,
  endDate,
  onStartDateChange,
  onEndDateChange,
}: DateRangePickerProps) {
  function handlePresetDays(days: number) {
    const end = new Date()
    const start = subDays(end, days)
    onEndDateChange(format(end, 'yyyy-MM-dd'))
    onStartDateChange(format(start, 'yyyy-MM-dd'))
  }

  return (
    <div className="flex flex-wrap items-center gap-4">
      <div className="flex items-center gap-2">
        <label className="text-sm font-medium text-foreground">From:</label>
        <input
          type="date"
          value={startDate}
          onChange={(e) => onStartDateChange(e.target.value)}
          className="rounded-md border border-input bg-background px-3 py-1.5 text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-ring"
        />
      </div>

      <div className="flex items-center gap-2">
        <label className="text-sm font-medium text-foreground">To:</label>
        <input
          type="date"
          value={endDate}
          onChange={(e) => onEndDateChange(e.target.value)}
          className="rounded-md border border-input bg-background px-3 py-1.5 text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-ring"
        />
      </div>

      <div className="flex items-center gap-2">
        <span className="text-sm text-muted-foreground">Presets:</span>
        <button
          onClick={() => handlePresetDays(1)}
          className="rounded-md border border-border bg-card px-2 py-1 text-xs text-foreground hover:bg-secondary"
        >
          Today
        </button>
        <button
          onClick={() => handlePresetDays(7)}
          className="rounded-md border border-border bg-card px-2 py-1 text-xs text-foreground hover:bg-secondary"
        >
          7 Days
        </button>
        <button
          onClick={() => handlePresetDays(30)}
          className="rounded-md border border-border bg-card px-2 py-1 text-xs text-foreground hover:bg-secondary"
        >
          30 Days
        </button>
      </div>
    </div>
  )
}
