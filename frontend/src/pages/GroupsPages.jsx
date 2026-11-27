import { useCallback, useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { groupsApi, invitesApi } from '../api/api'
import { balanceLabel, formatDate, getErrorMessage } from '../utils/format'
import PendingInvitesCard from '../components/PendingInvitesCard'
import {
  BalanceAmount, Button, ButtonLink, Card, EmptyState, ErrorAlert, Field, LoadingState, PageHeader, SuccessAlert,
} from '../components/ui'

export function GroupsPage() {
  const [groups, setGroups] = useState(null)
  const [invites, setInvites] = useState([])
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')

  const load = useCallback(() => {
    setError('')
    Promise.all([groupsApi.list(), invitesApi.list()])
      .then(([groupList, inviteList]) => {
        setGroups(groupList)
        setInvites(inviteList)
      })
      .catch((err) => setError(getErrorMessage(err)))
  }, [])
  useEffect(load, [load])

  async function handleInviteResponded({ invite, accepted }) {
    setNotice(accepted ? `You joined "${invite.group_name}".` : `Declined invitation to "${invite.group_name}".`)
    await load()
  }

  return (
    <>
      <PageHeader title="Your groups" subtitle="Flats, trips, teams — anywhere you share costs."
        actions={<ButtonLink to="/groups/new">+ New group</ButtonLink>} />
      <div className="mb-4 space-y-3">
        <SuccessAlert message={notice} />
        <ErrorAlert message={error} onRetry={load} />
      </div>
      <PendingInvitesCard invites={invites} onResponded={handleInviteResponded} />
      {!groups && !error && <LoadingState />}
      {groups && groups.length === 0 && (
        <EmptyState title="No groups yet" description="Create your first group and invite your roommates by their email."
          action={<ButtonLink to="/groups/new">Create a group</ButtonLink>} />
      )}
      {groups && groups.length > 0 && (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {groups.map((g) => (
            <Link key={g.id} to={`/groups/${g.id}`} className="card group p-5 transition hover:border-brand-500 hover:shadow-md">
              <div className="flex items-start justify-between">
                <h2 className="font-semibold text-slate-900 group-hover:text-brand-800">{g.name}</h2>
                {g.my_role === 'admin' && (
                  <span className="rounded-full bg-brand-50 px-2 py-0.5 text-xs font-medium text-brand-800">Admin</span>
                )}
              </div>
              <p className="mt-1 text-xs text-slate-500">{g.member_count} members · since {formatDate(g.created_at)}</p>
              <div className="mt-5 border-t border-slate-100 pt-4">
                <p className="text-xs text-slate-500">You {balanceLabel(g.my_balance_paise)}</p>
                <BalanceAmount paise={g.my_balance_paise} className="text-lg" />
              </div>
            </Link>
          ))}
        </div>
      )}
    </>
  )
}

export function CreateGroupPage() {
  const navigate = useNavigate()
  const [name, setName] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  async function handleSubmit(event) {
    event.preventDefault()
    if (!name.trim()) return setError('Please give the group a name.')
    setLoading(true)
    setError('')
    try {
      const group = await groupsApi.create({ name: name.trim() })
      navigate(`/groups/${group.id}/members`, { replace: true })
    } catch (err) {
      setError(getErrorMessage(err))
      setLoading(false)
    }
  }

  return (
    <div className="mx-auto max-w-lg">
      <PageHeader title="Create a group" subtitle="You'll be the group's admin and can invite members next." />
      <Card className="p-6">
        <form onSubmit={handleSubmit} className="space-y-4">
          <Field label="Group name" htmlFor="groupName" hint='For example "Room 204" or "Goa Trip"'>
            <input id="groupName" className="input" value={name} onChange={(e) => setName(e.target.value)} maxLength={100} autoFocus />
          </Field>
          <ErrorAlert message={error} />
          <div className="flex justify-end gap-2">
            <ButtonLink to="/groups" variant="secondary">Cancel</ButtonLink>
            <Button type="submit" loading={loading}>Create group</Button>
          </div>
        </form>
      </Card>
    </div>
  )
}
