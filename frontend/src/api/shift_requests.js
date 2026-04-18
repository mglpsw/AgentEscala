import api from './client.js'

export function listShiftRequests() {
  return api.get('/shift-requests').then((response) => response.data)
}

export function createShiftRequest(payload) {
  return api.post('/shift-requests/', payload).then((response) => response.data)
}

export function respondShiftRequest(requestId, payload) {
  return api.post(`/shift-requests/${requestId}/respond`, payload).then((response) => response.data)
}

export function adminReviewShiftRequest(requestId, payload) {
  return api.post(`/shift-requests/${requestId}/admin-review`, payload).then((response) => response.data)
}

export function cancelShiftRequest(requestId) {
  return api.post(`/shift-requests/${requestId}/cancel`).then((response) => response.data)
}
