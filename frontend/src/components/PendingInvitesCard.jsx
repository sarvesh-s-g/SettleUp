import { useState } from 'react'
import { invitesApi } from '../api/api'
import { formatDate, getErrorMessage } from '../utils/format'
import { Button, Card, ErrorAlert } from './ui'

/** Shared banner showing pending incoming group invitations with Accept / Decline actions. */
export default function PendingInvitesCard({ invites, onResponded }) {
  const [busy, setBusy] = useState(null)
  const [error, setError] = useState('')

  if (!invites || invites.length === 0) return null

  async function respond(invite, accept) {
    setBusy({ id: invite.id, accept })
    setError('')
    try {
      if (accept) {
        await invitesApi.accept(invite.id)
      } else {
        await invitesApi.decline(invite.id)
      }
      await onResponded({ invite, accepted: accept })
    } catch (err) {
      setError(getErrorMessage(err))
    } finally {
      setBusy(null)
    }
  }

  return (
    <Card className="mb-6 border-brand-200 bg-brand-50/40">
      <div className="border-b border-brand-100 px-5 py-3.5">
        <h2 className="text-base font-semibold text-slate-900">
          Pending group invitations ({invites.length})
        </h2>
        <p className="text-xs text-slate-600">
          Accept an invitation to join the group and start sharing expenses.
        </p>
      </div>
      {error && (
        <div className="px-5 pt-3">
          <ErrorAlert message={error} />
        </div>
      )}
      <ul className="divide-y divide-brand-100">
        {invites.map((inv) => {
          const isDeclining = busy?.id === inv.id && !busy.accept
          const isAccepting = busy?.id === inv.id && busy.accept
          return (
            <li key={inv.id} className="flex flex-col gap-3 px-5 py-3.5 sm:flex-row sm:items-center sm:justify-between">
              <div className="min-w-0">
                <p className="font-medium text-slate-900">{inv.group_name}</p>
                <p className="text-xs text-slate-600">
                  Invited by <strong>{inv.invited_by_name}</strong> · {formatDate(inv.created_at)}
                </p>
              </div>
              <div className="flex shrink-0 gap-2">
                <Button
                  variant="secondary"
                  className="px-3 py-1.5 text-xs"
                  disabled={busy !== null}
                  loading={isDeclining}
                  onClick={() => respond(inv, false)}
                >
                  Decline
                </Button>
                <Button
                  className="px-3 py-1.5 text-xs"
                  disabled={busy !== null}
                  loading={isAccepting}
                  onClick={() => respond(inv, true)}
                >
                  Accept
                </Button>
              </div>
            </li>
          )
        })}
      </ul>
    </Card>
  )
}
