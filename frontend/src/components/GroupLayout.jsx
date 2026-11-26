import { useCallback, useEffect, useState } from 'react'
import { Link, NavLink, Outlet, useParams } from 'react-router-dom'
import { groupsApi } from '../api/api'
import { formatPaise } from '../utils/money'
import { getErrorMessage } from '../utils/format'
import { ButtonLink, ErrorAlert, LoadingState } from './ui'

const tabs = [
  { to: '', label: 'Expenses', end: true },
  { to: 'balances', label: 'Balances' },
  { to: 'settle', label: 'Settle up' },
  { to: 'settlements', label: 'History' },
  { to: 'members', label: 'Members' },
]

/** Loads the group once and shares it with every group tab via <Outlet context>. */
export default function GroupLayout() {
  const { groupId } = useParams()
  const [group, setGroup] = useState(null)
  const [error, setError] = useState('')

  const reloadGroup = useCallback(() => {
    setError('')
    return groupsApi
      .get(groupId)
      .then(setGroup)
      .catch((err) => setError(getErrorMessage(err)))
  }, [groupId])

  useEffect(() => {
    setGroup(null)
    reloadGroup()
  }, [reloadGroup])

  if (error) {
    return (
      <div className="space-y-4">
        <ErrorAlert message={error} onRetry={reloadGroup} />
        <Link to="/groups" className="text-sm font-medium text-brand-700">
          ← Back to groups
        </Link>
      </div>
    )
  }
  if (!group) return <LoadingState label="Loading group…" />

  return (
    <div>
      <Link to="/groups" className="text-sm font-medium text-slate-500 hover:text-slate-800">
        ← All groups
      </Link>
      <div className="mt-3 mb-6 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">{group.name}</h1>
          <p className="mt-1 text-sm text-slate-500">
            {group.member_count} members · {group.expense_count} expenses ·{' '}
            <span className="amount">{formatPaise(group.total_spending_paise)}</span> total spent
          </p>
        </div>
        <ButtonLink to={`/groups/${group.id}/expenses/new`}>+ Add expense</ButtonLink>
      </div>
      <nav className="mb-6 flex gap-1 overflow-x-auto overflow-y-hidden shadow-[inset_0_-1px_0_#e2e8f0]" aria-label="Group sections">
        {tabs.map((tab) => (
          <NavLink
            key={tab.label}
            to={tab.to}
            end={tab.end}
            className={({ isActive }) =>
              `whitespace-nowrap border-b-2 px-3 py-2.5 text-sm font-medium transition ${
                isActive
                  ? 'border-brand-700 text-brand-800'
                  : 'border-transparent text-slate-500 hover:border-slate-300 hover:text-slate-800'
              }`
            }
          >
            {tab.label}
          </NavLink>
        ))}
      </nav>
      <Outlet context={{ group, reloadGroup }} />
    </div>
  )
}
