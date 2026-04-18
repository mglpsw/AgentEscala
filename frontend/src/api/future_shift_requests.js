import api from './client.js'

export function listFutureShiftRequests(params = {}) {
  return api.get('/me/future-shift-requests', { params }).then((response) => response.data)
}

export function createFutureShiftRequest(payload) {
  return api.post('/me/future-shift-requests', payload).then((response) => response.data)
}

export function cancelFutureShiftRequest(requestId) {
  return api.delete(`/me/future-shift-requests/${requestId}`).then((response) => response.data)
}
