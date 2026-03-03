import axios from "axios";
import { Compatibility, DeviceInfo, FirewallEndpoint, JobStatus } from "./types";

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000"
});

export function setToken(token: string) {
  api.defaults.headers.common.Authorization = `Bearer ${token}`;
}

export async function login(username: string, password: string) {
  const { data } = await api.post("/auth/login", { username, password });
  return data as { access_token: string; role: string };
}

export async function connectivityTest(endpoint: FirewallEndpoint) {
  const { data } = await api.post("/connectivity-test", endpoint);
  return data as { ok: boolean; error?: string; detail?: string };
}

export async function detectDevice(endpoint: FirewallEndpoint) {
  const { data } = await api.post("/detect-device", endpoint);
  return data as DeviceInfo;
}

export async function checkCompatibility(source: FirewallEndpoint, destination: FirewallEndpoint) {
  const { data } = await api.post("/check-compatibility", {
    source,
    destination,
    dry_run: true
  });
  return data as Compatibility;
}

export async function startMigration(source: FirewallEndpoint, destination: FirewallEndpoint, dryRun: boolean, notifyEmail?: string) {
  const endpoint = dryRun ? "/dry-run" : "/start-migration";
  const { data } = await api.post(endpoint, {
    source,
    destination,
    dry_run: dryRun,
    notify_email: notifyEmail || null
  });
  return data as { job_id: string };
}

export async function getJob(jobId: string) {
  const { data } = await api.get(`/jobs/${jobId}`);
  return data as JobStatus;
}

function saveBlob(blob: Blob, filename: string) {
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  window.URL.revokeObjectURL(url);
}

export async function downloadJsonReport(reportId: string) {
  const response = await api.get(`/reports/${reportId}/json`, { responseType: "blob" });
  saveBlob(response.data, `${reportId}.json`);
}

export async function downloadPdfReport(reportId: string) {
  const response = await api.get(`/reports/${reportId}/pdf`, { responseType: "blob" });
  saveBlob(response.data, `${reportId}.pdf`);
}
