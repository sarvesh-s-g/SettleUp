import { useMemo, useState } from 'react'
import { CATEGORIES, todayISO } from '../utils/format'
import { formatPaise, paiseToRupeesInput, previewEqualSplit, rupeesToPaise } from '../utils/money'
import { Avatar, Button, Card, ErrorAlert, Field } from './ui'

/**
 * Shared by "Add expense" and "Edit expense".
 * Collects the form values, validates them on the client for quick feedback,
 * and calls onSubmit(payload) with the exact JSON the backend expects.
 * (The backend validates everything again - the client checks are only for UX.)
 */
export default function ExpenseForm({ members, currentUserId, initial, submitLabel, onSubmit, onCancel }) {
  const memberIds = members.map((m) => m.user_id)
  const [form, setForm] = useState(() => ({
    description: initial?.description ?? '',
    amount: initial ? paiseToRupeesInput(initial.amount_paise) : '',
    paidBy: initial?.paid_by ?? (memberIds.includes(currentUserId) ? currentUserId : memberIds[0]),
    category: initial?.category ?? 'groceries',
    expenseDate: initial?.expense_date ?? todayISO(),
    notes: initial?.notes ?? '',
    splitType: initial?.split_type ?? 'equal',
  }))
  const [participants, setParticipants] = useState(
    () => new Set(initial ? initial.splits.map((s) => s.user_id) : memberIds),
  )
  const [customShares, setCustomShares] = useState(() =>
    Object.fromEntries(
      memberIds.map((id) => {
        const split = initial?.split_type === 'custom' && initial.splits.find((s) => s.user_id === id)
        return [id, split ? paiseToRupeesInput(split.share_amount_paise) : '']
      }),
    ),
  )
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)

  const set = (field) => (event) => setForm((f) => ({ ...f, [field]: event.target.value }))
  const amountPaise = rupeesToPaise(form.amount)

  const equalPreview = useMemo(
    () => previewEqualSplit(amountPaise ?? 0, [...participants]),
    [amountPaise, participants],
  )
  const customTotal = memberIds.reduce((sum, id) => sum + (rupeesToPaise(customShares[id]) ?? 0), 0)
  const customRemaining = (amountPaise ?? 0) - customTotal

  const toggleParticipant = (id) =>
    setParticipants((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })

  function buildPayload() {
    if (!form.description.trim()) return 'Please enter a description.'
    if (amountPaise === null || amountPaise <= 0) return 'Enter a valid amount, e.g. 1200 or 125.50.'
    const payload = {
      description: form.description.trim(),
      amount_paise: amountPaise,
      paid_by: Number(form.paidBy),
      category: form.category,
      expense_date: form.expenseDate,
      notes: form.notes.trim() || null,
      split_type: form.splitType,
    }
    if (form.splitType === 'equal') {
      if (participants.size === 0) return 'Select at least one person to split with.'
      payload.participant_ids = [...participants]
    } else {
      const splits = []
      for (const id of memberIds) {
        const raw = customShares[id]
        if (!raw || !raw.trim()) continue
        const share = rupeesToPaise(raw)
        if (share === null) return 'One of the custom shares is not a valid amount.'
        if (share > 0) splits.push({ user_id: id, share_amount_paise: share })
      }
      if (!splits.length) return 'Enter at least one share.'
      if (customRemaining !== 0) {
        return `Shares must add up to ${formatPaise(amountPaise)} (currently ${formatPaise(customTotal)}).`
      }
      payload.splits = splits
    }
    return payload
  }

  async function handleSubmit(event) {
    event.preventDefault()
    const payload = buildPayload()
    if (typeof payload === 'string') {
      setError(payload)
      return
    }
    setError('')
    setSubmitting(true)
    try {
      await onSubmit(payload)
    } catch (err) {
      setError(err.displayMessage || 'Could not save the expense.')
      setSubmitting(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="grid gap-6 lg:grid-cols-5" noValidate>
      <Card className="space-y-4 p-6 lg:col-span-3">
        <h2 className="text-base font-semibold">Details</h2>
        <Field label="Description" htmlFor="description">
          <input id="description" className="input" value={form.description} onChange={set('description')}
            placeholder="e.g. Groceries" maxLength={200} required />
        </Field>
        <div className="grid gap-4 sm:grid-cols-2">
          <Field label="Amount (₹)" htmlFor="amount" hint="Up to 2 decimal places">
            <input id="amount" className="input amount" inputMode="decimal" value={form.amount}
              onChange={set('amount')} placeholder="0.00" required />
          </Field>
          <Field label="Date" htmlFor="expenseDate">
            <input id="expenseDate" type="date" className="input" value={form.expenseDate}
              onChange={set('expenseDate')} required />
          </Field>
          <Field label="Paid by" htmlFor="paidBy">
            <select id="paidBy" className="input" value={form.paidBy} onChange={set('paidBy')}>
              {members.map((m) => (
                <option key={m.user_id} value={m.user_id}>
                  {m.name}{m.user_id === currentUserId ? ' (you)' : ''}
                </option>
              ))}
            </select>
          </Field>
          <Field label="Category" htmlFor="category">
            <select id="category" className="input" value={form.category} onChange={set('category')}>
              {CATEGORIES.map((c) => (
                <option key={c.value} value={c.value}>{c.label}</option>
              ))}
            </select>
          </Field>
        </div>
        <Field label="Notes (optional)" htmlFor="notes">
          <textarea id="notes" rows={3} className="input" value={form.notes} onChange={set('notes')} maxLength={1000} />
        </Field>
      </Card>

      <Card className="space-y-4 p-6 lg:col-span-2">
        <div className="flex items-center justify-between">
          <h2 className="text-base font-semibold">Split</h2>
          <div className="inline-flex rounded-lg bg-slate-100 p-1" role="radiogroup" aria-label="Split type">
            {['equal', 'custom'].map((type) => (
              <button key={type} type="button" role="radio" aria-checked={form.splitType === type}
                onClick={() => setForm((f) => ({ ...f, splitType: type }))}
                className={`rounded-md px-3 py-1 text-sm font-medium capitalize transition ${
                  form.splitType === type ? 'bg-white text-slate-900 shadow-sm' : 'text-slate-500'
                }`}>
                {type}
              </button>
            ))}
          </div>
        </div>

        {form.splitType === 'equal' ? (
          <ul className="divide-y divide-slate-100">
            {members.map((m) => (
              <li key={m.user_id} className="flex items-center justify-between py-2.5">
                <label className="flex cursor-pointer items-center gap-3 text-sm">
                  <input type="checkbox" className="h-4 w-4 accent-brand-700" checked={participants.has(m.user_id)}
                    onChange={() => toggleParticipant(m.user_id)} />
                  <Avatar name={m.name} size="sm" />
                  {m.name}
                </label>
                <span className="amount text-sm text-slate-600">
                  {participants.has(m.user_id) ? formatPaise(equalPreview[m.user_id] ?? 0) : '—'}
                </span>
              </li>
            ))}
          </ul>
        ) : (
          <div className="space-y-2">
            {members.map((m) => (
              <div key={m.user_id} className="flex items-center gap-3">
                <Avatar name={m.name} size="sm" />
                <label htmlFor={`share-${m.user_id}`} className="flex-1 text-sm">{m.name}</label>
                <input id={`share-${m.user_id}`} className="input amount w-32 text-right" inputMode="decimal"
                  placeholder="0.00" value={customShares[m.user_id]}
                  onChange={(e) => setCustomShares((s) => ({ ...s, [m.user_id]: e.target.value }))} />
              </div>
            ))}
            <p className={`pt-2 text-right text-sm ${customRemaining === 0 ? 'text-emerald-700' : 'text-amber-700'}`}>
              {customRemaining === 0
                ? 'Shares add up ✓'
                : customRemaining > 0
                  ? `${formatPaise(customRemaining)} left to assign`
                  : `${formatPaise(-customRemaining)} over the total`}
            </p>
          </div>
        )}
      </Card>

      <div className="space-y-4 lg:col-span-5">
        <ErrorAlert message={error} />
        <div className="flex justify-end gap-2">
          {onCancel && <Button type="button" variant="secondary" onClick={onCancel}>Cancel</Button>}
          <Button type="submit" loading={submitting}>{submitLabel}</Button>
        </div>
      </div>
    </form>
  )
}
