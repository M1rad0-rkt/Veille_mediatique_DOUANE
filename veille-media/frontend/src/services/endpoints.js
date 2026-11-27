import api from "./api";

const clean = (p) => Object.fromEntries(Object.entries(p || {}).filter(([, v]) => v !== "" && v != null && v !== "all"));
const get = (url, params) => api.get(url, { params: clean(params) }).then((r) => r.data);

export const auth = {
  login: (email, password) => api.post("/auth/login", { email, password }).then((r) => r.data),
  refresh: () => api.post("/auth/refresh").then((r) => r.data),
  logout: () => api.post("/auth/logout"),
};

export const news = {
  list: (p) => get("/news", p),
  favorites: (p) => get("/news/favorites", p),
  history: (p) => get("/news/history", p),
  latest: (since) => get("/news/latest", { since }),
  detail: (id) => get(`/news/${id}`),
  favorite: (id, on) => (on ? api.post(`/news/${id}/favorite`) : api.delete(`/news/${id}/favorite`)),
  read: (id, on) => (on ? api.post(`/news/${id}/read`) : api.delete(`/news/${id}/read`)),
  setCategory: (id, body) => api.patch(`/news/${id}/category`, body).then((r) => r.data),
  reprocess: (id) => api.post(`/news/${id}/reprocess`).then((r) => r.data),
};

export const categories = {
  list: (includeInactive = false) => get("/categories", { include_inactive: includeInactive || undefined }),
  nav: () => get("/categories/nav"),
  create: (b) => api.post("/categories", b).then((r) => r.data),
  update: (id, b) => api.put(`/categories/${id}`, b).then((r) => r.data),
  remove: (id) => api.delete(`/categories/${id}`),
};

export const sources = {
  list: () => get("/sources"),
  create: (b) => api.post("/sources", b).then((r) => r.data),
  update: (id, b) => api.put(`/sources/${id}`, b).then((r) => r.data),
  remove: (id) => api.delete(`/sources/${id}`),
  probe: (id, apply) => api.post(`/sources/${id}/probe`, null, { params: { apply } }).then((r) => r.data),
};

export const dashboard = {
  me: () => get("/dashboard"),
  admin: () => get("/admin/dashboard"),
};

export const admin = {
  users: () => get("/admin/users"),
  createUser: (b) => api.post("/admin/users", b).then((r) => r.data),
  updateUser: (id, b) => api.patch(`/admin/users/${id}`, b).then((r) => r.data),
  deleteUser: (id) => api.delete(`/admin/users/${id}`),
  settings: () => get("/admin/settings"),
  saveSettings: (b) => api.put("/admin/settings", b).then((r) => r.data),
};

export const agent = {
  status: () => get("/agent/status"),
  logs: (p) => get("/agent/logs", p),
  collect: (sourceId) => api.post("/agent/collect", { source_id: sourceId ?? null }).then((r) => r.data),
  process: () => api.post("/agent/process").then((r) => r.data),
};
