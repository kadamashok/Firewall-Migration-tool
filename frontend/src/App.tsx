import { useEffect, useMemo, useState } from "react";
import {
  checkCompatibility,
  connectivityTest,
  detectDevice,
  downloadJsonReport,
  downloadPdfReport,
  getJob,
  login,
  setToken as setApiToken,
  startMigration
} from "./api";
import Footer from "./components/Footer";
import { Compatibility, DeviceInfo, FirewallEndpoint, JobStatus } from "./types";

const initialEndpoint: FirewallEndpoint = { ip: "", username: "", password: "", ssh_port: 22 };

function validateIp(ip: string): boolean {
  const v4 =
    /^(25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)\.(25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)\.(25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)\.(25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)$/;
  const v6 = /^[0-9a-fA-F:]+$/;
  return v4.test(ip) || v6.test(ip);
}

export default function App() {
  const [source, setSource] = useState<FirewallEndpoint>(initialEndpoint);
  const [destination, setDestination] = useState<FirewallEndpoint>(initialEndpoint);
  const [sourceInfo, setSourceInfo] = useState<DeviceInfo | null>(null);
  const [destinationInfo, setDestinationInfo] = useState<DeviceInfo | null>(null);
  const [compatibility, setCompatibility] = useState<Compatibility | null>(null);
  const [job, setJob] = useState<JobStatus | null>(null);
  const [activeJobId, setActiveJobId] = useState<string>("");
  const [status, setStatus] = useState<string>("");
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState(false);
  const [notifyEmail, setNotifyEmail] = useState("");
  const [auth, setAuth] = useState({ username: "admin", password: "Admin@123" });
  const [token, setAuthToken] = useState("");
  const [role, setRole] = useState("");

  const compatColor = useMemo(() => {
    if (!compatibility) return "bg-slate-300";
    if (compatibility.score >= 85) return "bg-mint";
    if (compatibility.score >= 60) return "bg-amber";
    return "bg-coral";
  }, [compatibility]);

  useEffect(() => {
    if (!activeJobId || !token) return;
    const timer = setInterval(async () => {
      try {
        const data = await getJob(activeJobId);
        setJob(data);
        if (["completed", "failed"].includes(data.status)) {
          clearInterval(timer);
        }
      } catch {
        clearInterval(timer);
      }
    }, 1500);
    return () => clearInterval(timer);
  }, [activeJobId, token]);

  function validateBoth(): boolean {
    const next: Record<string, string> = {};
    if (!validateIp(source.ip)) next.sourceIp = "Invalid IP format";
    if (!source.username) next.sourceUsername = "Source username is required";
    if (!source.password) next.sourcePassword = "Source password is required";
    if (!validateIp(destination.ip)) next.destinationIp = "Invalid IP format";
    if (!destination.username) next.destinationUsername = "Destination username is required";
    if (!destination.password) next.destinationPassword = "Destination password is required";
    setErrors(next);
    return Object.keys(next).length === 0;
  }

  async function handleLogin() {
    setBusy(true);
    setStatus("");
    try {
      const data = await login(auth.username, auth.password);
      setApiToken(data.access_token);
      setAuthToken(data.access_token);
      setRole(data.role);
      setStatus(`Logged in as ${data.role}`);
    } catch (e: any) {
      setStatus(e?.response?.data?.detail || "Authentication failed");
    } finally {
      setBusy(false);
    }
  }

  async function handleConnectivity(which: "source" | "destination") {
    if (!token) return setStatus("Please login first");
    const endpoint = which === "source" ? source : destination;
    if (!validateIp(endpoint.ip)) {
      setErrors((prev) => ({ ...prev, [`${which}Ip`]: "Invalid IP format" }));
      return;
    }
    setBusy(true);
    try {
      const result = await connectivityTest(endpoint);
      setStatus(`${which.toUpperCase()} connectivity: ${result.ok ? "OK" : result.error}`);
    } catch (e: any) {
      setStatus(e?.response?.data?.detail || "Connectivity test failed");
    } finally {
      setBusy(false);
    }
  }

  async function handleDetect(which: "source" | "destination") {
    if (!token) return setStatus("Please login first");
    const endpoint = which === "source" ? source : destination;
    setBusy(true);
    try {
      const info = await detectDevice(endpoint);
      if (which === "source") setSourceInfo(info);
      else setDestinationInfo(info);
      setStatus(`${which.toUpperCase()} detected: ${info.vendor} ${info.model} ${info.os_version}`);
    } catch (e: any) {
      setStatus(e?.response?.data?.detail || "Device detection failed");
    } finally {
      setBusy(false);
    }
  }

  async function handleCompatibility() {
    if (!token) return setStatus("Please login first");
    if (!validateBoth()) return;
    setBusy(true);
    try {
      const result = await checkCompatibility(source, destination);
      setCompatibility(result);
      setStatus(`Compatibility score: ${result.score}`);
    } catch (e: any) {
      setStatus(e?.response?.data?.detail || "Compatibility check failed");
    } finally {
      setBusy(false);
    }
  }

  async function handleMigration(dryRun: boolean) {
    if (!token) return setStatus("Please login first");
    if (!validateBoth()) return;
    setBusy(true);
    try {
      const res = await startMigration(source, destination, dryRun, notifyEmail || undefined);
      setActiveJobId(res.job_id);
      setStatus(`${dryRun ? "Dry run" : "Migration"} started: ${res.job_id}`);
    } catch (e: any) {
      setStatus(e?.response?.data?.detail || "Migration start failed");
    } finally {
      setBusy(false);
    }
  }

  if (!token) {
    return (
      <div className="min-h-screen flex flex-col">
        <main className="flex-grow flex items-center justify-center p-6">
          <div className="panel w-full max-w-md p-6">
            <h1 className="text-2xl font-bold text-slateblue mb-4">Firewall Migration Tool</h1>
            <p className="text-sm text-slate-600 mb-5">Role-based login (Admin / Operator)</p>
            <div className="space-y-3">
              <input
                className="w-full rounded-lg border border-slate-300 px-3 py-2"
                placeholder="Username"
                value={auth.username}
                onChange={(e) => setAuth((p) => ({ ...p, username: e.target.value }))}
              />
              <input
                className="w-full rounded-lg border border-slate-300 px-3 py-2"
                placeholder="Password"
                type="password"
                value={auth.password}
                onChange={(e) => setAuth((p) => ({ ...p, password: e.target.value }))}
              />
              <button className="w-full rounded-lg bg-slateblue text-white py-2 font-semibold disabled:opacity-50" onClick={handleLogin} disabled={busy}>
                Login
              </button>
              <p className="text-sm text-coral">{status}</p>
            </div>
          </div>
        </main>
        <Footer />
      </div>
    );
  }

  return (
    <div className="min-h-screen flex flex-col">
      <main className="flex-grow p-4 md:p-8">
        <div className="max-w-7xl mx-auto space-y-5">
          <header className="panel p-5 flex flex-col md:flex-row md:items-center md:justify-between gap-3">
            <div>
              <h1 className="text-3xl font-bold text-slateblue">Enterprise Firewall Migration Dashboard</h1>
              <p className="text-slate-600">Signed in as {role}</p>
            </div>
            <div className="flex items-center gap-3">
              <div className="text-sm">Compatibility Status</div>
              <div className={`h-4 w-20 rounded-full ${compatColor}`} />
            </div>
          </header>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
            <section className="panel p-5 space-y-3">
              <h2 className="font-bold text-lg text-slateblue">Source Firewall Panel</h2>
              <input className="w-full rounded border px-3 py-2" placeholder="Source Firewall IP" value={source.ip} onChange={(e) => setSource((p) => ({ ...p, ip: e.target.value }))} />
              {errors.sourceIp && <p className="text-sm text-coral">{errors.sourceIp}</p>}
              <input className="w-full rounded border px-3 py-2" placeholder="Username" value={source.username} onChange={(e) => setSource((p) => ({ ...p, username: e.target.value }))} />
              {errors.sourceUsername && <p className="text-sm text-coral">{errors.sourceUsername}</p>}
              <input className="w-full rounded border px-3 py-2" placeholder="Password" type="password" value={source.password} onChange={(e) => setSource((p) => ({ ...p, password: e.target.value }))} />
              {errors.sourcePassword && <p className="text-sm text-coral">{errors.sourcePassword}</p>}
              <div className="flex gap-2">
                <button className="rounded bg-slateblue text-white px-3 py-2 text-sm" onClick={() => handleConnectivity("source")} disabled={busy}>Test Connectivity</button>
                <button className="rounded bg-mint text-white px-3 py-2 text-sm" onClick={() => handleDetect("source")} disabled={busy}>Detect Device</button>
              </div>
              {sourceInfo && <p className="text-sm text-slate-700">{sourceInfo.vendor} | {sourceInfo.model} | {sourceInfo.os_version}</p>}
            </section>

            <section className="panel p-5 space-y-3">
              <h2 className="font-bold text-lg text-slateblue">Destination Firewall Panel</h2>
              <input className="w-full rounded border px-3 py-2" placeholder="Destination Firewall IP" value={destination.ip} onChange={(e) => setDestination((p) => ({ ...p, ip: e.target.value }))} />
              {errors.destinationIp && <p className="text-sm text-coral">{errors.destinationIp}</p>}
              <input className="w-full rounded border px-3 py-2" placeholder="Username" value={destination.username} onChange={(e) => setDestination((p) => ({ ...p, username: e.target.value }))} />
              {errors.destinationUsername && <p className="text-sm text-coral">{errors.destinationUsername}</p>}
              <input className="w-full rounded border px-3 py-2" placeholder="Password" type="password" value={destination.password} onChange={(e) => setDestination((p) => ({ ...p, password: e.target.value }))} />
              {errors.destinationPassword && <p className="text-sm text-coral">{errors.destinationPassword}</p>}
              <div className="flex gap-2">
                <button className="rounded bg-slateblue text-white px-3 py-2 text-sm" onClick={() => handleConnectivity("destination")} disabled={busy}>Test Connectivity</button>
                <button className="rounded bg-mint text-white px-3 py-2 text-sm" onClick={() => handleDetect("destination")} disabled={busy}>Detect Device</button>
              </div>
              {destinationInfo && <p className="text-sm text-slate-700">{destinationInfo.vendor} | {destinationInfo.model} | {destinationInfo.os_version}</p>}
            </section>
          </div>
          <section className="panel p-5 space-y-3">
            <div className="flex flex-wrap gap-2">
              <button className="rounded bg-slateblue text-white px-4 py-2 text-sm" onClick={handleCompatibility} disabled={busy}>Check Compatibility</button>
              <button className="rounded bg-amber text-white px-4 py-2 text-sm" onClick={() => handleMigration(true)} disabled={busy}>Dry Run</button>
              <button className="rounded bg-coral text-white px-4 py-2 text-sm" onClick={() => handleMigration(false)} disabled={busy}>Start Migration</button>
            </div>
            <input
              className="w-full max-w-md rounded border px-3 py-2"
              placeholder="Optional completion email notification"
              value={notifyEmail}
              onChange={(e) => setNotifyEmail(e.target.value)}
            />
            <p className="text-sm text-slate-700">{status}</p>
            {compatibility && (
              <div className="rounded bg-slate-50 border p-3">
                <div className="text-sm font-semibold">Mode: {compatibility.mode} | Score: {compatibility.score}</div>
                {compatibility.issues.map((i, idx) => (
                  <div key={idx} className="text-sm mt-1">
                    [{i.severity}] {i.category}: {i.message}
                  </div>
                ))}
              </div>
            )}
          </section>

          <section className="panel p-5 space-y-3">
            <h2 className="font-bold text-lg text-slateblue">Migration Log Console</h2>
            <div className="h-3 w-full bg-slate-200 rounded-full overflow-hidden">
              <div className="h-3 bg-mint transition-all duration-500" style={{ width: `${job?.progress ?? 0}%` }} />
            </div>
            <div className="rounded border bg-slate-900 text-slate-100 p-3 h-56 overflow-auto text-xs leading-5">
              {(job?.logs || ["No migration logs yet"]).map((line, idx) => (
                <div key={idx}>{line}</div>
              ))}
            </div>
            <div className="flex gap-2">
              <button
                className="rounded bg-slateblue text-white px-4 py-2 text-sm disabled:opacity-50"
                disabled={!job?.report_id}
                onClick={async () => {
                  if (!job?.report_id) return;
                  try {
                    await downloadPdfReport(job.report_id);
                  } catch {
                    setStatus("Failed to download PDF report");
                  }
                }}
              >
                Download PDF Report
              </button>
              <button
                className="rounded bg-mint text-white px-4 py-2 text-sm disabled:opacity-50"
                disabled={!job?.report_id}
                onClick={async () => {
                  if (!job?.report_id) return;
                  try {
                    await downloadJsonReport(job.report_id);
                  } catch {
                    setStatus("Failed to download JSON report");
                  }
                }}
              >
                Download JSON Report
              </button>
            </div>
          </section>
        </div>
      </main>
      <Footer />
    </div>
  );
}
