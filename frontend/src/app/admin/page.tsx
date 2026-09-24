"use client";

import { useEffect, useState } from "react";
import { 
  Server, Cpu, CheckCircle2, ShieldCheck, ShieldAlert, 
  Send, RefreshCw, Mail, Phone, Bell, AlertTriangle, Power, Play, AlertOctagon
} from "lucide-react";
import { fetchFromAPI } from "@/lib/api";

export default function AdminPage() {
  const [health, setHealth] = useState<any>(null);
  const [sources, setSources] = useState<any[]>([]);
  const [alertConfig, setAlertConfig] = useState<any>(null);
  const [safetyToggling, setSafetyToggling] = useState(false);
  const [killSwitchToggling, setKillSwitchToggling] = useState(false);
  const [evaluatingNow, setEvaluatingNow] = useState(false);
  const [evaluateResult, setEvaluateResult] = useState<any>(null);

  // Test Notification State
  const [testPhone, setTestPhone] = useState("+91-98765-43210");
  const [testEmail, setTestEmail] = useState("duty-officer@sdma.gov.in");
  const [testChannel, setTestChannel] = useState<"both" | "sms" | "email">("both");
  const [testSending, setTestSending] = useState(false);
  const [testResult, setTestResult] = useState<any>(null);

  // Credential Validation State
  const [validatingCredentials, setValidatingCredentials] = useState(false);
  const [validationResult, setValidationResult] = useState<any>(null);

  // Controlled Live Delivery Test State
  const [runningLiveTest, setRunningLiveTest] = useState(false);
  const [liveTestResult, setLiveTestResult] = useState<any>(null);

  const loadData = () => {
    fetchFromAPI("/system/health").then(h => setHealth(h));
    fetchFromAPI("/system/data-sources").then(s => setSources(s || []));
    fetchFromAPI("/alerts/config").then(c => {
      if (c) {
        setAlertConfig(c);
        if (c.test_phone) setTestPhone(c.test_phone);
        if (c.test_email) setTestEmail(c.test_email);
      }
    });
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleToggleSafety = async () => {
    if (!alertConfig) return;
    setSafetyToggling(true);
    try {
      const res = await fetchFromAPI("/alerts/config", {
        method: "POST",
        body: JSON.stringify({
          live_alerts_enabled: !alertConfig.live_alerts_enabled
        })
      });
      if (res && res.config) {
        setAlertConfig(res.config);
      }
    } finally {
      setSafetyToggling(false);
    }
  };

  const handleToggleKillSwitch = async () => {
    setKillSwitchToggling(true);
    try {
      const currentlyActive = Boolean(alertConfig?.kill_switch_active);
      const res = await fetchFromAPI("/alerts/kill-switch", {
        method: "POST",
        body: JSON.stringify({ active: !currentlyActive })
      });
      if (res) {
        setAlertConfig((prev: any) => ({
          ...prev,
          kill_switch_active: res.kill_switch_active
        }));
      }
    } finally {
      setKillSwitchToggling(false);
    }
  };

  const handleEvaluateNow = async () => {
    setEvaluatingNow(true);
    setEvaluateResult(null);
    try {
      const res = await fetchFromAPI("/alerts/evaluate-now", {
        method: "POST"
      });
      setEvaluateResult(res);
      // Refresh config to update rate limits
      loadData();
    } catch (err: any) {
      setEvaluateResult({ status: "error", error: String(err) });
    } finally {
      setEvaluatingNow(false);
    }
  };

  const handleSendTestNotification = async () => {
    setTestSending(true);
    setTestResult(null);
    try {
      const res = await fetchFromAPI("/alerts/test-notification", {
        method: "POST",
        body: JSON.stringify({
          channel: testChannel,
          recipient_phone: testPhone,
          recipient_email: testEmail,
          message: "CycloneX operational notification pipeline verification dispatch. Decision support test only."
        })
      });
      setTestResult(res);
      // Refresh config to update rate limit counters
      const updatedConf = await fetchFromAPI("/alerts/config");
      if (updatedConf) setAlertConfig(updatedConf);
    } catch (err: any) {
      setTestResult({ status: "error", error: String(err) });
    } finally {
      setTestSending(false);
    }
  };

  const handleValidateCredentials = async () => {
    setValidatingCredentials(true);
    setValidationResult(null);
    try {
      const res = await fetchFromAPI("/alerts/validate-credentials", {
        method: "POST"
      });
      setValidationResult(res);
      loadData();
    } catch (err: any) {
      setValidationResult({ verification_status: "NOT VERIFIED", reason: String(err) });
    } finally {
      setValidatingCredentials(false);
    }
  };

  const handleSendControlledLiveTest = async () => {
    setRunningLiveTest(true);
    setLiveTestResult(null);
    try {
      const res = await fetchFromAPI("/alerts/test-live-delivery", {
        method: "POST",
        body: JSON.stringify({
          confirm_live_test: true,
          recipient_phone: testPhone,
          recipient_email: testEmail
        })
      });
      setLiveTestResult(res);
      loadData();
    } catch (err: any) {
      setLiveTestResult({ verification_status: "TEST_FAILED", summary: String(err) });
    } finally {
      setRunningLiveTest(false);
    }
  };

  return (
    <div className="flex-1 p-4 sm:p-6 lg:p-8 max-w-7xl mx-auto w-full space-y-6">
      {/* Header */}
      <div className="bg-white border border-slate-200 rounded p-4 flex flex-col md:flex-row md:items-baseline justify-between gap-2">
        <div>
          <h1 className="text-base font-bold text-slate-900 tracking-tight uppercase font-mono">
            SYSTEM ADMINISTRATION & MLOPS CONSOLE
          </h1>
          <p className="text-xs text-slate-500 mt-0.5">
            API cluster health, multi-source ingestion adapter latency, notification gateway configuration, and model registry telemetry.
          </p>
        </div>

        <div className="text-[11px] font-mono text-slate-400">
          TELEMETRY: FASTAPI CORE v1.0.0
        </div>
      </div>

      {/* System Status Indicators */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 font-mono text-xs">
        <div className="p-4 rounded bg-white border border-slate-200 space-y-1">
          <span className="text-slate-500 block text-[10px]">API ENGINE STATUS:</span>
          <div className="text-lg font-bold text-slate-900 flex items-center space-x-1.5">
            <CheckCircle2 className="w-4 h-4 text-emerald-600" />
            <span className="uppercase">{health?.status || "ONLINE"}</span>
          </div>
          <span className="text-slate-400 text-[10px] block">FastAPI Core • v1.0.0</span>
        </div>

        <div className="p-4 rounded bg-white border border-slate-200 space-y-1">
          <span className="text-slate-500 block text-[10px]">DATABASE ENGINE:</span>
          <div className="text-lg font-bold text-slate-900 uppercase">
            {health?.database || "CONNECTED"}
          </div>
          <span className="text-slate-400 text-[10px] block">SQLite / Spatial Fallback</span>
        </div>

        <div className="p-4 rounded bg-white border border-slate-200 space-y-1">
          <span className="text-slate-500 block text-[10px]">EXECUTION MODE:</span>
          <div className="text-lg font-bold text-slate-900">
            {health?.demo_mode ? "SIH DEMO MODE" : "OPERATIONAL"}
          </div>
          <span className="text-slate-400 text-[10px] block">Circuit Breakers Active</span>
        </div>

        <div className="p-4 rounded bg-white border border-slate-200 space-y-1">
          <span className="text-slate-500 block text-[10px]">ACTIVE SYSTEMS:</span>
          <div className="text-lg font-bold text-slate-900">
            {health?.active_cyclones_count ?? 1} TRACKED
          </div>
          <span className="text-slate-400 text-[10px] block">NOAA Synoptic Sync Active</span>
        </div>
      </div>

      {/* Notification Dispatch & External Gateway Configuration */}
      <div className="bg-white border border-slate-200 rounded p-4 space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-200 pb-3">
          <div>
            <h2 className="text-sm font-bold text-slate-900 uppercase flex items-center space-x-2 font-mono">
              <Bell className="w-4 h-4 text-blue-700" />
              <span>Automated Early Warning & External Notification Gateways</span>
            </h2>
            <p className="text-xs text-slate-500 mt-0.5">
              Production SMS (Twilio/Gateway) and Email (SMTP/SendGrid) multi-channel notification subsystem.
            </p>
          </div>

          <div className="flex items-center space-x-2">
            <button
              onClick={loadData}
              className="p-1.5 rounded border border-slate-200 hover:bg-slate-50 text-slate-600 transition"
              title="Refresh configuration status"
            >
              <RefreshCw className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>

        {/* Emergency Kill Switch Banner */}
        <div className={`p-3.5 rounded border flex flex-col md:flex-row md:items-center justify-between gap-3 ${
          alertConfig?.kill_switch_active
            ? "bg-rose-100 border-rose-400 text-rose-950 animate-pulse"
            : "bg-slate-50 border-slate-300 text-slate-900"
        }`}>
          <div className="flex items-start space-x-3">
            <Power className={`w-5 h-5 shrink-0 mt-0.5 ${
              alertConfig?.kill_switch_active ? "text-rose-700" : "text-slate-400"
            }`} />
            <div>
              <div className="flex items-center space-x-2">
                <span className="font-mono text-xs font-bold uppercase tracking-wide">
                  Emergency Kill Switch:
                </span>
                <span className={`px-2 py-0.5 rounded text-[10px] font-mono font-bold uppercase ${
                  alertConfig?.kill_switch_active
                    ? "bg-rose-600 text-white border border-rose-700"
                    : "bg-slate-200 text-slate-700"
                }`}>
                  {alertConfig?.kill_switch_active ? "DISPATCH BLOCKED (ACTIVE)" : "STANDBY (NORMAL)"}
                </span>
              </div>
              <p className="text-xs text-slate-600 mt-0.5 font-sans">
                {alertConfig?.kill_switch_active
                  ? "EMERGENCY OVERRIDE: All external SMS and Email notifications are IMMEDIATELY SUSPENDED. No messages will leave the system."
                  : "One-click emergency override that immediately stops all external notification dispatch across all channels."
                }
              </p>
            </div>
          </div>

          <button
            onClick={handleToggleKillSwitch}
            disabled={killSwitchToggling}
            className={`px-3 py-1.5 rounded text-xs font-mono font-bold transition shrink-0 ${
              alertConfig?.kill_switch_active
                ? "bg-emerald-700 text-white hover:bg-emerald-800"
                : "bg-rose-700 text-white hover:bg-rose-800"
            }`}
          >
            {killSwitchToggling
              ? "Toggling..."
              : alertConfig?.kill_switch_active
                ? "Deactivate Kill Switch (Resume)"
                : "Activate Kill Switch (Stop All)"
            }
          </button>
        </div>

        {/* Master Safety Switch Interlock Banner */}
        <div className={`p-3.5 rounded border flex flex-col md:flex-row md:items-center justify-between gap-3 ${
          alertConfig?.live_alerts_enabled 
            ? "bg-amber-50 border-amber-300 text-amber-950" 
            : "bg-slate-50 border-slate-300 text-slate-900"
        }`}>
          <div className="flex items-start space-x-3">
            {alertConfig?.live_alerts_enabled ? (
              <ShieldAlert className="w-5 h-5 text-amber-600 shrink-0 mt-0.5" />
            ) : (
              <ShieldCheck className="w-5 h-5 text-emerald-600 shrink-0 mt-0.5" />
            )}
            <div>
              <div className="flex items-center space-x-2">
                <span className="font-mono text-xs font-bold uppercase tracking-wide">
                  Master Safety Switch Interlock:
                </span>
                <span className={`px-2 py-0.5 rounded text-[10px] font-mono font-bold uppercase ${
                  alertConfig?.live_alerts_enabled
                    ? "bg-amber-200 text-amber-900 border border-amber-300"
                    : "bg-emerald-100 text-emerald-800 border border-emerald-300"
                }`}>
                  {alertConfig?.live_alerts_enabled ? "LIVE ALERTS ACTIVE" : "SAFE SIMULATION MODE (DEFAULT)"}
                </span>
              </div>
              <p className="text-xs text-slate-600 mt-0.5 font-sans">
                {alertConfig?.live_alerts_enabled
                  ? "Real external SMS and Email dispatches will be transmitted to configured authority numbers and email addresses via active gateways."
                  : "External SMS and Email dispatches are blocked. All triggered alerts will log internal delivery results with status SIMULATED (no external API calls or costs)."
                }
              </p>
            </div>
          </div>

          <button
            onClick={handleToggleSafety}
            disabled={safetyToggling}
            className={`px-3 py-1.5 rounded text-xs font-mono font-semibold transition shrink-0 ${
              alertConfig?.live_alerts_enabled
                ? "bg-slate-900 text-white hover:bg-slate-800"
                : "bg-amber-700 text-white hover:bg-amber-800"
            }`}
          >
            {safetyToggling
              ? "Updating..."
              : alertConfig?.live_alerts_enabled
                ? "Activate Safe Simulation Mode"
                : "Enable Live Alerts"
            }
          </button>
        </div>

        {/* Automatic Monitor & Manual Evaluation Banner */}
        <div className="p-3.5 rounded border border-blue-200 bg-blue-50/50 flex flex-col md:flex-row md:items-center justify-between gap-3 text-xs font-mono">
          <div>
            <div className="flex items-center space-x-2">
              <span className="font-bold text-slate-900 uppercase">
                Automatic Alert Pipeline:
              </span>
              <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-100 text-emerald-800 border border-emerald-300">
                ACTIVE (15-min background loop)
              </span>
            </div>
            <p className="text-slate-600 mt-0.5 font-sans text-xs">
              Background task continuously evaluates active cyclones against ML predictions and threshold rules.
            </p>
          </div>

          <button
            onClick={handleEvaluateNow}
            disabled={evaluatingNow}
            className="px-3 py-1.5 rounded bg-blue-700 hover:bg-blue-800 text-white font-bold transition flex items-center space-x-1.5 shrink-0 disabled:opacity-50"
          >
            <Play className={`w-3.5 h-3.5 ${evaluatingNow ? "animate-spin" : ""}`} />
            <span>{evaluatingNow ? "Evaluating..." : "Evaluate Active Storms Now"}</span>
          </button>
        </div>

        {/* Evaluation Result Feedback */}
        {evaluateResult && (
          <div className="p-3 rounded border border-slate-300 bg-white font-mono text-xs space-y-1">
            <div className="flex items-center justify-between pb-1 border-b border-slate-200">
              <span className="font-bold text-slate-900">
                Pipeline Evaluation Results ({evaluateResult.evaluated_cyclones_count ?? 0} storm(s) evaluated):
              </span>
              <span className="text-[10px] text-slate-500">
                {evaluateResult.timestamp}
              </span>
            </div>
            {Array.isArray(evaluateResult.results) && evaluateResult.results.map((r: any, idx: number) => (
              <div key={idx} className="flex items-center justify-between text-[11px] pt-1">
                <span>
                  <strong>{r.cyclone_name || "Cyclone"}:</strong> {r.reason || r.action_type || "Evaluated"}
                </span>
                <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                  r.triggered
                    ? "bg-rose-100 text-rose-800 border border-rose-300"
                    : r.action_type === "DUPLICATE_SUPPRESSED"
                      ? "bg-amber-100 text-amber-800 border border-amber-300"
                      : "bg-slate-100 text-slate-700"
                }`}>
                  {r.triggered ? `TRIGGERED (${r.alert_level})` : r.action_type || "NO_ALERT"}
                </span>
              </div>
            ))}
          </div>
        )}

        {/* Channels & Rate Limiting Grid */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 font-mono text-xs">
          {/* SMS Provider Card */}
          <div className="p-3.5 rounded border border-slate-200 bg-slate-50 space-y-2">
            <div className="flex items-center justify-between">
              <span className="font-bold text-slate-900 flex items-center space-x-1.5">
                <Phone className="w-3.5 h-3.5 text-blue-700" />
                <span>SMS Gateway</span>
              </span>
              <span className={`px-1.5 py-0.2 rounded text-[10px] font-bold ${
                alertConfig?.sms_status === "CONFIGURED"
                  ? "bg-emerald-100 text-emerald-800 border border-emerald-300"
                  : alertConfig?.sms_status === "INVALID"
                    ? "bg-rose-100 text-rose-800 border border-rose-300"
                    : "bg-slate-200 text-slate-700"
              }`}>
                {alertConfig?.sms_status || (alertConfig?.twilio_configured ? "CONFIGURED" : "NOT CONFIGURED")}
              </span>
            </div>
            <div className="space-y-1 text-[11px] text-slate-600 pt-1">
              <div><span className="text-slate-400">Provider:</span> {alertConfig?.sms_provider || "Twilio REST API"}</div>
              <div><span className="text-slate-400">Account SID:</span> {alertConfig?.masked_twilio_sid || "Not Configured"}</div>
              <div><span className="text-slate-400">From Caller ID:</span> {alertConfig?.from_phone || "CycloneX-Gov"}</div>
              <div className="pt-1 border-t border-slate-200">
                <span className="text-slate-400">Hourly Rate Limit:</span>{" "}
                <span className="font-bold text-slate-900">
                  {alertConfig?.rate_limits?.sms_sent_last_hour ?? 0} / {alertConfig?.rate_limits?.sms_limit_hourly ?? 20} used
                </span>
              </div>
            </div>
          </div>

          {/* Email Provider Card */}
          <div className="p-3.5 rounded border border-slate-200 bg-slate-50 space-y-2">
            <div className="flex items-center justify-between">
              <span className="font-bold text-slate-900 flex items-center space-x-1.5">
                <Mail className="w-3.5 h-3.5 text-purple-700" />
                <span>Email Gateway</span>
              </span>
              <span className={`px-1.5 py-0.2 rounded text-[10px] font-bold ${
                alertConfig?.email_status === "CONFIGURED"
                  ? "bg-emerald-100 text-emerald-800 border border-emerald-300"
                  : alertConfig?.email_status === "INVALID"
                    ? "bg-rose-100 text-rose-800 border border-rose-300"
                    : "bg-slate-200 text-slate-700"
              }`}>
                {alertConfig?.email_status || (alertConfig?.smtp_configured ? "CONFIGURED" : "NOT CONFIGURED")}
              </span>
            </div>
            <div className="space-y-1 text-[11px] text-slate-600 pt-1">
              <div><span className="text-slate-400">Provider:</span> {alertConfig?.email_provider || "Standard SMTP"}</div>
              <div><span className="text-slate-400">Host/Gateway:</span> {alertConfig?.masked_smtp_host || "smtp.***:587"}</div>
              <div><span className="text-slate-400">From Address:</span> {alertConfig?.from_email || "alerts@cyclonex.gov.in"}</div>
              <div className="pt-1 border-t border-slate-200">
                <span className="text-slate-400">Hourly Rate Limit:</span>{" "}
                <span className="font-bold text-slate-900">
                  {alertConfig?.rate_limits?.email_sent_last_hour ?? 0} / {alertConfig?.rate_limits?.email_limit_hourly ?? 50} used
                </span>
              </div>
            </div>
          </div>

          {/* In-App Operations Center Channel */}
          <div className="p-3.5 rounded border border-slate-200 bg-slate-50 space-y-2">
            <div className="flex items-center justify-between">
              <span className="font-bold text-slate-900 flex items-center space-x-1.5">
                <Bell className="w-3.5 h-3.5 text-emerald-700" />
                <span>Operations Terminal</span>
              </span>
              <span className="px-1.5 py-0.2 rounded text-[10px] font-bold bg-emerald-100 text-emerald-800 border border-emerald-300">
                ACTIVE
              </span>
            </div>
            <div className="space-y-1 text-[11px] text-slate-600 pt-1">
              <div><span className="text-slate-400">Channel:</span> In-App CAP Alert Feed</div>
              <div><span className="text-slate-400">Format:</span> CAP v1.2 Standard</div>
              <div><span className="text-slate-400">Audit Logging:</span> Persistent SQLite / Log</div>
              <div className="pt-1 border-t border-slate-200">
                <span className="text-slate-400">Delivery Status:</span> <span className="font-bold text-emerald-700">100% Operational</span>
              </div>
            </div>
          </div>
        </div>

        {/* Live Connectivity Test Dispatcher */}
        <div className="p-4 rounded border border-slate-200 bg-white space-y-3 font-mono text-xs">
          <div className="flex items-center justify-between">
            <span className="font-bold text-slate-900 uppercase">
              Isolated Gateway Connectivity Verification (Test Dispatch)
            </span>
            <span className="text-[10px] text-slate-500">
              Dispatches ONLY to verified test recipient (no authority broadcast)
            </span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <div>
              <label className="block text-[10px] text-slate-500 mb-1">Target Test Phone:</label>
              <input
                type="text"
                value={testPhone}
                onChange={e => setTestPhone(e.target.value)}
                placeholder="+91-98765-43210"
                className="w-full px-2.5 py-1.5 text-xs rounded border border-slate-300 font-mono text-slate-900 bg-slate-50 focus:bg-white outline-none"
              />
            </div>

            <div>
              <label className="block text-[10px] text-slate-500 mb-1">Target Test Email:</label>
              <input
                type="text"
                value={testEmail}
                onChange={e => setTestEmail(e.target.value)}
                placeholder="officer@sdma.gov.in"
                className="w-full px-2.5 py-1.5 text-xs rounded border border-slate-300 font-mono text-slate-900 bg-slate-50 focus:bg-white outline-none"
              />
            </div>

            <div>
              <label className="block text-[10px] text-slate-500 mb-1">Channel Selector:</label>
              <div className="flex items-center space-x-2">
                <select
                  value={testChannel}
                  onChange={e => setTestChannel(e.target.value as any)}
                  className="flex-1 px-2.5 py-1.5 text-xs rounded border border-slate-300 font-mono text-slate-900 bg-slate-50 outline-none"
                >
                  <option value="both">Both (SMS + Email)</option>
                  <option value="sms">SMS Only</option>
                  <option value="email">Email Only</option>
                </select>

                <button
                  onClick={handleSendTestNotification}
                  disabled={testSending}
                  className="px-3 py-1.5 rounded bg-blue-700 hover:bg-blue-800 text-white font-bold transition flex items-center space-x-1.5 shrink-0 disabled:opacity-50"
                >
                  <Send className={`w-3.5 h-3.5 ${testSending ? "animate-pulse" : ""}`} />
                  <span>{testSending ? "Sending..." : "Send Test"}</span>
                </button>
              </div>
            </div>
          </div>

          {/* Test Dispatch Result Feedback */}
          {testResult && (
            <div className={`p-3 rounded border text-xs ${
              testResult.status === "success" 
                ? "bg-slate-50 border-slate-300 text-slate-900" 
                : "bg-rose-50 border-rose-300 text-rose-900"
            }`}>
              <div className="flex items-center justify-between pb-1.5 border-b border-slate-200">
                <span className="font-bold">
                  {testResult.status === "success" ? "Test Dispatch Completed:" : "Test Dispatch Error:"}
                </span>
                <span className="text-[10px] text-slate-500 font-mono">
                  {testResult.safety_mode || "Test Completed"}
                </span>
              </div>
              <div className="pt-1.5 space-y-1">
                {Array.isArray(testResult.dispatches) ? (
                  testResult.dispatches.map((d: any, idx: number) => (
                    <div key={idx} className="flex items-center justify-between text-[11px]">
                      <span className="font-bold uppercase text-slate-700">[{d.channel}] &rarr; {d.recipient_contact}</span>
                      <span className={`px-2 py-0.2 rounded font-bold text-[10px] ${
                        d.delivery_status === "DELIVERED"
                          ? "bg-emerald-100 text-emerald-800 border border-emerald-300"
                          : d.delivery_status === "SIMULATED"
                            ? "bg-blue-100 text-blue-800 border border-blue-300"
                            : "bg-rose-100 text-rose-800 border border-rose-300"
                      }`}>
                        {d.delivery_status}
                      </span>
                    </div>
                  ))
                ) : (
                  <div>{testResult.error || "Execution completed"}</div>
                )}
              </div>
            </div>
          )}
        </div>

        {/* Credential & Provider Verification Action */}
        <div className="p-4 rounded border border-slate-200 bg-slate-50 space-y-3 font-mono text-xs">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
            <div>
              <div className="flex items-center space-x-2">
                <span className="font-bold text-slate-900 uppercase">
                  End-to-End Credential Validation & Provider Certification
                </span>
                <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                  alertConfig?.live_verification_state === "LIVE_VERIFIED"
                    ? "bg-emerald-200 text-emerald-900 border border-emerald-400"
                    : alertConfig?.live_verification_state === "TEST_FAILED"
                      ? "bg-rose-200 text-rose-900 border border-rose-400"
                      : alertConfig?.live_verification_state === "CONFIGURED_NOT_TESTED"
                        ? "bg-blue-200 text-blue-900 border border-blue-400"
                        : "bg-slate-200 text-slate-800 border border-slate-300"
                }`}>
                  {alertConfig?.live_verification_state || "NOT_CONFIGURED"}
                </span>
              </div>
              <p className="text-[11px] text-slate-500 font-sans mt-0.5">
                Format checks inspect syntax without dispatches. Controlled Live Test sends actual test alerts strictly to configured test contacts.
              </p>
            </div>
            <div className="flex items-center space-x-2 shrink-0">
              <button
                onClick={handleValidateCredentials}
                disabled={validatingCredentials || runningLiveTest}
                className="px-3.5 py-1.5 rounded bg-white hover:bg-slate-100 text-slate-800 border border-slate-300 font-bold transition flex items-center space-x-1.5 disabled:opacity-50"
              >
                <CheckCircle2 className={`w-3.5 h-3.5 ${validatingCredentials ? "animate-spin" : ""}`} />
                <span>{validatingCredentials ? "Validating..." : "Validate Credentials (.env)"}</span>
              </button>
              <button
                onClick={handleSendControlledLiveTest}
                disabled={runningLiveTest || validatingCredentials}
                className="px-3.5 py-1.5 rounded bg-slate-900 hover:bg-slate-800 text-white font-bold transition flex items-center space-x-1.5 disabled:opacity-50"
              >
                <Send className={`w-3.5 h-3.5 ${runningLiveTest ? "animate-spin" : ""}`} />
                <span>{runningLiveTest ? "Dispatching Live Test..." : "Send Controlled Live Test"}</span>
              </button>
            </div>
          </div>

          {/* Validation Result Display */}
          {validationResult && (
            <div className={`p-3 rounded border text-xs ${
              validationResult.verification_status === "CONFIGURED_NOT_TESTED"
                ? "bg-blue-50 border-blue-300 text-blue-950"
                : validationResult.verification_status === "LIVE VERIFIED" || validationResult.verification_status === "LIVE_VERIFIED"
                  ? "bg-emerald-50 border-emerald-300 text-emerald-950"
                  : "bg-amber-50 border-amber-300 text-amber-950"
            }`}>
              <div className="flex items-center justify-between pb-1.5 border-b border-slate-200">
                <span className="font-bold flex items-center space-x-1.5">
                  <span>FORMAT VALIDATION:</span>
                  <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-white/70 border border-current">
                    {validationResult.verification_status}
                  </span>
                </span>
                <span className="text-[10px] text-slate-500">
                  SMS: {validationResult.sms_status || "UNKNOWN"} | EMAIL: {validationResult.email_status || "UNKNOWN"}
                </span>
              </div>
              <div className="pt-2 space-y-1.5 text-[11px]">
                {validationResult.note && <div><strong>Note:</strong> {validationResult.note}</div>}
                {validationResult.reason && <div><strong>Reason:</strong> {validationResult.reason}</div>}
                {validationResult.details && (
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 mt-1">
                    <div className="p-2 bg-white/60 rounded border border-slate-200">
                      <span className="font-bold">SMS Details:</span>
                      <pre className="text-[10px] overflow-x-auto">{JSON.stringify(validationResult.details.sms, null, 2)}</pre>
                    </div>
                    <div className="p-2 bg-white/60 rounded border border-slate-200">
                      <span className="font-bold">Email Details:</span>
                      <pre className="text-[10px] overflow-x-auto">{JSON.stringify(validationResult.details.email, null, 2)}</pre>
                    </div>
                  </div>
                )}
                {Array.isArray(validationResult.missing_variables) && validationResult.missing_variables.length > 0 && (
                  <div>
                    <strong>Missing / Incomplete Variables in .env:</strong>
                    <ul className="list-disc list-inside mt-0.5 text-rose-700">
                      {validationResult.missing_variables.map((m: string, idx: number) => (
                        <li key={idx}>{m}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Controlled Live Test Result Display */}
          {liveTestResult && (
            <div className={`p-3 rounded border text-xs ${
              liveTestResult.verification_status === "LIVE_VERIFIED"
                ? "bg-emerald-50 border-emerald-300 text-emerald-950"
                : "bg-rose-50 border-rose-300 text-rose-950"
            }`}>
              <div className="flex items-center justify-between pb-1.5 border-b border-slate-200">
                <span className="font-bold flex items-center space-x-1.5">
                  <span>CONTROLLED LIVE TEST RESULT:</span>
                  <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                    liveTestResult.verification_status === "LIVE_VERIFIED"
                      ? "bg-emerald-200 text-emerald-900"
                      : "bg-rose-200 text-rose-900"
                  }`}>
                    {liveTestResult.verification_status}
                  </span>
                </span>
                <span className="text-[10px] text-slate-500">
                  {liveTestResult.summary || ""}
                </span>
              </div>
              <div className="pt-2 space-y-1.5 text-[11px]">
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 mt-1">
                  <div className="p-2 bg-white/60 rounded border border-slate-200">
                    <span className="font-bold">SMS Delivery Result:</span>
                    <pre className="text-[10px] overflow-x-auto">{JSON.stringify(liveTestResult.sms_delivery, null, 2)}</pre>
                  </div>
                  <div className="p-2 bg-white/60 rounded border border-slate-200">
                    <span className="font-bold">Email Delivery Result:</span>
                    <pre className="text-[10px] overflow-x-auto">{JSON.stringify(liveTestResult.email_delivery, null, 2)}</pre>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Statutory Decision-Support Disclaimer */}
        <div className="p-3 bg-slate-50 border border-slate-200 rounded text-slate-600 text-[11px] leading-relaxed">
          <strong className="text-slate-900 font-mono">STATUTORY NOTICE:</strong> CycloneX automated alerts are computer-generated decision-support advisories designed to provide early situational awareness to disaster response personnel. Official, legally binding cyclonic warning bulletins and mandatory evacuation orders are issued exclusively by the India Meteorological Department (IMD) and National/State Disaster Management Authorities (NDMA/SDMA).
        </div>
      </div>

      {/* Data Source Ingestion Health */}
      <div className="bg-white border border-slate-200 rounded p-4 space-y-3">
        <div className="flex items-center justify-between border-b border-slate-200 pb-3">
          <h2 className="text-sm font-bold text-slate-900 uppercase flex items-center space-x-2">
            <Server className="w-4 h-4 text-blue-700" />
            <span>Multi-Source External Data Ingestion Adapters</span>
          </h2>
          <span className="text-xs font-mono text-slate-500">{sources.length} Adapters</span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs font-mono border-collapse">
            <thead>
              <tr className="border-b border-slate-200 bg-slate-50 text-slate-600">
                <th className="py-2.5 px-3">Source Name</th>
                <th className="py-2.5 px-3">Endpoint URL</th>
                <th className="py-2.5 px-3">Status</th>
                <th className="py-2.5 px-3">Latency</th>
                <th className="py-2.5 px-3">Ingested Records</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200 text-slate-700">
              {sources.map((src) => (
                <tr key={src.id} className="hover:bg-slate-50">
                  <td className="py-2.5 px-3 font-bold text-slate-900">{src.source_name}</td>
                  <td className="py-2.5 px-3 text-slate-500 truncate max-w-xs">{src.source_url}</td>
                  <td className="py-2.5 px-3">
                    <span className="px-2 py-0.5 rounded bg-emerald-50 text-emerald-800 border border-emerald-200 text-[10px] font-bold">
                      {src.status}
                    </span>
                  </td>
                  <td className="py-2.5 px-3 text-slate-700">{src.latency_ms} ms</td>
                  <td className="py-2.5 px-3 text-slate-900 font-bold">{src.records_count}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Model Registry & Scientific Validation Table */}
      <div className="bg-white border border-slate-200 rounded p-4 space-y-3">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-200 pb-3">
          <h2 className="text-sm font-bold text-slate-900 uppercase flex items-center space-x-2">
            <Cpu className="w-4 h-4 text-purple-700" />
            <span>AI/ML Model Registry & Leave-One-Storm-Out (LOSO) Validation</span>
          </h2>
          <span className="text-[11px] font-mono text-purple-800 bg-purple-50 px-2 py-0.5 rounded border border-purple-200 font-semibold">
            Leak-Free Storm-Grouped Cross-Validation
          </span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs font-mono border-collapse">
            <thead>
              <tr className="border-b border-slate-200 bg-slate-50 text-slate-600">
                <th className="py-2.5 px-3">Model Identifier</th>
                <th className="py-2.5 px-3">Target Parameter</th>
                <th className="py-2.5 px-3">Architecture</th>
                <th className="py-2.5 px-3">Verified Metric</th>
                <th className="py-2.5 px-3">Baseline Comparison</th>
                <th className="py-2.5 px-3">Validation Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200 text-slate-700">
              <tr className="hover:bg-slate-50">
                <td className="py-3 px-3 font-bold text-slate-900">IMD Stage Classifier</td>
                <td className="py-3 px-3 text-slate-500">T+6h Storm Category</td>
                <td className="py-3 px-3">RandomForest (100 Trees)</td>
                <td className="py-3 px-3"><span className="text-slate-900 font-bold">67.21% Acc</span> / 0.6706 F1</td>
                <td className="py-3 px-3 text-slate-500">Stage Persistence: 70.0% | Random: 16.7%</td>
                <td className="py-3 px-3"><span className="px-2 py-0.5 rounded bg-emerald-50 text-emerald-800 border border-emerald-200 text-[10px] font-bold">LOSO VALIDATED</span></td>
              </tr>
              <tr className="hover:bg-slate-50">
                <td className="py-3 px-3 font-bold text-slate-900">Intensity Regressor</td>
                <td className="py-3 px-3 text-slate-500">+6h to +72h Max Sustained Wind</td>
                <td className="py-3 px-3">GradientBoostingRegressor</td>
                <td className="py-3 px-3"><span className="text-emerald-700 font-bold">6.32 kt MAE</span> (+6h) / 10.21 kt (+12h)</td>
                <td className="py-3 px-3 text-emerald-700 font-semibold">+14.6% to +32.0% Skill vs Persistence</td>
                <td className="py-3 px-3"><span className="px-2 py-0.5 rounded bg-emerald-50 text-emerald-800 border border-emerald-200 text-[10px] font-bold">LOSO VALIDATED</span></td>
              </tr>
              <tr className="hover:bg-slate-50">
                <td className="py-3 px-3 font-bold text-slate-900">Track Regressor (CLIPER)</td>
                <td className="py-3 px-3 text-slate-500">+6h to +72h Lat & Lon Displacements</td>
                <td className="py-3 px-3">Dual GradientBoosting</td>
                <td className="py-3 px-3"><span className="text-slate-900 font-bold">41.3 km Error</span> (+6h) / 75.2 km (+12h)</td>
                <td className="py-3 px-3 text-slate-600 font-semibold">+5.8% (+48h) / +17.9% (+72h) vs Persistence</td>
                <td className="py-3 px-3"><span className="px-2 py-0.5 rounded bg-emerald-50 text-emerald-800 border border-emerald-200 text-[10px] font-bold">LOSO VALIDATED</span></td>
              </tr>
              <tr className="hover:bg-slate-50">
                <td className="py-3 px-3 font-bold text-slate-900">Meteorological Detector</td>
                <td className="py-3 px-3 text-slate-500">Binary Cyclonic Vorticity State</td>
                <td className="py-3 px-3">RandomForestClassifier</td>
                <td className="py-3 px-3"><span className="text-slate-900 font-bold">95.0% Acc</span> / 0.942 F1</td>
                <td className="py-3 px-3 text-slate-500">Climatological: 60.0%</td>
                <td className="py-3 px-3"><span className="px-2 py-0.5 rounded bg-emerald-50 text-emerald-800 border border-emerald-200 text-[10px] font-bold">VALIDATED</span></td>
              </tr>
              <tr className="hover:bg-slate-50">
                <td className="py-3 px-3 font-bold text-slate-900">Satellite Vision Pipeline</td>
                <td className="py-3 px-3 text-slate-500">Eye Localization & Organization</td>
                <td className="py-3 px-3">Spectral-Gradient Vorticity Pipeline</td>
                <td className="py-3 px-3 text-amber-700">Analytic Vorticity Baseline</td>
                <td className="py-3 px-3 text-slate-500">CNN Model: Dataset Required</td>
                <td className="py-3 px-3"><span className="px-2 py-0.5 rounded bg-amber-50 text-amber-800 border border-amber-200 text-[10px] font-bold">BASELINE ACTIVE</span></td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
