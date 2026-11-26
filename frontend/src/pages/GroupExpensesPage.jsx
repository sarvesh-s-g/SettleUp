import { useCallback, useEffect, useState } from 'react'
import { Link, useOutletContext } from 'react-router-dom'
import { expensesApi } from '../api/api'
import { useAuth } from '../context/AuthContext'
import { CATEGORIES, formatDate, getErrorMessage } from '../utils/format'
import { formatPaise } from '../utils/money'
import { Button, ButtonLink, Card, CategoryBadge, EmptyState, ErrorAlert, LoadingState } from '../components/ui'

const PAGE_SIZE = 10
const emptyFilters = { category: '', member_id: '', from_date: '', to_date: '' }

/** Group details page: the group's expense history with filters and pagination. */
export default function GroupExpensesPage() {
  const { group } = useOutletContext()
  const { user } = useAuth()
  const [filters, setFilters] = useState(emptyFilters)
  const [page, setPage] = useState(1)
  const [result, setResult] = useState(null)
  const [error, setError] = useState('')

  const load = useCallback(() => {
    setError('')
    // Only send filters that have a value.
    const params = Object.fromEntries(Object.entries(filters).filter(([, v]) => v !== ''))
    expensesApi
      .list(group.id, { ...params, page, page_size: PAGE_SIZE })
      .then(setResult)
      .catch((err) => setError(getErrorMessage(err)))
  }, [group.id, filters, page])
  useEffect(load, [load])

  const setFilter = (field) => (e) => {
    setPage(1)
    setFilters((f) => ({ ...f, [field]: e.target.value }))
  }
  const hasFilters = Object.values(filters).some(Boolean)
  const totalPages = result ? Math.max(1, Math.ceil(result.total / PAGE_SIZE)) : 1

  return (
    <div className="space-y-4">
      <Card className="grid gap-3 p-4 sm:grid-cols-2 lg:grid-cols-5">
        <select aria-label="Filter by category" className="input" value={filters.category} onChange={setFilter('category')}>
          <option value="">All categories</option>
          {CATEGORIES.map((c) => <option key={c.value} value={c.value}>{c.label}</option>)}
        </select>
        <select aria-label="Filter by member" className="input" value={filters.member_id} onChange={setFilter('member_id')}>
          <option value="">All members</option>
          {group.members.map((m) => <option key={m.user_id} value={m.user_id}>{m.name}</option>)}
        </select>
        <input aria-label="From date" type="date" className="input" value={filters.from_date} onChange={setFilter('from_date')} />
        <input aria-label="To date" type="date" className="input" value={filters.to_date} onChange={setFilter('to_date')} />
        <Button variant="ghost" onClick={() => { setFilters(emptyFilters); setPage(1) }} disabled={!hasFilters}>
          Clear filters
        </Button>
      </Card>

      <ErrorAlert message={error} onRetry={load} />
      {!result && !error && <LoadingState label="Loading expenses…" />}

      {result && result.total === 0 && (
        hasFilters ? (
          <EmptyState title="No expenses match these filters" description="Try a different category, member or date range." />
        ) : (
          <EmptyState title="No expenses yet" description="Add the first shared expense for this group."
            action={<ButtonLink to={`/groups/${group.id}/expenses/new`}>Add expense</ButtonLink>} />
        )
      )}

      {result && result.total > 0 && (
        <Card>
          <ul className="divide-y divide-slate-100">
            {result.items.map((e) => {
              const mine = e.splits.find((s) => s.user_id === user.id)?.share_amount_paise ?? 0
              const iPaid = e.paid_by === user.id
              const effect = (iPaid ? e.amount_paise : 0) - mine
              return (
                <li key={e.id}>
                  <Link to={`/expenses/${e.id}`} className="flex items-center gap-4 px-5 py-4 hover:bg-slate-50">
                    <div className="hidden w-14 shrink-0 text-center sm:block">
                      <p className="text-xs uppercase text-slate-500">{formatDate(e.expense_date).split(' ')[1]}</p>
                      <p className="text-lg font-semibold leading-tight">{formatDate(e.expense_date).split(' ')[0]}</p>
                    </div>
                    <div className="min-w-0 flex-1">
                      <p className="truncate font-medium text-slate-900">{e.description}</p>
                      <div className="mt-1 flex flex-wrap items-center gap-2 text-xs text-slate-500">
                        <CategoryBadge category={e.category} />
                        <span>{iPaid ? 'You' : e.paid_by_name} paid {formatPaise(e.amount_paise)}</span>
                        <span className="sm:hidden">· {formatDate(e.expense_date)}</span>
                        <span>· {e.split_type} split, {e.splits.length} people</span>
                      </div>
                    </div>
                    <div className="shrink-0 text-right">
                      {effect === 0 ? (
                        <p className="text-xs text-slate-400">{mine || iPaid ? 'even' : 'not involved'}</p>
                      ) : (
                        <>
                          <p className="text-xs text-slate-500">{effect > 0 ? 'you lent' : 'you borrowed'}</p>
                          <p className={`amount text-sm font-semibold ${effect > 0 ? 'text-emerald-700' : 'text-rose-700'}`}>
                            {formatPaise(Math.abs(effect))}
                          </p>
                        </>
                      )}
                    </div>
                  </Link>
                </li>
              )
            })}
          </ul>
          <div className="flex items-center justify-between border-t border-slate-100 px-5 py-3 text-sm">
            <span className="text-slate-500">
              {result.total} expense{result.total === 1 ? '' : 's'} · page {page} of {totalPages}
            </span>
            <div className="flex gap-2">
              <Button variant="secondary" onClick={() => setPage((p) => p - 1)} disabled={page <= 1}>Previous</Button>
              <Button variant="secondary" onClick={() => setPage((p) => p + 1)} disabled={page >= totalPages}>Next</Button>
            </div>
          </div>
        </Card>
      )}
    </div>
  )
}
