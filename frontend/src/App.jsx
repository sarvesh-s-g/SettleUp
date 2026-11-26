import { Navigate, Route, Routes } from 'react-router-dom'
import Layout from './components/Layout'
import GroupLayout from './components/GroupLayout'
import ProtectedRoute, { GuestRoute } from './components/ProtectedRoute'
import { LoginPage, RegisterPage } from './pages/AuthPages'
import DashboardPage from './pages/DashboardPage'
import { CreateGroupPage, GroupsPage } from './pages/GroupsPages'
import GroupExpensesPage from './pages/GroupExpensesPage'
import MembersPage from './pages/MembersPage'
import { BalancesPage, SettleUpPage, SettlementHistoryPage } from './pages/SettlementPages'
import { AddExpensePage, EditExpensePage, ExpenseDetailPage } from './pages/ExpensePages'
import ProfilePage, { NotFoundPage } from './pages/ProfilePage'

export default function App() {
  return (
    <Routes>
      {/* Only for logged-out visitors */}
      <Route element={<GuestRoute />}>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/register" element={<RegisterPage />} />
      </Route>

      {/* Everything else requires a valid JWT */}
      <Route element={<ProtectedRoute />}>
        <Route element={<Layout />}>
          <Route path="/" element={<Navigate to="/dashboard" replace />} />
          <Route path="/dashboard" element={<DashboardPage />} />
          <Route path="/groups" element={<GroupsPage />} />
          <Route path="/groups/new" element={<CreateGroupPage />} />
          <Route path="/groups/:groupId" element={<GroupLayout />}>
            <Route index element={<GroupExpensesPage />} />
            <Route path="members" element={<MembersPage />} />
            <Route path="balances" element={<BalancesPage />} />
            <Route path="settle" element={<SettleUpPage />} />
            <Route path="settlements" element={<SettlementHistoryPage />} />
            <Route path="expenses/new" element={<AddExpensePage />} />
          </Route>
          <Route path="/expenses/:expenseId" element={<ExpenseDetailPage />} />
          <Route path="/expenses/:expenseId/edit" element={<EditExpensePage />} />
          <Route path="/profile" element={<ProfilePage />} />
          <Route path="*" element={<NotFoundPage />} />
        </Route>
      </Route>
    </Routes>
  )
}
