/**
 * API client implementing Person A contracts:
 * - POST /ingest/upload
 * - POST /ingest/sms
 * - GET /transactions
 * - PATCH /transactions/{id}
 * - GET /rules
 * - DELETE /rules/{id}
 * - GET /recurring
 * - POST /recurring/{merchant_hash}/mark-unused
 * - GET /health
 */

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

async function request(endpoint, options = {}) {
  const url = `${API_BASE}${endpoint}`;
  const response = await fetch(url, options);

  if (response.status === 204) {
    return null;
  }

  const contentType = response.headers.get('content-type') || '';
  const data = contentType.includes('application/json')
    ? await response.json()
    : await response.text();

  if (!response.ok) {
    const errorMsg =
      (data && typeof data === 'object' && (data.message || data.error || (data.detail && data.detail.message))) ||
      `Request failed with status ${response.status}`;
    const err = new Error(errorMsg);
    err.status = response.status;
    err.data = data;
    throw err;
  }

  return data;
}

export const api = {
  // Ingest
  async uploadStatement(file, account = '') {
    const formData = new FormData();
    formData.append('file', file);
    if (account) {
      formData.append('account', account);
    }
    return request('/ingest/upload', {
      method: 'POST',
      body: formData,
    });
  },

  async ingestSms(messages, defaultYear = new Date().getFullYear()) {
    return request('/ingest/sms', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ messages, default_year: defaultYear }),
    });
  },

  // Transactions
  async getTransactions(filters = {}) {
    const params = new URLSearchParams();
    if (filters.category) params.append('category', filters.category);
    if (filters.source) params.append('source', filters.source);
    if (filters.merchant) params.append('merchant', filters.merchant);
    if (filters.from_date) params.append('from_date', filters.from_date);
    if (filters.to_date) params.append('to_date', filters.to_date);
    if (filters.limit !== undefined) params.append('limit', String(filters.limit));
    if (filters.offset !== undefined) params.append('offset', String(filters.offset));

    const qs = params.toString();
    return request(`/transactions${qs ? `?${qs}` : ''}`);
  },

  async updateTransactionCategory(txnId, category) {
    return request(`/transactions/${txnId}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ category }),
    });
  },

  // Rules
  async getRules() {
    return request('/rules');
  },

  async deleteRule(ruleId) {
    return request(`/rules/${ruleId}`, {
      method: 'DELETE',
    });
  },

  // Recurring
  async getRecurring() {
    return request('/recurring');
  },

  async markRecurringUnused(merchantHash) {
    return request(`/recurring/${merchantHash}/mark-unused`, {
      method: 'POST',
    });
  },

  // Health
  async getHealth() {
    return request('/health');
  },
};
