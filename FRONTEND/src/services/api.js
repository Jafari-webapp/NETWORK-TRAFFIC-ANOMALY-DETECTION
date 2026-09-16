import axios from "axios";

const BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8001";

const api = axios.create({
  baseURL: BASE_URL,
  headers: { "Content-Type": "application/json" },
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem("access_token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem("access_token");
      localStorage.removeItem("username");
      localStorage.removeItem("full_name");
      if (window.location.pathname !== "/login") {
        window.location.href = "/login";
      }
    }
    return Promise.reject(error);
  }
);

// --- Auth ---
export const login = (username, password) =>
  api.post("/api/auth/login", { username, password });
export const getMe = () => api.get("/api/auth/me");
export const updateProfile = (payload) => api.patch("/api/auth/me", payload);
export const changePassword = (payload) => api.post("/api/auth/change-password", payload);
export const getPreferences = () => api.get("/api/auth/preferences");
export const updatePreferences = (payload) => api.put("/api/auth/preferences", payload);

// --- Firewall Logs ---
export const getLogs = (params) => api.get("/api/logs", { params });
export const getLog = (id) => api.get(`/api/logs/${id}`);
export const getUploadHistory = () => api.get("/api/logs/upload-history");
export const deleteUploadHistoryEntry = (id) => api.delete(`/api/logs/upload-history/${id}`);
export const clearUploadHistory = () => api.delete("/api/logs/upload-history");
export const uploadLogs = (file, onUploadProgress) => {
  const formData = new FormData();
  formData.append("file", file);
  return api.post("/api/logs/upload", formData, {
    headers: { "Content-Type": "multipart/form-data" },
    onUploadProgress,
  });
};

// --- Anomalies ---
export const getAnomalyDetail = (id) => api.get(`/api/anomalies/${id}`);
export const detectAnomaly = (firewallLogId) =>
  api.post("/api/anomalies/detect", { firewall_log_id: firewallLogId });
export const detectAndAnalyze = (firewallLogId) =>
  api.post("/api/anomalies/detect-and-analyze", { firewall_log_id: firewallLogId });

// --- LLM ---
export const analyzeWithGemini = (anomalyId) => api.post(`/api/llm/analyze/${anomalyId}`);
export const getGeminiAnalysis = (anomalyId) => api.get(`/api/llm/analyze/${anomalyId}`);

// --- Dashboard ---
export const getDashboardSummary = (scopeParams = {}) =>
  api.get("/api/dashboard/summary", { params: scopeParams });
export const getRecentAnomalies = (limit = 20, hours = 24, scopeParams = {}) =>
  api.get("/api/dashboard/recent-anomalies", { params: { limit, hours, ...scopeParams } });
export const getAnomalyTrends = (days = 14, scopeParams = {}) =>
  api.get("/api/dashboard/anomaly-trends", { params: { days, ...scopeParams } });
export const getTopSourceIps = (limit = 10, scopeParams = {}) =>
  api.get("/api/dashboard/top-ips", { params: { column: "src_ip", limit, ...scopeParams } });
export const getTopDestinationIps = (limit = 10, scopeParams = {}) =>
  api.get("/api/dashboard/top-ips", { params: { column: "dst_ip", limit, ...scopeParams } });
export const getProtocolDistribution = (scopeParams = {}) =>
  api.get("/api/dashboard/protocol-distribution", { params: scopeParams });
export const getRuleTypeDistribution = (scopeParams = {}) =>
  api.get("/api/dashboard/rule-type-distribution", { params: scopeParams });
export const getTopDestinationPorts = (limit = 10, scopeParams = {}) =>
  api.get("/api/dashboard/top-destination-ports", { params: { limit, ...scopeParams } });
export const getFirewallRuleActivity = (limit = 10, scopeParams = {}) =>
  api.get("/api/dashboard/firewall-rule-activity", { params: { limit, ...scopeParams } });

// --- AI Assistant ---
export const chatWithAssistant = (message, history) =>
  api.post("/api/assistant/chat", { message, history });

// --- AI Report Generator ---
export const generateReport = (period, reportType) =>
  api.post("/api/reports/generate", { period, report_type: reportType });

// Turns an axios error into a readable string: backend's own `detail` message
// when the server responded, otherwise a clear network/timeout explanation.
// Use this in every page's catch block instead of a hardcoded generic string,
// so real failures (wrong API URL, CORS, 500s) are visible
// on screen instead of hidden behind "Could not load ...".
export const getErrorMessage = (err, fallback = "Something went wrong.") => {
  if (err?.response) {
    const detail = err.response.data?.detail;
    if (typeof detail === "string") return detail;
    return `${fallback} (server responded ${err.response.status})`;
  }
  if (err?.request) {
    return `${fallback} Could not reach the API at ${BASE_URL} — check the backend is running and VITE_API_BASE_URL is correct.`;
  }
  return err?.message || fallback;
};

export default api;

