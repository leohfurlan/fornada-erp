import axios, { AxiosError } from "axios";
import { useAuthStore } from "@/stores/use-auth-store";

/**
 * URL base do backend, resolvida dinamicamente.
 *
 * Estratégia: usar o mesmo host que o navegador está acessando o frontend,
 * trocando a porta para 8000 (do backend). Assim funciona automaticamente:
 *   - desktop em localhost:3000  → API em localhost:8000
 *   - celular em 192.168.x.x:3000 → API em 192.168.x.x:8000
 *   - qualquer outra rede sem alterar config.
 *
 * `NEXT_PUBLIC_API_URL` segue suportado como override (CI, produção, casos
 * em que o backend está em outro host).
 */
function baseApiUrl(): string {
  if (process.env.NEXT_PUBLIC_API_URL) {
    return process.env.NEXT_PUBLIC_API_URL;
  }
  if (typeof window !== "undefined") {
    return `${window.location.protocol}//${window.location.hostname}:8000`;
  }
  // SSR/build sem janela — fallback seguro. Hooks só chamam a API no client,
  // então essa branch raramente é exercida em produção.
  return "http://localhost:8000";
}

export const api = axios.create({
  headers: { "Content-Type": "application/json" },
});

// Interceptor de request: resolve baseURL no momento da chamada (no client)
// e anexa o JWT. baseURL precisa ser setado por request porque depende de
// window.location, que não existe em build time.
api.interceptors.request.use((config) => {
  config.baseURL = `${baseApiUrl()}/api/v1`;
  const token = useAuthStore.getState().accessToken;
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

let isRefreshing = false;
let failedQueue: Array<{ resolve: (token: string) => void; reject: (err: unknown) => void }> = [];

const processQueue = (error: unknown, token: string | null = null) => {
  failedQueue.forEach((prom) => {
    if (error) {
      prom.reject(error);
    } else {
      prom.resolve(token!);
    }
  });
  failedQueue = [];
};

// Renova o token automaticamente quando expirar (401)
api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const originalRequest = error.config as typeof error.config & { _retry?: boolean };

    if (error.response?.status !== 401 || originalRequest._retry) {
      return Promise.reject(error);
    }

    if (isRefreshing) {
      return new Promise((resolve, reject) => {
        failedQueue.push({ resolve, reject });
      }).then((token) => {
        originalRequest.headers!.Authorization = `Bearer ${token}`;
        return api(originalRequest);
      });
    }

    originalRequest._retry = true;
    isRefreshing = true;

    const { refreshToken, setTokens, logout } = useAuthStore.getState();

    if (!refreshToken) {
      logout();
      return Promise.reject(error);
    }

    try {
      const response = await axios.post(`${baseApiUrl()}/api/v1/auth/refresh`, {
        refresh_token: refreshToken,
      });
      const { access_token, refresh_token } = response.data;
      setTokens(access_token, refresh_token);
      processQueue(null, access_token);
      originalRequest.headers!.Authorization = `Bearer ${access_token}`;
      return api(originalRequest);
    } catch (refreshError) {
      processQueue(refreshError);
      logout();
      return Promise.reject(refreshError);
    } finally {
      isRefreshing = false;
    }
  }
);
