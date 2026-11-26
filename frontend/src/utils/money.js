// All money in SettleUp is an integer number of paise (Rs 1 = 100 paise).
// These helpers convert between what the user types/sees and paise,
// using only integer and string operations (no floating-point maths).

const RUPEES_PATTERN = /^\d{1,8}(\.\d{0,2})?$/

/** "125.5" -> 12550, "1,200" -> 120000. Returns null for invalid input. */
export function rupeesToPaise(text) {
  if (text === null || text === undefined) return null
  const cleaned = String(text).trim().replace(/,/g, '')
  if (!RUPEES_PATTERN.test(cleaned)) return null
  const [rupees, paise = ''] = cleaned.split('.')
  return parseInt(rupees, 10) * 100 + parseInt(paise.padEnd(2, '0'), 10)
}

/** 12550 -> "125.50" (for pre-filling input boxes). */
export function paiseToRupeesInput(paise) {
  const abs = Math.abs(paise)
  return `${paise < 0 ? '-' : ''}${Math.floor(abs / 100)}.${String(abs % 100).padStart(2, '0')}`
}

const groupFormatter = new Intl.NumberFormat('en-IN')

/** 12345678 -> "₹1,23,456.78" (Indian digit grouping). */
export function formatPaise(paise, { signed = false } = {}) {
  const value = Number(paise) || 0
  const abs = Math.abs(value)
  const rupees = groupFormatter.format(Math.floor(abs / 100))
  const fraction = String(abs % 100).padStart(2, '0')
  let sign = ''
  if (value < 0) sign = '-'
  else if (signed && value > 0) sign = '+'
  return `${sign}₹${rupees}.${fraction}`
}

/** Same deterministic algorithm as the backend, used only for the live preview. */
export function previewEqualSplit(amountPaise, userIds) {
  const ordered = [...userIds].sort((a, b) => a - b)
  if (!ordered.length || !amountPaise) return {}
  const base = Math.floor(amountPaise / ordered.length)
  const remainder = amountPaise % ordered.length
  return Object.fromEntries(ordered.map((id, i) => [id, base + (i < remainder ? 1 : 0)]))
}
