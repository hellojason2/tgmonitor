'use client'

import useSWR from 'swr'
import { fetchEmployees } from '@/lib/api'
import EmployeeCard from '@/components/EmployeeCard'

const REFRESH_INTERVAL = 60000 // 60 seconds

export default function DashboardPage() {
  const { data: employees, error, isLoading } = useSWR(
    'employees',
    fetchEmployees,
    {
      refreshInterval: REFRESH_INTERVAL,
      revalidateOnFocus: true,
    }
  )

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="animate-pulse text-muted-foreground">
          Loading employees...
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="rounded-lg border border-destructive bg-destructive/10 p-4 text-destructive">
        Failed to load employees. Please check your connection.
      </div>
    )
  }

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-foreground">Employees</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Monitor employee activity and screenshots
        </p>
      </div>

      {employees && employees.length > 0 ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
          {employees.map((employee) => (
            <EmployeeCard key={employee.id} employee={employee} />
          ))}
        </div>
      ) : (
        <div className="rounded-lg border border-border bg-card p-8 text-center">
          <p className="text-muted-foreground">No employees found.</p>
        </div>
      )}

      <div className="mt-4 text-xs text-muted-foreground">
        Auto-refresh every 60 seconds
      </div>
    </div>
  )
}
