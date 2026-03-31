'use client'

import { use } from 'react'
import { useState } from 'react'
import useSWR from 'swr'
import { format, subDays } from 'date-fns'
import { fetchEmployeeById, fetchScreenshots, fetchJournals } from '@/lib/api'
import ScreenshotCard from '@/components/ScreenshotCard'
import DateRangePicker from '@/components/DateRangePicker'
import type { Employee, Screenshot, Journal } from '@/lib/api'

const REFRESH_INTERVAL = 60000

interface EmployeePageProps {
  params: Promise<{ id: string }>
}

export default function EmployeePage({ params }: EmployeePageProps) {
  const { id } = use(params)
  const [selectedDate, setSelectedDate] = useState(format(new Date(), 'yyyy-MM-dd'))

  const { data: employee, error: employeeError } = useSWR<Employee>(
    id ? `employee-${id}` : null,
    () => fetchEmployeeById(id),
    { refreshInterval: REFRESH_INTERVAL }
  )

  const { data: screenshots, error: screenshotsError, isLoading: screenshotsLoading } = useSWR(
    id && selectedDate ? [`screenshots-${id}-${selectedDate}`, id, selectedDate] : null,
    () => fetchScreenshots(id, selectedDate),
    { refreshInterval: REFRESH_INTERVAL }
  )

  const { data: journals } = useSWR<Journal[]>(
    id ? [`journals-${id}`] : null,
    () => fetchJournals(id),
    { refreshInterval: REFRESH_INTERVAL }
  )

  const journalForDate = journals?.find(
    (j) => j.journal_date === selectedDate
  )

  if (employeeError) {
    return (
      <div className="rounded-lg border border-destructive bg-destructive/10 p-4 text-destructive">
        Failed to load employee details.
      </div>
    )
  }

  return (
    <div>
      <div className="mb-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-foreground">
              {employee?.name || 'Loading...'}
            </h1>
            {employee?.location && (
              <p className="mt-1 text-sm text-muted-foreground">
                {employee.location}
              </p>
            )}
          </div>
        </div>
      </div>

      <div className="mb-6">
        <DateRangePicker
          startDate={selectedDate}
          endDate={selectedDate}
          onStartDateChange={setSelectedDate}
          onEndDateChange={setSelectedDate}
        />
      </div>

      {journalForDate && (
        <div className="mb-6 rounded-lg border border-border bg-card p-4">
          <h3 className="font-semibold text-foreground">Daily Summary</h3>
          <div className="mt-2 grid grid-cols-2 gap-4 sm:grid-cols-4">
            <div>
              <p className="text-2xl font-bold text-foreground">
                {journalForDate.screenshot_count}
              </p>
              <p className="text-xs text-muted-foreground">Screenshots</p>
            </div>
            <div>
              <p className="text-2xl font-bold text-destructive">
                {journalForDate.high_risk_count}
              </p>
              <p className="text-xs text-muted-foreground">High Risk Events</p>
            </div>
          </div>
          {journalForDate.narrative && (
            <p className="mt-3 text-sm text-foreground/80">
              {journalForDate.narrative}
            </p>
          )}
        </div>
      )}

      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-lg font-semibold text-foreground">
          Screenshots - {selectedDate}
        </h2>
        <span className="text-sm text-muted-foreground">
          {screenshots?.length || 0} screenshots
        </span>
      </div>

      {screenshotsLoading ? (
        <div className="flex items-center justify-center py-12">
          <div className="animate-pulse text-muted-foreground">
            Loading screenshots...
          </div>
        </div>
      ) : screenshotsError ? (
        <div className="rounded-lg border border-destructive bg-destructive/10 p-4 text-destructive">
          Failed to load screenshots.
        </div>
      ) : screenshots && screenshots.length > 0 ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
          {screenshots.map((screenshot) => (
            <ScreenshotCard key={screenshot.id} screenshot={screenshot} />
          ))}
        </div>
      ) : (
        <div className="rounded-lg border border-border bg-card p-8 text-center">
          <p className="text-muted-foreground">No screenshots for this date.</p>
        </div>
      )}

      <div className="mt-4 text-xs text-muted-foreground">
        Auto-refresh every 60 seconds
      </div>
    </div>
  )
}
