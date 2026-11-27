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
  remove: (groupId) => data(client.delete(`/groups/${groupId}`)),
  members: (groupId) => data(client.get(`/groups/${groupId}/members`)),
  invites: (groupId) => data(client.get(`/groups/${groupId}/invites`)),
  inviteMember: (groupId, email) => data(client.post(`/groups/${groupId}/invites`, { email })),
  cancelInvite: (groupId, inviteId) => data(client.delete(`/groups/${groupId}/invites/${inviteId}`)),
  removeMember: (groupId, userId) => data(client.delete(`/groups/${groupId}/members/${userId}`)),
}

export const invitesApi = {
  list: () => data(client.get('/invites')),
  accept: (inviteId) => data(client.post(`/invites/${inviteId}/accept`)),
  decline: (inviteId) => data(client.post(`/invites/${inviteId}/decline`)),
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
  get: (params) => data(client.get('/dashboard', { params })),
}
