// Client HTTP : jeton d'accès gardé en mémoire (jamais dans localStorage), renouvelé via le cookie httpOnly.
import axios from "axios";

let accessToken = null;
let onAuthLost = () => {};

export const setAccessToken = (t) => { accessToken = t; };
export const setAuthLostHandler = (fn) => { onAuthLost = fn; };

const api = axios.create({ baseURL: "/api", withCredentials: true });

api.interceptors.request.use((config) => {
  if (accessToken) config.headers.Authorization = `Bearer ${accessToken}`;
  return config;
});

let refreshing = null;
api.interceptors.response.use(
  (r) => r,
  async (error) => {
    const original = error.config;
    const isAuthCall = original?.url?.startsWith("/auth/");
    if (error.response?.status === 401 && !original._retry && !isAuthCall) {
      original._retry = true;
      try {
        refreshing = refreshing || api.post("/auth/refresh").finally(() => { refreshing = null; });
        const { data } = await refreshing;
        accessToken = data.access_token;
        original.headers.Authorization = `Bearer ${accessToken}`;
        return api(original);
      } catch {
        accessToken = null;
        onAuthLost();
      }
    }
    return Promise.reject(error);
  }
);

export const errorMessage = (e, fallback = "Une erreur est survenue") => {
  const d = e?.response?.data?.detail;
  if (typeof d === "string") return d;
  if (Array.isArray(d)) return d.map((x) => x.msg).join(" ; ");
  if (e?.response?.status === 429) return "Trop de tentatives, réessayez dans une minute";
  return fallback;
};

export default api;
