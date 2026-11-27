import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { Bar, BarChart, CartesianGrid, Cell, LabelList, Legend, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { dashboardApi, invitesApi } from '../api/api'
import { useAuth } from '../context/AuthContext'
import { CATEGORY_COLORS, categoryLabel, formatDate, formatMonth, getErrorMessage, todayISO } from '../utils/format'
import { formatPaise } from '../utils/money'
import PendingInvitesCard from '../components/PendingInvitesCard'
import {
  BalanceAmount, ButtonLink, Card, CategoryBadge, EmptyState, ErrorAlert, LoadingState, PageHeader, StatCard,
} from '../components/ui'

const rupeeTick = (paise) => `₹${Math.round(paise / 100).toLocaleString('en-IN')}`
const GROUP_CHART_COLORS = ['#0f766e', '#d97706', '#2563eb', '#9333ea', '#dc2626', '#475569', '#059669', '#c2410c']
const ANALYSIS_RANGES = [
  { months: 1, label: 'This month' },
  { months: 3, label: 'Last 3 months' },
  { months: 6, label: 'Last 6 months' },
  { months: 12, label: 'Last 12 months' },
]

const groupShareKey = (groupId) => `group_${groupId}`

function renderMonthlyTotalLabel(groupKey, groupKeys, monthly) {
  return ({ x, y, width, index }) => {
    const row = monthly[index]
    const topGroupKey = [...groupKeys].reverse().find((key) => row?.[key] > 0)
    if (groupKey !== topGroupKey || !row?.my_share_paise) return null
    return (
      <text x={x + width / 2} y={y - 8} fill="#475569" textAnchor="middle" fontSize={10}>
        {formatPaise(row.my_share_paise)}
      </text>
    )
  }
}

function getAnalysisDates(months) {
  const now = new Date()
  const start = new Date(now.getFullYear(), now.getMonth() - months + 1, 1)
  const startDate = `${start.getFullYear()}-${String(start.getMonth() + 1).padStart(2, '0')}-01`
  return { start_date: startDate, end_date: todayISO() }
}

export default function DashboardPage() {
  const { user } = useAuth()
  const [data, setData] = useState(null)
  const [invites, setInvites] = useState([])
  const [error, setError] = useState('')
  const [rangeMonths, setRangeMonths] = useState(6)
  const { start_date: startDate, end_date: endDate } = getAnalysisDates(rangeMonths)

  const load = useCallback(() => {
    setError('')
    Promise.all([dashboardApi.get({ start_date: startDate, end_date: endDate }), invitesApi.list()])
      .then(([dashboard, inviteList]) => {
        setData(dashboard)
        setInvites(inviteList)
      })
      .catch((err) => setError(getErrorMessage(err)))
  }, [startDate, endDate])
  useEffect(load, [load])

  if (error) return <ErrorAlert message={error} onRetry={load} />
  if (!data) return <LoadingState label="Loading dashboard…" />

  const net = data.my_net_balance_paise
  const firstName = user?.name?.split(' ')[0]

  if (data.group_count === 0) {
    return (
      <>
        <PageHeader title={`Hi ${firstName} 👋`} subtitle="Let's set up your first group." />
        <PendingInvitesCard invites={invites} onResponded={load} />
        <EmptyState
          title="You're not in any groups yet"
          description="Create a group for your flat, trip or team, then invite the people you share expenses with."
          action={<ButtonLink to="/groups/new">Create a group</ButtonLink>}
        />
      </>
    )
  }

  const chartGroups = [...new Map(
    data.monthly_summary
      .flatMap((month) => month.group_shares)
      .map((group) => [group.group_id, group]),
  ).values()].sort((a, b) => a.group_id - b.group_id)
  const groupKeys = chartGroups.map((group) => groupShareKey(group.group_id))
  const monthly = data.monthly_summary.map((month) => ({
    ...month,
    ...Object.fromEntries(
      month.group_shares.map((group) => [groupShareKey(group.group_id), group.my_share_paise]),
    ),
    label: formatMonth(month.month),
  }))

  return (
    <>
      <PageHeader
        title={`Hi ${firstName} 👋`}
        subtitle="Here's where things stand across all your groups."
        actions={<ButtonLink to="/groups">View groups</ButtonLink>}
      />
      <PendingInvitesCard invites={invites} onResponded={load} />

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          label="Your portion"
          value={formatPaise(data.my_total_share_paise)}
          hint="Part assigned to you on group expenses (all time)"
        />
        <StatCard
          label="Bills you paid upfront"
          value={formatPaise(data.my_total_paid_paise)}
          hint="Group bills you paid (all time; includes others' shares, not repayments)"
        />
        <StatCard
          label={net > 0 ? 'Others owe you' : net < 0 ? 'You owe others' : 'Balance'}
          value={formatPaise(Math.abs(net))}
          tone={net > 0 ? 'positive' : net < 0 ? 'negative' : 'default'}
          hint={net === 0 ? 'All groups are settled up' : 'Current amount after recorded repayments'}
        />
        <StatCard label="Groups" value={data.group_count} hint="Groups you belong to" />
      </div>

      <section className="mt-6">
        <div className="mb-3 flex flex-wrap items-end justify-between gap-3">
          <div>
            <h2 className="text-base font-semibold">Spending analysis</h2>
            <p className="text-xs text-slate-500">
              {formatDate(startDate)} – {formatDate(endDate)} · Charts show your share
            </p>
          </div>
          <label className="flex items-center gap-2 text-sm font-medium text-slate-700">
            Time range
            <select
              aria-label="Analysis time range"
              className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm"
              value={rangeMonths}
              onChange={(event) => setRangeMonths(Number(event.target.value))}
            >
              {ANALYSIS_RANGES.map(({ months, label }) => (
                <option key={months} value={months}>{label}</option>
              ))}
            </select>
          </label>
        </div>
        <div className="grid gap-6 lg:grid-cols-3">
          <Card className="p-5 lg:col-span-2">
            <h2 className="text-base font-semibold">Your monthly portion by group</h2>
            <p className="text-xs text-slate-500">Bar totals show your portion that month; colors identify each group.</p>
            <div className="mt-4 h-64">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={monthly} margin={{ left: 8, right: 8 }}>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" />
                  <XAxis dataKey="label" tickLine={false} axisLine={false} fontSize={12} />
                  <YAxis tickFormatter={rupeeTick} tickLine={false} axisLine={false} fontSize={12} width={70} />
                  <Tooltip formatter={(value, name) => [formatPaise(value), name]} />
                  <Legend iconType="circle" wrapperStyle={{ fontSize: 12 }} />
                  {chartGroups.map((group, index) => {
                    const key = groupShareKey(group.group_id)
                    return (
                      <Bar
                        key={group.group_id}
                        isAnimationActive={false}
                        dataKey={key}
                        name={group.group_name}
                        stackId="monthly-share"
                        fill={GROUP_CHART_COLORS[index % GROUP_CHART_COLORS.length]}
                      >
                        <LabelList
                          dataKey="my_share_paise"
                          content={renderMonthlyTotalLabel(key, groupKeys, monthly)}
                        />
                      </Bar>
                    )
                  })}
                </BarChart>
              </ResponsiveContainer>
            </div>
          </Card>

          <Card className="p-5">
            <h2 className="text-base font-semibold">Your spending by category</h2>
            {data.category_breakdown.length === 0 ? (
              <p className="mt-6 text-sm text-slate-500">No expenses involving you in this period.</p>
            ) : (
              <>
                <div className="h-44">
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie isAnimationActive={false} data={data.category_breakdown} dataKey="my_share_paise" nameKey="category" innerRadius={45} outerRadius={75} paddingAngle={2}>
                        {data.category_breakdown.map((c) => <Cell key={c.category} fill={CATEGORY_COLORS[c.category]} />)}
                      </Pie>
                      <Tooltip formatter={(v, name) => [formatPaise(v), categoryLabel(name)]} />
                    </PieChart>
                  </ResponsiveContainer>
                </div>
                <ul className="mt-2 space-y-1.5 text-sm">
                  {data.category_breakdown.map((c) => (
                    <li key={c.category} className="flex items-center justify-between">
                      <CategoryBadge category={c.category} />
                      <span className="amount text-slate-700">{formatPaise(c.my_share_paise)}</span>
                    </li>
                  ))}
                </ul>
              </>
            )}
          </Card>
        </div>
      </section>

      <div className="mt-6 grid gap-6 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <div className="border-b border-slate-100 px-5 py-4">
            <h2 className="text-base font-semibold">Recent expenses</h2>
          </div>
          {data.recent_expenses.length === 0 ? (
            <p className="px-5 py-6 text-sm text-slate-500">No expenses yet.</p>
          ) : (
            <ul className="divide-y divide-slate-100">
              {data.recent_expenses.map((e) => (
                <li key={e.id}>
                  <Link to={`/expenses/${e.id}`} className="flex items-center justify-between gap-4 px-5 py-3 hover:bg-slate-50">
                    <div className="min-w-0">
                      <p className="truncate text-sm font-medium text-slate-900">{e.description}</p>
                      <p className="truncate text-xs text-slate-500">
                        {e.group_name} · {e.paid_by_name} paid · {formatDate(e.expense_date)}
                      </p>
                    </div>
                    <div className="shrink-0 text-right">
                      <p className="amount text-sm font-semibold">{formatPaise(e.amount_paise)}</p>
                      <p className="amount text-xs text-slate-500">
                        {e.my_share_paise ? `your portion ${formatPaise(e.my_share_paise)}` : 'not involved'}
                      </p>
                    </div>
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </Card>

        <div className="space-y-6">
          <Card>
            <div className="border-b border-slate-100 px-5 py-4">
              <h2 className="text-base font-semibold">Suggested settlements</h2>
              <p className="text-xs text-slate-500">Payments that involve you</p>
            </div>
            {data.suggested_settlements.length === 0 ? (
              <p className="px-5 py-6 text-sm text-slate-500">Nothing to settle — nice!</p>
            ) : (
              <ul className="divide-y divide-slate-100">
                {data.suggested_settlements.map((s, i) => {
                  const iPay = s.from_user_id === user.id
                  return (
                    <li key={i} className="px-5 py-3">
                      <Link to={`/groups/${s.group_id}/settle`} className="block">
                        <p className="text-sm">
                          {iPay ? <>You pay <strong>{s.to_name}</strong></> : <><strong>{s.from_name}</strong> pays you</>}
                        </p>
                        <div className="mt-0.5 flex justify-between text-xs text-slate-500">
                          <span>{s.group_name}</span>
                          <span className={`amount font-semibold ${iPay ? 'text-rose-700' : 'text-emerald-700'}`}>{formatPaise(s.amount_paise)}</span>
                        </div>
                      </Link>
                    </li>
                  )
                })}
              </ul>
            )}
          </Card>

          <Card>
            <div className="border-b border-slate-100 px-5 py-4">
              <h2 className="text-base font-semibold">Your balance by group</h2>
            </div>
            <ul className="divide-y divide-slate-100">
              {data.group_balances.map((g) => (
                <li key={g.group_id}>
                  <Link to={`/groups/${g.group_id}/balances`} className="flex justify-between px-5 py-3 text-sm hover:bg-slate-50">
                    <span>{g.group_name}</span>
                    <BalanceAmount paise={g.net_balance_paise} />
                  </Link>
                </li>
              ))}
            </ul>
          </Card>
        </div>
      </div>
    </>
  )
}
