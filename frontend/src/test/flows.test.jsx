// Component tests for important user flows. The API module is mocked, so these
// tests check the UI logic (validation, error display, routing) in isolation.
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

vi.mock('../api/api', () => ({
  authApi: { login: vi.fn(), register: vi.fn(), me: vi.fn() },
}))

import { authApi } from '../api/api'
import { AuthProvider } from '../context/AuthContext'
import ProtectedRoute from '../components/ProtectedRoute'
import { LoginPage } from '../pages/AuthPages'
import ExpenseForm from '../components/ExpenseForm'

function renderWithAuth(ui, { route = '/' } = {}) {
  return render(
    <MemoryRouter initialEntries={[route]}>
      <AuthProvider>{ui}</AuthProvider>
    </MemoryRouter>,
  )
}

beforeEach(() => {
  vi.clearAllMocks()
  localStorage.clear()
})

describe('ProtectedRoute', () => {
  it('redirects anonymous visitors to the login page', () => {
    renderWithAuth(
      <Routes>
        <Route path="/login" element={<p>login screen</p>} />
        <Route element={<ProtectedRoute />}>
          <Route path="/dashboard" element={<p>secret dashboard</p>} />
        </Route>
      </Routes>,
      { route: '/dashboard' },
    )
    expect(screen.getByText('login screen')).toBeInTheDocument()
    expect(screen.queryByText('secret dashboard')).not.toBeInTheDocument()
  })
})

describe('LoginPage', () => {
  it('shows the server error message when login fails', async () => {
    authApi.login.mockRejectedValue({ response: { status: 401, data: { detail: 'Incorrect email or password' } } })
    renderWithAuth(<LoginPage />, { route: '/login' })

    await userEvent.type(screen.getByLabelText('Email'), 'sarvesh@example.com')
    await userEvent.type(screen.getByLabelText('Password'), 'wrong-password')
    await userEvent.click(screen.getByRole('button', { name: 'Log in' }))

    expect(await screen.findByRole('alert')).toHaveTextContent('Incorrect email or password')
    expect(authApi.login).toHaveBeenCalledWith({ email: 'sarvesh@example.com', password: 'wrong-password' })
  })

  it('stores the token after a successful login', async () => {
    authApi.login.mockResolvedValue({
      access_token: 'jwt-token', token_type: 'bearer',
      user: { id: 1, name: 'Sarvesh', email: 'sarvesh@example.com', created_at: '2026-11-01T00:00:00Z' },
    })
    renderWithAuth(
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/dashboard" element={<p>welcome dashboard</p>} />
      </Routes>,
      { route: '/login' },
    )
    await userEvent.type(screen.getByLabelText('Email'), 'sarvesh@example.com')
    await userEvent.type(screen.getByLabelText('Password'), 'Password@123')
    await userEvent.click(screen.getByRole('button', { name: 'Log in' }))

    expect(await screen.findByText('welcome dashboard')).toBeInTheDocument()
    expect(localStorage.getItem('settleup_token')).toBe('jwt-token')
  })
})

describe('ExpenseForm', () => {
  const members = [
    { user_id: 1, name: 'Sarvesh' },
    { user_id: 2, name: 'Rahul' },
    { user_id: 3, name: 'Kiran' },
    { user_id: 4, name: 'Aman' },
  ]

  it('sends an equal split as integer paise with all members selected', async () => {
    const onSubmit = vi.fn().mockResolvedValue()
    render(<ExpenseForm members={members} currentUserId={1} submitLabel="Save" onSubmit={onSubmit} />)

    await userEvent.type(screen.getByLabelText('Description'), 'Groceries')
    await userEvent.type(screen.getByLabelText('Amount (₹)'), '1200')
    expect(screen.getAllByText('₹300.00')).toHaveLength(4) // live preview
    await userEvent.click(screen.getByRole('button', { name: 'Save' }))

    await waitFor(() => expect(onSubmit).toHaveBeenCalled())
    const payload = onSubmit.mock.calls[0][0]
    expect(payload).toMatchObject({ description: 'Groceries', amount_paise: 120000, paid_by: 1, split_type: 'equal' })
    expect(payload.participant_ids.sort()).toEqual([1, 2, 3, 4])
  })

  it('blocks a custom split whose shares do not add up', async () => {
    const onSubmit = vi.fn()
    render(<ExpenseForm members={members} currentUserId={1} submitLabel="Save" onSubmit={onSubmit} />)

    await userEvent.type(screen.getByLabelText('Description'), 'Electricity')
    await userEvent.type(screen.getByLabelText('Amount (₹)'), '1000')
    await userEvent.click(screen.getByRole('radio', { name: 'custom' }))
    await userEvent.type(screen.getByLabelText('Sarvesh'), '400')
    await userEvent.type(screen.getByLabelText('Rahul'), '300')
    expect(screen.getByText('₹300.00 left to assign')).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: 'Save' }))

    expect(await screen.findByRole('alert')).toHaveTextContent('Shares must add up to ₹1,000.00')
    expect(onSubmit).not.toHaveBeenCalled()
  })
})
