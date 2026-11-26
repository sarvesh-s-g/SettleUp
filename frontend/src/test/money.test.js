import { describe, expect, it } from 'vitest'
import { formatPaise, paiseToRupeesInput, previewEqualSplit, rupeesToPaise } from '../utils/money'
import { getErrorMessage } from '../utils/format'

describe('rupeesToPaise', () => {
  it('converts typed rupee amounts to integer paise without floating point', () => {
    expect(rupeesToPaise('1200')).toBe(120000)
    expect(rupeesToPaise('125.5')).toBe(12550)
    expect(rupeesToPaise('125.50')).toBe(12550)
    expect(rupeesToPaise('0.07')).toBe(7)
    expect(rupeesToPaise('1,200.99')).toBe(120099)
    // 0.1 + 0.2 style float errors cannot happen: string maths only
    expect(rupeesToPaise('0.29')).toBe(29)
  })

  it('rejects invalid input', () => {
    for (const bad of ['', 'abc', '12.345', '-5', '1e3', null, undefined]) {
      expect(rupeesToPaise(bad)).toBeNull()
    }
  })
})

describe('formatPaise', () => {
  it('uses Indian digit grouping', () => {
    expect(formatPaise(12345678)).toBe('₹1,23,456.78')
    expect(formatPaise(5)).toBe('₹0.05')
    expect(formatPaise(-35000)).toBe('-₹350.00')
    expect(formatPaise(45000, { signed: true })).toBe('+₹450.00')
  })

  it('round-trips with the input helper', () => {
    expect(rupeesToPaise(paiseToRupeesInput(12550))).toBe(12550)
  })
})

describe('previewEqualSplit', () => {
  it('matches the backend rule: remainder paise go to the lowest user ids', () => {
    expect(previewEqualSplit(1000, [3, 1, 2])).toEqual({ 1: 334, 2: 333, 3: 333 })
  })
})

describe('getErrorMessage', () => {
  it('reads FastAPI string details', () => {
    expect(getErrorMessage({ response: { data: { detail: 'Group not found' } } })).toBe('Group not found')
  })
  it('flattens Pydantic validation errors', () => {
    const error = { response: { data: { detail: [{ loc: ['body', 'amount_paise'], msg: 'Input should be greater than 0' }] } } }
    expect(getErrorMessage(error)).toBe('amount_paise: Input should be greater than 0')
  })
  it('explains network failures', () => {
    expect(getErrorMessage({ code: 'ERR_NETWORK' })).toMatch(/Cannot reach the server/)
  })
})
