import { useCallback, useEffect, useState } from 'react'
import { useOutletContext } from 'react-router-dom'
import { settlementsApi } from '../api/api'
import { useAuth } from '../context/AuthContext'
import { balanceLabel, formatDate, getErrorMessage, todayISO } from '../utils/format'
import { formatPaise, paiseToRupeesInput, rupeesToPaise } from '../utils/money'
import {
  Avatar, BalanceAmount, Button, Card, EmptyState, ErrorAlert, Field, LoadingState, SuccessAlert,
} from '../components/ui'

function useLoader(fetcher) {
  const [data, setData] = useState(null)
  const [error, setError] = useState('')
  const load = useCallback(() => {
    setError('')
    return fetcher().then(setData).catch((err) => setError(getErrorMessage(err)))
  }, [fetcher])
  useEffect(() => {
    load()
  }, [load])
  return { data, error, load }
}

/* ------------------------------------------------------------ Balances */

export function BalancesPage() {
  const { group } = useOutletContext()
  const fetcher = useCallback(() => settlementsApi.balances(group.id), [group.id])
  const { data, error, load } = useLoader(fetcher)

  if (error) return <ErrorAlert message={error} onRetry={load} />
  if (!data) return <LoadingState label="Calculating balances…" />

  const maxAbs = Math.max(1, ...data.balances.map((b) => Math.abs(b.net_balance_paise)))

  return (
    <div className="space-y-6">
      <Card className="p-5">
        <h2 className="text-base font-semibold">Who is up, who is down</h2>
        <p className="text-xs text-slate-500">Green members should receive money; red members owe money.</p>
        <ul className="mt-5 space-y-3">
          {data.balances.map((b) => {
            const pct = (Math.abs(b.net_balance_paise) / maxAbs) * 50
            return (
              <li key={b.user_id} className="grid grid-cols-[7rem_1fr_7rem] items-center gap-3 text-sm sm:grid-cols-[10rem_1fr_8rem]">
                <span className="flex items-center gap-2 truncate">
                  <Avatar name={b.name} size="sm" /> {b.name}{!b.is_member && <span className="text-xs text-slate-400">(left)</span>}
                </span>
                <div className="relative h-3 rounded-full bg-slate-100">
                  <div className="absolute inset-y-0 left-1/2 w-px bg-slate-300" />
                  {b.net_balance_paise !== 0 && (
                    <div
                      className={`absolute inset-y-0 rounded-full ${b.net_balance_paise > 0 ? 'left-1/2 bg-emerald-500' : 'right-1/2 bg-rose-500'}`}
                      style={{ width: `${pct}%` }}
                    />
                  )}
                </div>
                <BalanceAmount paise={b.net_balance_paise} className="text-right" />
              </li>
            )
          })}
        </ul>
      </Card>

      <Card className="overflow-x-auto">
        <table className="w-full min-w-[640px] text-sm">
          <thead className="bg-slate-50 text-left text-xs uppercase tracking-wide text-slate-500">
            <tr>
              <th className="px-5 py-3 font-semibold">Member</th>
              <th className="px-3 py-3 text-right font-semibold">Paid</th>
              <th className="px-3 py-3 text-right font-semibold">Share</th>
              <th className="px-3 py-3 text-right font-semibold">Repaid</th>
              <th className="px-3 py-3 text-right font-semibold">Received</th>
              <th className="px-5 py-3 text-right font-semibold">Net balance</th>
            </tr>
          </thead>
          <tbody className="amount divide-y divide-slate-100">
            {data.balances.map((b) => (
              <tr key={b.user_id}>
                <td className="px-5 py-3 font-medium">{b.name}</td>
                <td className="px-3 py-3 text-right">{formatPaise(b.total_paid_paise)}</td>
                <td className="px-3 py-3 text-right">{formatPaise(b.total_share_paise)}</td>
                <td className="px-3 py-3 text-right">{formatPaise(b.settlements_paid_paise)}</td>
                <td className="px-3 py-3 text-right">{formatPaise(b.settlements_received_paise)}</td>
                <td className="px-5 py-3 text-right">
                  <BalanceAmount paise={b.net_balance_paise} />
                  <p className="text-xs text-slate-400">{balanceLabel(b.net_balance_paise)}</p>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        <p className="border-t border-slate-100 px-5 py-3 text-xs text-slate-500">
          Net balance = Paid − Share + Repaid − Received. The net balances of a group always add up to ₹0.00.
        </p>
      </Card>
    </div>
  )
}

/* ------------------------------------------------------------ Suggested settlements + record */

export function SettleUpPage() {
  const { group, reloadGroup } = useOutletContext()
  const { user } = useAuth()
  const fetcher = useCallback(() => settlementsApi.suggested(group.id), [group.id])
  const { data, error, load } = useLoader(fetcher)
  const [form, setForm] = useState({ paidBy: '', paidTo: '', amount: '', date: todayISO() })
  const [saving, setSaving] = useState(false)
  const [formError, setFormError] = useState('')
  const [success, setSuccess] = useState('')
  const isAdmin = group.my_role === 'admin'

  const set = (field) => (e) => setForm((f) => ({ ...f, [field]: e.target.value }))

  const prefill = (s) => {
    setSuccess('')
    setFormError('')
    setForm({ paidBy: String(s.from_user_id), paidTo: String(s.to_user_id), amount: paiseToRupeesInput(s.amount_paise), date: todayISO() })
    document.getElementById('record-form')?.scrollIntoView({ behavior: 'smooth', block: 'center' })
  }

  async function handleSubmit(event) {
    event.preventDefault()
    const amountPaise = rupeesToPaise(form.amount)
    if (!form.paidBy || !form.paidTo) return setFormError('Choose who paid and who received the money.')
    if (form.paidBy === form.paidTo) return setFormError('Payer and receiver must be different people.')
    if (!amountPaise) return setFormError('Enter a valid amount.')
    setSaving(true)
    setFormError('')
    setSuccess('')
    try {
      const s = await settlementsApi.create(group.id, {
        paid_by: Number(form.paidBy), paid_to: Number(form.paidTo), amount_paise: amountPaise, settled_at: form.date,
      })
      setSuccess(`Recorded: ${s.paid_by_name} paid ${s.paid_to_name} ${formatPaise(s.amount_paise)}.`)
      setForm({ paidBy: '', paidTo: '', amount: '', date: todayISO() })
      await Promise.all([load(), reloadGroup()])
    } catch (err) {
      setFormError(getErrorMessage(err))
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="grid gap-6 lg:grid-cols-5">
      <div className="space-y-4 lg:col-span-3">
        <Card>
          <div className="border-b border-slate-100 px-5 py-4">
            <h2 className="text-base font-semibold">Suggested settlements</h2>
            <p className="text-xs text-slate-500">The fewest repayments our greedy algorithm finds to settle everyone.</p>
          </div>
          <ErrorAlert message={error} onRetry={load} />
          {!data && !error && <LoadingState />}
          {data && data.settlements.length === 0 && (
            <div className="p-5">
              <EmptyState title="Everyone is settled up 🎉" description="There are no outstanding balances in this group." />
            </div>
          )}
          {data && data.settlements.length > 0 && (
            <ul className="divide-y divide-slate-100">
              {data.settlements.map((s, i) => {
                const canRecord = isAdmin || [s.from_user_id, s.to_user_id].includes(user.id)
                return (
                  <li key={i} className="flex flex-wrap items-center gap-3 px-5 py-4">
                    <Avatar name={s.from_name} />
                    <div className="min-w-0 flex-1 text-sm">
                      <p>
                        <strong>{s.from_user_id === user.id ? 'You' : s.from_name}</strong> pay{s.from_user_id === user.id ? '' : 's'}{' '}
                        <strong>{s.to_user_id === user.id ? 'you' : s.to_name}</strong>
                      </p>
                      <p className="amount text-lg font-semibold text-slate-900">{formatPaise(s.amount_paise)}</p>
                    </div>
                    {canRecord && <Button variant="secondary" onClick={() => prefill(s)}>Record payment</Button>}
                  </li>
                )
              })}
            </ul>
          )}
        </Card>
      </div>

      <div className="space-y-4 lg:col-span-2" id="record-form">
        <Card className="p-5">
          <h2 className="text-base font-semibold">Record a repayment</h2>
          <p className="mt-1 text-xs text-slate-500">
            Log a payment made outside the app (cash, UPI…). You can record payments you made or received
            {isAdmin ? ', or any payment as admin' : ''}.
          </p>
          <form onSubmit={handleSubmit} className="mt-4 space-y-3">
            <Field label="Paid by" htmlFor="paidBy">
              <select id="paidBy" className="input" value={form.paidBy} onChange={set('paidBy')}>
                <option value="">Select member</option>
                {group.members.map((m) => <option key={m.user_id} value={m.user_id}>{m.name}</option>)}
              </select>
            </Field>
            <Field label="Paid to" htmlFor="paidTo">
              <select id="paidTo" className="input" value={form.paidTo} onChange={set('paidTo')}>
                <option value="">Select member</option>
                {group.members.map((m) => <option key={m.user_id} value={m.user_id}>{m.name}</option>)}
              </select>
            </Field>
            <div className="grid grid-cols-2 gap-3">
              <Field label="Amount (₹)" htmlFor="settleAmount">
                <input id="settleAmount" className="input amount" inputMode="decimal" value={form.amount} onChange={set('amount')} placeholder="0.00" />
              </Field>
              <Field label="Date" htmlFor="settleDate">
                <input id="settleDate" type="date" className="input" value={form.date} onChange={set('date')} />
              </Field>
            </div>
            <ErrorAlert message={formError} />
            <SuccessAlert message={success} />
            <Button type="submit" className="w-full" loading={saving}>Save repayment</Button>
          </form>
        </Card>
      </div>
    </div>
  )
}

/* ------------------------------------------------------------ History */

export function SettlementHistoryPage() {
  const { group } = useOutletContext()
  const fetcher = useCallback(() => settlementsApi.list(group.id), [group.id])
  const { data, error, load } = useLoader(fetcher)

  if (error) return <ErrorAlert message={error} onRetry={load} />
  if (!data) return <LoadingState />
  if (data.length === 0) {
    return <EmptyState title="No repayments recorded yet" description="When someone pays back, record it on the Settle up tab." />
  }
  return (
    <Card>
      <ul className="divide-y divide-slate-100">
        {data.map((s) => (
          <li key={s.id} className="flex items-center gap-3 px-5 py-4">
            <div className="flex -space-x-2">
              <Avatar name={s.paid_by_name} />
              <Avatar name={s.paid_to_name} />
            </div>
            <div className="min-w-0 flex-1 text-sm">
              <p><strong>{s.paid_by_name}</strong> paid <strong>{s.paid_to_name}</strong></p>
              <p className="text-xs text-slate-500">{formatDate(s.settled_at)}</p>
            </div>
            <span className="amount font-semibold text-slate-900">{formatPaise(s.amount_paise)}</span>
          </li>
        ))}
      </ul>
    </Card>
  )
}
