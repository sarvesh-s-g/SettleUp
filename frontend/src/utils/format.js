export const CATEGORIES = [
  { value: 'food', label: 'Food & dining' },
  { value: 'groceries', label: 'Groceries' },
  { value: 'rent', label: 'Rent' },
  { value: 'utilities', label: 'Utilities' },
  { value: 'transport', label: 'Transport' },
  { value: 'entertainment', label: 'Entertainment' },
  { value: 'shopping', label: 'Shopping' },
  { value: 'other', label: 'Other' },
]

export const CATEGORY_COLORS = {
  food: '#f97316',
  groceries: '#16a34a',
  rent: '#0f766e',
  utilities: '#2563eb',
  transport: '#9333ea',
  entertainment: '#db2777',
  shopping: '#ca8a04',
  other: '#64748b',
}

export function categoryLabel(value) {
  return CATEGORIES.find((c) => c.value === value)?.label ?? value
}

/** "2026-11-05" -> "5 Nov 2026" without timezone shifts. */
export function formatDate(isoDate) {
  if (!isoDate) return ''
  const [y, m, d] = isoDate.slice(0, 10).split('-').map(Number)
  return new Date(y, m - 1, d).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' })
}

/** "2026-11" -> "Nov 26" */
export function formatMonth(yearMonth) {
  const [y, m] = yearMonth.split('-').map(Number)
  return new Date(y, m - 1, 1).toLocaleDateString('en-IN', { month: 'short', year: '2-digit' })
}

/** Today's date as YYYY-MM-DD in the user's local timezone. */
export function todayISO() {
  const now = new Date()
  const local = new Date(now.getTime() - now.getTimezoneOffset() * 60000)
  return local.toISOString().slice(0, 10)
}

/** Turn an Axios error into one readable sentence. */
export function getErrorMessage(error, fallback = 'Something went wrong. Please try again.') {
  if (!error?.response) {
    return error?.code === 'ERR_NETWORK'
      ? 'Cannot reach the server. Is the backend running?'
      : fallback
  }
  const detail = error.response.data?.detail
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail) && detail.length) {
    // FastAPI/Pydantic validation errors: [{loc: [...], msg: '...'}]
    return detail
      .map((d) => {
        const field = d.loc?.filter((p) => p !== 'body').join('.')
        const msg = (d.msg || '').replace(/^Value error, /, '')
        return field ? `${field}: ${msg}` : msg
      })
      .join(' · ')
  }
  return fallback
}

export function initials(name = '') {
  return name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((p) => p[0].toUpperCase())
    .join('')
}

export function balanceLabel(paise) {
  if (paise > 0) return 'gets back'
  if (paise < 0) return 'owes'
  return 'settled up'
}
