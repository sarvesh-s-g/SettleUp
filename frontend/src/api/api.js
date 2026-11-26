// One small function per backend endpoint. Pages import these instead of
// building URLs themselves, so all API paths live in one place.
import client from './client'

const data = (promise) => promise.then((response) => response.data)

export const authApi = {
  register: (body) => data(client.post('/auth/register', body)),
  login: (body) => data(client.post('/auth/login', body)),
  me: () => data(client.get('/auth/me')),
}

export const groupsApi = {
  list: () => data(client.get('/groups')),
  create: (body) => data(client.post('/groups', body)),
  get: (groupId) => data(client.get(`/groups/${groupId}`)),
  members: (groupId) => data(client.get(`/groups/${groupId}/members`)),
  addMember: (groupId, email) => data(client.post(`/groups/${groupId}/members`, { email })),
  removeMember: (groupId, userId) => data(client.delete(`/groups/${groupId}/members/${userId}`)),
}

export const expensesApi = {
  list: (groupId, params) => data(client.get(`/groups/${groupId}/expenses`, { params })),
  create: (groupId, body) => data(client.post(`/groups/${groupId}/expenses`, body)),
  get: (expenseId) => data(client.get(`/expenses/${expenseId}`)),
  update: (expenseId, body) => data(client.patch(`/expenses/${expenseId}`, body)),
  remove: (expenseId) => data(client.delete(`/expenses/${expenseId}`)),
}

export const settlementsApi = {
  balances: (groupId) => data(client.get(`/groups/${groupId}/balances`)),
  suggested: (groupId) => data(client.get(`/groups/${groupId}/settlements/suggested`)),
  list: (groupId) => data(client.get(`/groups/${groupId}/settlements`)),
  create: (groupId, body) => data(client.post(`/groups/${groupId}/settlements`, body)),
}

export const dashboardApi = {
  get: () => data(client.get('/dashboard')),
}
