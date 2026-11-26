import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { groupsApi } from '../api/api'
import { useAuth } from '../context/AuthContext'
import { formatDate } from '../utils/format'
import { Avatar, Button, ButtonLink, Card, PageHeader } from '../components/ui'

export default function ProfilePage() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const [groups, setGroups] = useState(null)

  useEffect(() => {
    groupsApi.list().then(setGroups).catch(() => setGroups([]))
  }, [])

  return (
    <div className="mx-auto max-w-2xl">
      <PageHeader title="Profile" />
      <Card className="p-6">
        <div className="flex items-center gap-4">
          <Avatar name={user.name} size="lg" />
          <div>
            <p className="text-lg font-semibold">{user.name}</p>
            <p className="text-sm text-slate-500">{user.email}</p>
          </div>
        </div>
        <dl className="mt-6 grid gap-4 border-t border-slate-100 pt-6 text-sm sm:grid-cols-3">
          <div><dt className="text-slate-500">Member since</dt><dd className="font-medium">{formatDate(user.created_at)}</dd></div>
          <div><dt className="text-slate-500">Groups</dt><dd className="font-medium">{groups ? groups.length : '…'}</dd></div>
          <div><dt className="text-slate-500">Admin of</dt><dd className="font-medium">{groups ? groups.filter((g) => g.my_role === 'admin').length : '…'}</dd></div>
        </dl>
      </Card>
      {groups && groups.length > 0 && (
        <Card className="mt-6">
          <ul className="divide-y divide-slate-100">
            {groups.map((g) => (
              <li key={g.id}>
                <Link to={`/groups/${g.id}`} className="flex justify-between px-6 py-3 text-sm hover:bg-slate-50">
                  <span>{g.name}</span>
                  <span className="text-slate-500">{g.my_role}</span>
                </Link>
              </li>
            ))}
          </ul>
        </Card>
      )}
      <div className="mt-6 flex justify-end">
        <Button variant="secondary" onClick={() => { logout(); navigate('/login') }}>Log out</Button>
      </div>
    </div>
  )
}

export function NotFoundPage() {
  return (
    <div className="py-20 text-center">
      <p className="text-sm font-semibold text-brand-700">404</p>
      <h1 className="mt-2 text-2xl font-bold">Page not found</h1>
      <div className="mt-6"><ButtonLink to="/dashboard">Go to dashboard</ButtonLink></div>
    </div>
  )
}
