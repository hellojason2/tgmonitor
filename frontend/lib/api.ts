const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export interface Employee {
  id: string
  name: string
  location: string | null
  devices: Device[]
  latest_activity?: {
    app_name: string
    window_title: string
    captured_at: string
  }
}

export interface Device {
  id: string
  name: string
  last_seen: string
}

export interface Screenshot {
  id: string
  employee_id: string
  captured_at: string
  file_path: string
  app_name: string
  window_title: string
  analysis_status: 'pending' | 'completed' | 'failed'
  analysis_result?: {
    caption: string
    risk_score: number
  }
}

export interface Alert {
  id: string
  caption: string
  risk_score: number
  alert_type: string
  created_at: string
  acknowledged: boolean
  screenshot?: {
    file_path: string
    employee_id: string
  }
  employee?: {
    id: string
    name: string
  }
}

export interface Journal {
  journal_date: string
  narrative: string | null
  screenshot_count: number
  high_risk_count: number
}

function getAuthHeaders(): HeadersInit {
  if (typeof window === 'undefined') return {}
  const token = localStorage.getItem('auth_token')
  return token ? { Authorization: `Bearer ${token}` } : {}
}

export async function fetchEmployees(): Promise<Employee[]> {
  const res = await fetch(`${API_URL}/api/v1/employees`, {
    headers: getAuthHeaders(),
  })
  if (!res.ok) throw new Error('Failed to fetch employees')
  return res.json()
}

export async function fetchEmployeeById(id: string): Promise<Employee> {
  const res = await fetch(`${API_URL}/api/v1/employees/${id}`, {
    headers: getAuthHeaders(),
  })
  if (!res.ok) throw new Error('Failed to fetch employee')
  return res.json()
}

export async function fetchScreenshots(
  employeeId: string,
  date: string,
  limit = 100
): Promise<Screenshot[]> {
  const params = new URLSearchParams({
    employee_id: employeeId,
    date,
    limit: String(limit),
  })
  const res = await fetch(`${API_URL}/api/v1/screenshots?${params}`, {
    headers: getAuthHeaders(),
  })
  if (!res.ok) throw new Error('Failed to fetch screenshots')
  return res.json()
}

export async function fetchAlerts(acknowledged = false): Promise<Alert[]> {
  const params = new URLSearchParams({ acknowledged: String(acknowledged) })
  const res = await fetch(`${API_URL}/api/v1/alerts?${params}`, {
    headers: getAuthHeaders(),
  })
  if (!res.ok) throw new Error('Failed to fetch alerts')
  return res.json()
}

export async function acknowledgeAlert(alertId: string): Promise<void> {
  const res = await fetch(`${API_URL}/api/v1/alerts/${alertId}/acknowledge`, {
    method: 'POST',
    headers: {
      ...getAuthHeaders(),
      'Content-Type': 'application/json',
    },
  })
  if (!res.ok) throw new Error('Failed to acknowledge alert')
}

export async function fetchJournals(employeeId: string): Promise<Journal[]> {
  const params = new URLSearchParams({ employee_id: employeeId })
  const res = await fetch(`${API_URL}/api/v1/journals?${params}`, {
    headers: getAuthHeaders(),
  })
  if (!res.ok) throw new Error('Failed to fetch journals')
  return res.json()
}

export async function login(password: string): Promise<{ token: string }> {
  const res = await fetch(`${API_URL}/api/v1/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ password }),
  })
  if (!res.ok) throw new Error('Invalid password')
  return res.json()
}

export async function verifyAuth(): Promise<boolean> {
  try {
    const token = localStorage.getItem('auth_token')
    if (!token) return false
    const res = await fetch(`${API_URL}/api/v1/auth/verify`, {
      headers: { Authorization: `Bearer ${token}` },
    })
    return res.ok
  } catch {
    return false
  }
}

export function getScreenshotUrl(filePath: string): string {
  if (!filePath) return ''
  const cleanPath = filePath.startsWith('/') ? filePath.slice(1) : filePath
  return `${API_URL}/screenshots/${cleanPath}`
}
