import { useEffect, useState } from 'react'
import { Link, useNavigate, useOutletContext, useParams } from 'react-router-dom'
import { expensesApi, groupsApi } from '../api/api'
import { useAuth } from '../context/AuthContext'
import ExpenseForm from '../components/ExpenseForm'
import { categoryLabel, formatDate, getErrorMessage } from '../utils/format'
import { formatPaise } from '../utils/money'
import { Avatar, Button, ButtonLink, Card, CategoryBadge, ErrorAlert, LoadingState, PageHeader } from '../components/ui'

/** Wrap an API call so ExpenseForm can show a readable error message. */
async function withMessage(promise) {
  try {
    return await promise
  } catch (err) {
    err.displayMessage = getErrorMessage(err)
    throw err
  }
}

export function AddExpensePage() {
  const { group, reloadGroup } = useOutletContext()
  const { user } = useAuth()
  const navigate = useNavigate()

  async function handleSubmit(payload) {
    const expense = await withMessage(expensesApi.create(group.id, payload))
    await reloadGroup()
    navigate(`/expenses/${expense.id}`, { replace: true })
  }

  return (
    <>
      <h2 className="mb-4 text-lg font-semibold">Add an expense</h2>
      <ExpenseForm
        members={group.members}
        currentUserId={user.id}
        submitLabel="Save expense"
        onSubmit={handleSubmit}
        onCancel={() => navigate(`/groups/${group.id}`)}
      />
    </>
  )
}

/** Loads an expense plus its group (for member list and the caller's role). */
function useExpenseWithGroup(expenseId) {
  const [state, setState] = useState({ expense: null, group: null, error: '' })
  useEffect(() => {
    let cancelled = false
    expensesApi
      .get(expenseId)
      .then(async (expense) => {
        const group = await groupsApi.get(expense.group_id)
        if (!cancelled) setState({ expense, group, error: '' })
      })
      .catch((err) => !cancelled && setState({ expense: null, group: null, error: getErrorMessage(err) }))
    return () => {
      cancelled = true
    }
  }, [expenseId])
  return state
}

export function EditExpensePage() {
  const { expenseId } = useParams()
  const { user } = useAuth()
  const navigate = useNavigate()
  const { expense, group, error } = useExpenseWithGroup(expenseId)

  if (error) return <ErrorAlert message={error} />
  if (!expense) return <LoadingState label="Loading expense…" />

  async function handleSubmit(payload) {
    await withMessage(expensesApi.update(expense.id, payload))
    navigate(`/expenses/${expense.id}`, { replace: true })
  }

  return (
    <>
      <Link to={`/expenses/${expense.id}`} className="text-sm font-medium text-slate-500 hover:text-slate-800">← Back to expense</Link>
      <PageHeader title="Edit expense" subtitle={`${group.name} · ${expense.description}`} />
      <ExpenseForm
        members={group.members}
        currentUserId={user.id}
        initial={expense}
        submitLabel="Save changes"
        onSubmit={handleSubmit}
        onCancel={() => navigate(`/expenses/${expense.id}`)}
      />
    </>
  )
}

export function ExpenseDetailPage() {
  const { expenseId } = useParams()
  const { user } = useAuth()
  const navigate = useNavigate()
  const { expense, group, error } = useExpenseWithGroup(expenseId)
  const [deleteError, setDeleteError] = useState('')
  const [deleting, setDeleting] = useState(false)

  if (error) return <ErrorAlert message={error} />
  if (!expense) return <LoadingState label="Loading expense…" />

  const canModify = expense.paid_by === user.id || group.my_role === 'admin'

  async function handleDelete() {
    if (!window.confirm(`Delete "${expense.description}"? Balances will be recalculated.`)) return
    setDeleting(true)
    try {
      await expensesApi.remove(expense.id)
      navigate(`/groups/${expense.group_id}`, { replace: true })
    } catch (err) {
      setDeleteError(getErrorMessage(err))
      setDeleting(false)
    }
  }

  return (
    <div className="mx-auto max-w-3xl">
      <Link to={`/groups/${group.id}`} className="text-sm font-medium text-slate-500 hover:text-slate-800">← {group.name}</Link>
      <PageHeader
        title={expense.description}
        subtitle={`${categoryLabel(expense.category)} · ${formatDate(expense.expense_date)}`}
        actions={canModify && (
          <>
            <ButtonLink to={`/expenses/${expense.id}/edit`} variant="secondary">Edit</ButtonLink>
            <Button variant="danger" onClick={handleDelete} loading={deleting}>Delete</Button>
          </>
        )}
      />
      <ErrorAlert message={deleteError} />
      <div className="mt-4 grid gap-6 sm:grid-cols-5">
        <Card className="space-y-4 p-5 sm:col-span-2">
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Total</p>
            <p className="amount text-3xl font-bold">{formatPaise(expense.amount_paise)}</p>
          </div>
          <dl className="space-y-2 text-sm">
            <div className="flex justify-between"><dt className="text-slate-500">Paid by</dt><dd className="font-medium">{expense.paid_by_name}</dd></div>
            <div className="flex justify-between"><dt className="text-slate-500">Category</dt><dd><CategoryBadge category={expense.category} /></dd></div>
            <div className="flex justify-between"><dt className="text-slate-500">Split</dt><dd className="capitalize">{expense.split_type}</dd></div>
            <div className="flex justify-between"><dt className="text-slate-500">Added</dt><dd>{formatDate(expense.created_at)}</dd></div>
          </dl>
          {expense.notes && <p className="rounded-lg bg-slate-50 p-3 text-sm text-slate-600">{expense.notes}</p>}
        </Card>
        <Card className="sm:col-span-3">
          <div className="border-b border-slate-100 px-5 py-4">
            <h2 className="text-base font-semibold">Shares ({expense.splits.length})</h2>
          </div>
          <ul className="divide-y divide-slate-100">
            {expense.splits.map((s) => (
              <li key={s.user_id} className="flex items-center gap-3 px-5 py-3 text-sm">
                <Avatar name={s.user_name} size="sm" />
                <span className="flex-1">
                  {s.user_name} {s.user_id === user.id && <span className="text-slate-400">(you)</span>}
                  {s.user_id === expense.paid_by && <span className="ml-2 text-xs text-emerald-700">paid</span>}
                </span>
                <span className="amount font-medium">{formatPaise(s.share_amount_paise)}</span>
              </li>
            ))}
          </ul>
          <p className="border-t border-slate-100 px-5 py-3 text-xs text-slate-500">
            {expense.paid_by_name} paid the full {formatPaise(expense.amount_paise)}; everyone else owes them their share.
          </p>
        </Card>
      </div>
    </div>
  )
}
