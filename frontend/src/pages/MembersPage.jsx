import { useCallback, useEffect, useState } from 'react'
import { useNavigate, useOutletContext } from 'react-router-dom'
import { groupsApi } from '../api/api'
import { useAuth } from '../context/AuthContext'
import { formatDate, getErrorMessage } from '../utils/format'
import { Avatar, Button, Card, ErrorAlert, Field, SuccessAlert } from '../components/ui'

export default function MembersPage() {
  const { group, reloadGroup } = useOutletContext()
  const { user } = useAuth()
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [inviting, setInviting] = useState(false)
  const [deletingGroup, setDeletingGroup] = useState(false)
  const [pendingInvites, setPendingInvites] = useState([])
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const isAdmin = group.my_role === 'admin'

  const loadInvites = useCallback(() => {
    if (!isAdmin) {
      setPendingInvites([])
      return Promise.resolve()
    }
    return groupsApi.invites(group.id).then(setPendingInvites).catch(() => {})
  }, [group.id, isAdmin])

  useEffect(() => {
    loadInvites()
  }, [loadInvites])

  async function handleInvite(event) {
    event.preventDefault()
    if (!email.trim()) return
    setInviting(true)
    setError('')
    setSuccess('')
    try {
      const invite = await groupsApi.inviteMember(group.id, email.trim())
      setSuccess(`Invitation sent to ${invite.invited_user_name}. They will join ${group.name} once they accept.`)
      setEmail('')
      await loadInvites()
    } catch (err) {
      setError(getErrorMessage(err))
    } finally {
      setInviting(false)
    }
  }

  async function handleCancelInvite(invite) {
    setError('')
    setSuccess('')
    try {
      await groupsApi.cancelInvite(group.id, invite.id)
      setSuccess(`Cancelled invitation for ${invite.invited_user_name}.`)
      await loadInvites()
    } catch (err) {
      setError(getErrorMessage(err))
    }
  }

  async function handleRemove(member) {
    const leaving = member.user_id === user?.id
    const question = leaving ? `Leave "${group.name}"?` : `Remove ${member.name} from "${group.name}"?`
    if (!window.confirm(question)) return
    setError('')
    setSuccess('')
    try {
      await groupsApi.removeMember(group.id, member.user_id)
      if (leaving) navigate('/groups', { replace: true })
      else {
        setSuccess(`${member.name} was removed.`)
        await reloadGroup()
      }
    } catch (err) {
      setError(getErrorMessage(err))
    }
  }

  async function handleDeleteGroup() {
    if (
      !window.confirm(
        `Delete "${group.name}"? This will permanently delete the group and its expense history. All balances must be ₹0.00.`,
      )
    ) {
      return
    }
    setDeletingGroup(true)
    setError('')
    setSuccess('')
    try {
      await groupsApi.remove(group.id)
      navigate('/groups', { replace: true })
    } catch (err) {
      setError(getErrorMessage(err))
      setDeletingGroup(false)
    }
  }

  return (
    <div className="grid gap-6 lg:grid-cols-3">
      <div className="space-y-6 lg:col-span-2">
        <Card>
          <div className="border-b border-slate-100 px-5 py-4">
            <h2 className="text-base font-semibold">Members ({group.members.length})</h2>
          </div>
          <ul className="divide-y divide-slate-100">
            {group.members.map((m) => (
              <li key={m.user_id} className="flex items-center gap-3 px-5 py-3">
                <Avatar name={m.name} />
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-medium">
                    {m.name} {m.user_id === user?.id && <span className="text-slate-400">(you)</span>}
                  </p>
                  <p className="truncate text-xs text-slate-500">{m.email} · joined {formatDate(m.joined_at)}</p>
                </div>
                <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${m.role === 'admin' ? 'bg-brand-50 text-brand-800' : 'bg-slate-100 text-slate-600'}`}>
                  {m.role}
                </span>
                {(isAdmin || m.user_id === user?.id) && group.members.length > 1 && (
                  <Button variant="ghost" className="px-2 text-xs" onClick={() => handleRemove(m)}>
                    {m.user_id === user?.id ? 'Leave' : 'Remove'}
                  </Button>
                )}
              </li>
            ))}
          </ul>
        </Card>

        {isAdmin && pendingInvites.length > 0 && (
          <Card>
            <div className="border-b border-slate-100 px-5 py-4">
              <h2 className="text-base font-semibold">Pending invitations ({pendingInvites.length})</h2>
              <p className="text-xs text-slate-500">Waiting for these users to accept.</p>
            </div>
            <ul className="divide-y divide-slate-100">
              {pendingInvites.map((inv) => (
                <li key={inv.id} className="flex items-center gap-3 px-5 py-3">
                  <Avatar name={inv.invited_user_name} />
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-medium">{inv.invited_user_name}</p>
                    <p className="truncate text-xs text-slate-500">
                      {inv.invited_user_email} · invited {formatDate(inv.created_at)}
                    </p>
                  </div>
                  <span className="rounded-full bg-amber-50 px-2 py-0.5 text-xs font-medium text-amber-800">
                    pending
                  </span>
                  <Button variant="ghost" className="px-2 text-xs" onClick={() => handleCancelInvite(inv)}>
                    Cancel
                  </Button>
                </li>
              ))}
            </ul>
          </Card>
        )}
      </div>

      <div className="space-y-4">
        <SuccessAlert message={success} />
        <ErrorAlert message={error} />
        {isAdmin ? (
          <Card className="p-5">
            <h2 className="text-base font-semibold">Invite a member</h2>
            <p className="mt-1 text-xs text-slate-500">
              They must already have a SettleUp account and accept the invitation before joining.
            </p>
            <form onSubmit={handleInvite} className="mt-4 space-y-3">
              <Field label="Email address" htmlFor="memberEmail">
                <input id="memberEmail" type="email" className="input" value={email}
                  onChange={(e) => setEmail(e.target.value)} placeholder="friend@example.com" />
              </Field>
              <Button type="submit" className="w-full" loading={inviting}>Send invite</Button>
            </form>
          </Card>
        ) : (
          <Card className="p-5 text-sm text-slate-600">Only group admins can invite or remove members.</Card>
        )}
        <Card className="p-5 text-xs leading-relaxed text-slate-500">
          A member can only be removed (or leave) once their balance in this group is zero. If the only admin leaves,
          the longest-standing member becomes admin.
        </Card>
        {isAdmin && (
          <Card className="border-rose-200 p-5">
            <h2 className="text-base font-semibold text-rose-800">Delete group</h2>
            <p className="mt-1 text-xs leading-relaxed text-slate-600">
              Permanently delete <strong>{group.name}</strong>. Allowed only when every member&apos;s balance is ₹0.00.
            </p>
            <Button
              variant="danger"
              className="mt-4 w-full"
              loading={deletingGroup}
              onClick={handleDeleteGroup}
            >
              Delete group
            </Button>
          </Card>
        )}
      </div>
    </div>
  )
}
