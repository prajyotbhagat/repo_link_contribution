// API client with automatic JWT token refresh
// In production (Amplify build), VITE_API_URL is injected as the full HTTPS
// origin (e.g. https://13-48-26-213.sslip.io). For local dev it falls back
// to the Vite dev-server proxy so no .env change is needed locally.
const API_BASE = import.meta.env.VITE_API_URL
  ? `${import.meta.env.VITE_API_URL}/api`
  : '/api';

function getTokens() {
  return {
    access: localStorage.getItem('access_token'),
    refresh: localStorage.getItem('refresh_token'),
  };
}

function saveTokens({ access, refresh }) {
  if (access) localStorage.setItem('access_token', access);
  if (refresh) localStorage.setItem('refresh_token', refresh);
}

function clearTokens() {
  localStorage.removeItem('access_token');
  localStorage.removeItem('refresh_token');
}

async function refreshAccessToken() {
  const { refresh } = getTokens();
  if (!refresh) throw new Error('No refresh token');

  const res = await fetch(`${API_BASE}/auth/token/refresh/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ refresh }),
  });
  if (!res.ok) { clearTokens(); throw new Error('Session expired'); }
  const data = await res.json();
  saveTokens({ access: data.access, refresh: data.refresh });
  return data.access;
}

async function apiFetch(path, options = {}) {
  const { access } = getTokens();
  const headers = { 'Content-Type': 'application/json', ...(options.headers || {}) };
  if (access) headers['Authorization'] = `Bearer ${access}`;

  let res = await fetch(`${API_BASE}${path}`, { ...options, headers });

  // If 401, try refreshing once
  if (res.status === 401) {
    try {
      const newAccess = await refreshAccessToken();
      headers['Authorization'] = `Bearer ${newAccess}`;
      res = await fetch(`${API_BASE}${path}`, { ...options, headers });
    } catch {
      clearTokens();
      window.location.reload();
      return;
    }
  }

  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.detail || JSON.stringify(data));
  return data;
}

export async function login(email, password) {
  const data = await apiFetch('/auth/login/', {
    method: 'POST',
    body: JSON.stringify({ email, password }),
  });
  saveTokens({ access: data.access, refresh: data.refresh });
  return data.user;
}

export async function register(email, password) {
  const data = await apiFetch('/auth/register/', {
    method: 'POST',
    body: JSON.stringify({ email, password }),
  });
  saveTokens({ access: data.access, refresh: data.refresh });
  return data.user;
}

export async function logout() {
  const { refresh } = getTokens();
  await apiFetch('/auth/logout/', { method: 'POST', body: JSON.stringify({ refresh }) }).catch(() => {});
  clearTokens();
}

export async function getMe() {
  if (!getTokens().access) return null;
  try { return await apiFetch('/auth/me/'); } catch { return null; }
}

export const fetchRepos = (query = '', language = '') =>
  apiFetch(`/repos/recommendations/?query=${encodeURIComponent(query)}&language=${encodeURIComponent(language)}&limit=50`);

export const fetchRepo = (id) => apiFetch(`/repos/${id}/`);

export const fetchRecentIssues = (id) => apiFetch(`/repos/${id}/recent_issues/`);

export const starRepo = (id) => apiFetch(`/repos/${id}/star/`, { method: 'POST' });

export const unstarRepo = (id) => apiFetch(`/repos/${id}/unstar/`, { method: 'POST' });

export const startChat = (issue_id) =>
  apiFetch('/chat/start/', { method: 'POST', body: JSON.stringify({ issue_id }) });

export const sendChatMessage = (session_id, message) =>
  apiFetch(`/chat/${session_id}/message/`, { method: 'POST', body: JSON.stringify({ message }) });
