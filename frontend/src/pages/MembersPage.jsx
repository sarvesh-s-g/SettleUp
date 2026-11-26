import { useState } from 'react'
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
  const [adding, setAdding] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const isAdmin = group.my_role === 'admin'

  async function handleAdd(event) {
    event.preventDefault()
    if (!email.trim()) return
    setAdding(true)
    setError('')
    setSuccess('')
    try {
      const member = await groupsApi.addMember(group.id, email.trim())
      setSuccess(`${member.name} was added to ${group.name}.`)
      setEmail('')
      await reloadGroup()
    } catch (err) {
      setError(getErrorMessage(err))
    } finally {
      setAdding(false)
    }
  }

  async function handleRemove(member) {
    const leaving = member.user_id === user.id
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

  return (
    <div className="grid gap-6 lg:grid-cols-3">
      <Card className="lg:col-span-2">
        <div className="border-b border-slate-100 px-5 py-4">
          <h2 className="text-base font-semibold">Members ({group.members.length})</h2>
        </div>
        <ul className="divide-y divide-slate-100">
          {group.members.map((m) => (
            <li key={m.user_id} className="flex items-center gap-3 px-5 py-3">
              <Avatar name={m.name} />
              <div className="min-w-0 flex-1">
                <p className="truncate text-sm font-medium">
                  {m.name} {m.user_id === user.id && <span className="text-slate-400">(you)</span>}
                </p>
                <p className="truncate text-xs text-slate-500">{m.email} · joined {formatDate(m.joined_at)}</p>
              </div>
              <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${m.role === 'admin' ? 'bg-brand-50 text-brand-800' : 'bg-slate-100 text-slate-600'}`}>
                {m.role}
              </span>
              {(isAdmin || m.user_id === user.id) && group.members.length > 1 && (
                <Button variant="ghost" className="px-2 text-xs" onClick={() => handleRemove(m)}>
                  {m.user_id === user.id ? 'Leave' : 'Remove'}
                </Button>
              )}
            </li>
          ))}
        </ul>
      </Card>

      <div className="space-y-4">
        <SuccessAlert message={success} />
        <ErrorAlert message={error} />
        {isAdmin ? (
          <Card className="p-5">
            <h2 className="text-base font-semibold">Add a member</h2>
            <p className="mt-1 text-xs text-slate-500">They must already have a SettleUp account.</p>
            <form onSubmit={handleAdd} className="mt-4 space-y-3">
              <Field label="Email address" htmlFor="memberEmail">
                <input id="memberEmail" type="email" className="input" value={email}
                  onChange={(e) => setEmail(e.target.value)} placeholder="friend@example.com" />
              </Field>
              <Button type="submit" className="w-full" loading={adding}>Add member</Button>
            </form>
          </Card>
        ) : (
          <Card className="p-5 text-sm text-slate-600">Only group admins can add or remove members.</Card>
        )}
        <Card className="p-5 text-xs leading-relaxed text-slate-500">
          A member can only be removed (or leave) once their balance in this group is zero. If the only admin leaves,
          the longest-standing member becomes admin.
        </Card>
      </div>
    </div>
  )
}
