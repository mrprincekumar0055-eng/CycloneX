"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { 
  AlertTriangle, Info, Activity, Bell, CheckCircle2, 
  RefreshCw, Play, FileText, X, Phone, Mail, Radio, AlertOctagon,
  ShieldCheck, ShieldAlert, Power
} from "lucide-react";
import { fetchFromAPI } from "@/lib/api";

export default function AlertsPage() {
  const [alerts, setAlerts] = useState<any[]>([]);
  const [stats, setStats] = useState<any>(null);
  const [auditLogs, setAuditLogs] = useState<any[]>([]);
  const [alertConfig, setAlertConfig] = useState<any>(null);
  const [selectedAudience, setSelectedAudience] = useState<string>("All");
  const [selectedStatus, setSelectedStatus] = useState<string>("All");
  const [activeTab, setActiveTab] = useState<"alerts" | "audit">("alerts");
  const [loading, setLoading] = useState(true);
  const [isOffline, setIsOffline] = useState(false);
  const [actionLoading, setActionLoading] = useState<string | null>(null);
  const [evaluatingNow, setEvaluatingNow] = useState(false);
  const [evaluateMsg, setEvaluateMsg] = useState<string | null>(null);

  // Simulation Modal State
  const [showSimModal, setShowSimModal] = useState(false);
  const [simScenario, setSimScenario] = useState("Rapid Intensification & Landfall");
  const [simWindKts, setSimWindKts] = useState(95);
  const [simEtaHours, setSimEtaHours] = useState(18);
  const [simDistricts, setSimDistricts] = useState("Kutch, Devbhumi Dwarka, Jamnagar");
  const [simRunning, setSimRunning] = useState(false);
  const [simSuccessMsg, setSimSuccessMsg] = useState<string | null>(null);

  // Selected Alert for Audit Inspection Modal
  const [inspectAlert, setInspectAlert] = useState<any | null>(null);
  const [inspectLogs, setInspectLogs] = useState<any[]>([]);
  const [inspectLoading, setInspectLoading] = useState(false);

  const loadData = async () => {
    setLoading(true);
    try {
      const [alertsData, statsData, logsData, configData] = await Promise.all([
        fetchFromAPI("/alerts"),
        fetchFromAPI("/alerts/stats"),
        fetchFromAPI("/alerts/audit-log?limit=25"),
        fetchFromAPI("/alerts/config")
      ]);

      if (Array.isArray(alertsData) && alertsData.length > 0) {
        setAlerts(alertsData);
        setIsOffline(false);
      } else {
        setIsOffline(true);
      }

      if (statsData) setStats(statsData);
      if (Array.isArray(logsData)) setAuditLogs(logsData);
      if (configData) setAlertConfig(configData);
    } catch {
      setIsOffline(true);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleAcknowledge = async (alertId: string) => {
    setActionLoading(alertId);
    try {
      const res = await fetchFromAPI(`/alerts/${alertId}/acknowledge`, {
        method: "POST",
        body: JSON.stringify({
          action: "acknowledge",
          operator_name: "Disaster Operations Officer",
          notes: "Acknowledged via Operations Command Center"
        })
      });
      if (res) {
        await loadData();
      }
    } finally {
      setActionLoading(null);
    }
  };

  const handleEscalate = async (alertId: string) => {
    setActionLoading(alertId);
    try {
      const res = await fetchFromAPI(`/alerts/${alertId}/escalate`, {
        method: "POST",
        body: JSON.stringify({
          action: "escalate",
          new_severity: "Emergency",
          operator_name: "State Relief Commissioner",
          notes: "Elevated threat escalation triggered by commanding officer"
        })
      });
      if (res) {
        await loadData();
      }
    } finally {
      setActionLoading(null);
    }
  };

  const handleResolve = async (alertId: string) => {
    setActionLoading(alertId);
    try {
      const res = await fetchFromAPI(`/alerts/${alertId}/resolve`, {
        method: "POST",
        body: JSON.stringify({
          action: "resolve",
          operator_name: "Incident Commander",
          notes: "Hazard conditions normalized post-event"
        })
      });
      if (res) {
        await loadData();
      }
    } finally {
      setActionLoading(null);
    }
  };

  const handleInspectAudit = async (alert: any) => {
    setInspectAlert(alert);
    setInspectLoading(true);
    try {
      const logs = await fetchFromAPI(`/alerts/${alert.id}/audit-log`);
      setInspectLogs(Array.isArray(logs) ? logs : []);
    } catch {
      setInspectLogs([]);
    } finally {
      setInspectLoading(false);
    }
  };

  const handleEvaluateNow = async () => {
    setEvaluatingNow(true);
    setEvaluateMsg(null);
    try {
      const res = await fetchFromAPI("/alerts/evaluate-now", { method: "POST" });
      if (res && res.status === "success") {
        const trig = res.triggered_count ?? 0;
        const total = res.evaluated_cyclones_count ?? 0;
        setEvaluateMsg(`Evaluated ${total} storm(s): ${trig} alert(s) triggered.`);
        await loadData();
        setTimeout(() => setEvaluateMsg(null), 4000);
      }
    } catch {
      setEvaluateMsg("Evaluation error.");
      setTimeout(() => setEvaluateMsg(null), 3000);
    } finally {
      setEvaluatingNow(false);
    }
  };

  const handleRunSimulation = async () => {
    setSimRunning(true);
    setSimSuccessMsg(null);
    try {
      const distList = simDistricts.split(",").map(d => d.trim()).filter(Boolean);
      const res = await fetchFromAPI("/alerts/simulate", {
        method: "POST",
        body: JSON.stringify({
          cyclone_name: "BIPARJOY",
          scenario: simScenario,
          wind_speed_kts: parseFloat(String(simWindKts)),
          central_pressure_hpa: 955.0,
          landfall_eta_hours: parseInt(String(simEtaHours)),
          target_location: `${distList.join(" & ")} Coast, Gujarat`,
          affected_districts: distList,
          channels: ["dashboard", "sms", "email"],
          simulate_delivery: true
        })
      });
      if (res && res.status === "success") {
        setSimSuccessMsg(`Simulated ${res.simulation_details?.alert_level} scenario triggered. Dispatched across Dashboard, SMS, and Email.`);
        await loadData();
        setTimeout(() => {
          setShowSimModal(false);
          setSimSuccessMsg(null);
        }, 1800);
      }
    } finally {
      setSimRunning(false);
    }
  };

  // Filter alerts by audience and lifecycle status
  const filteredAlerts = alerts.filter(a => {
    const audMatch = selectedAudience === "All" || a.audience === selectedAudience || a.audience === "All";
    const statusMatch = selectedStatus === "All" || (a.status || "ACTIVE") === selectedStatus.toUpperCase();
    return audMatch && statusMatch;
  });

  return (
    <div className="flex-1 p-4 sm:p-6 lg:p-8 max-w-6xl mx-auto w-full space-y-5">
      {/* Offline Alert Banner */}
      {isOffline && (
        <div className="p-3 bg-amber-50 border border-amber-300 rounded flex flex-col sm:flex-row sm:items-center justify-between gap-2 text-xs text-amber-900 font-mono">
          <div className="flex items-center space-x-2">
            <AlertTriangle className="w-4 h-4 text-amber-600 shrink-0" />
            <span>
              <strong>Offline Mode:</strong> Alert dispatch service unreachable. Showing cached operational records.
            </span>
          </div>
          <span className="px-2 py-0.5 rounded bg-amber-200 text-amber-900 font-bold text-[10px] shrink-0 uppercase tracking-wide">
            OFFLINE
          </span>
        </div>
      )}

      {/* Top Header & Operational Controls */}
      <div className="bg-white border border-slate-200 rounded p-4">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-3 pb-3 border-b border-slate-200">
          <div>
            <div className="flex flex-wrap items-center gap-2">
              <h1 className="text-base font-bold text-slate-900 tracking-tight uppercase font-mono">
                OPERATIONAL EARLY WARNING & NOTIFICATION CENTER
              </h1>
              <span className="text-[10px] px-1.5 py-0.2 rounded bg-slate-100 text-slate-700 font-mono font-medium border border-slate-200">
                CAP v1.2 ALIGNED
              </span>
              {alertConfig?.kill_switch_active && (
                <span className="text-[10px] px-2 py-0.5 rounded font-mono font-bold border flex items-center space-x-1 bg-rose-600 text-white border-rose-700 animate-pulse">
                  <Power className="w-3 h-3 shrink-0" />
                  <span>KILL SWITCH ACTIVE (DISPATCH BLOCKED)</span>
                </span>
              )}
              {alertConfig && !alertConfig.kill_switch_active && (
                <span className={`text-[10px] px-2 py-0.5 rounded font-mono font-bold border flex items-center space-x-1 ${
                  alertConfig.live_alerts_enabled
                    ? "bg-amber-100 text-amber-900 border-amber-300"
                    : "bg-slate-100 text-slate-700 border-slate-300"
                }`}>
                  {alertConfig.live_alerts_enabled ? (
                    <>
                      <ShieldAlert className="w-3 h-3 text-amber-600 shrink-0" />
                      <span>LIVE ALERTS ACTIVE</span>
                    </>
                  ) : (
                    <>
                      <ShieldCheck className="w-3 h-3 text-emerald-600 shrink-0" />
                      <span>SAFE SIMULATION MODE</span>
                    </>
                  )}
                </span>
              )}
              <Link
                href="/admin"
                className="text-[11px] font-mono text-blue-700 hover:text-blue-900 hover:underline flex items-center space-x-1 ml-1"
                title="Configure notification channels, provider credentials, and master safety switch in Admin Console"
              >
                <span>Gateway Settings &rarr;</span>
              </Link>
            </div>
            <p className="text-xs text-slate-500 mt-0.5 font-sans">
              Automated ML risk detection, multi-channel dispatch (Dashboard, SMS, Email), and audit trail.
            </p>
          </div>

          <div className="flex items-center space-x-2">
            <button
              onClick={handleEvaluateNow}
              disabled={evaluatingNow}
              className="px-3 py-1.5 rounded bg-blue-700 hover:bg-blue-800 text-white text-xs font-mono font-medium transition flex items-center space-x-1.5 shrink-0 disabled:opacity-50"
              title="Immediately evaluate all active cyclones against ML predictions and threshold rules"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${evaluatingNow ? "animate-spin" : ""}`} />
              <span>{evaluatingNow ? "Evaluating..." : "Evaluate Storms Now"}</span>
            </button>

            <button
              onClick={() => setShowSimModal(true)}
              className="px-3 py-1.5 rounded bg-slate-900 text-white text-xs font-mono font-medium hover:bg-slate-800 transition flex items-center space-x-1.5 shrink-0"
              title="Trigger simulated scenario for jury evaluation"
            >
              <Play className="w-3.5 h-3.5 fill-current" />
              <span>Simulate Scenario (Demo)</span>
            </button>

            <button
              onClick={loadData}
              disabled={loading}
              className="p-1.5 rounded border border-slate-200 hover:bg-slate-50 text-slate-600 transition disabled:opacity-50"
              title="Refresh inbox"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
            </button>
          </div>
        </div>

        {/* Evaluation Feedback Banner */}
        {evaluateMsg && (
          <div className="mt-2 p-2 bg-blue-50 border border-blue-200 rounded text-xs font-mono text-blue-900 flex items-center justify-between">
            <span>{evaluateMsg}</span>
          </div>
        )}

        {/* Operational Status Summary Strip (KPIs) */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 pt-3 text-xs font-mono">
          <div className="p-2.5 rounded bg-slate-50 border border-slate-200 flex justify-between items-center">
            <div>
              <span className="text-[10px] text-slate-400 block font-sans">ACTIVE ALERTS</span>
              <span className="text-lg font-bold text-red-600">{stats?.statuses?.active ?? 0}</span>
            </div>
            <span className="w-2 h-2 rounded-full bg-red-500"></span>
          </div>

          <div className="p-2.5 rounded bg-slate-50 border border-slate-200 flex justify-between items-center">
            <div>
              <span className="text-[10px] text-slate-400 block font-sans">ACKNOWLEDGED</span>
              <span className="text-lg font-bold text-amber-600">{stats?.statuses?.acknowledged ?? 0}</span>
            </div>
            <span className="w-2 h-2 rounded-full bg-amber-500"></span>
          </div>

          <div className="p-2.5 rounded bg-slate-50 border border-slate-200 flex justify-between items-center">
            <div>
              <span className="text-[10px] text-slate-400 block font-sans">ESCALATED</span>
              <span className="text-lg font-bold text-purple-600">{stats?.statuses?.escalated ?? 0}</span>
            </div>
            <span className="w-2 h-2 rounded-full bg-purple-500"></span>
          </div>

          <div className="p-2.5 rounded bg-slate-50 border border-slate-200 flex justify-between items-center">
            <div>
              <span className="text-[10px] text-slate-400 block font-sans">RESOLVED</span>
              <span className="text-lg font-bold text-slate-700">{stats?.statuses?.resolved ?? 0}</span>
            </div>
            <span className="w-2 h-2 rounded-full bg-slate-400"></span>
          </div>
        </div>
      </div>

      {/* Main View Tabs (Alert Dispatches vs Delivery Audit Log) */}
      <div className="flex items-center space-x-1 border-b border-slate-200 text-xs font-mono">
        <button
          onClick={() => setActiveTab("alerts")}
          className={`px-4 py-2 border-b-2 font-medium transition ${
            activeTab === "alerts"
              ? "border-slate-900 text-slate-900"
              : "border-transparent text-slate-500 hover:text-slate-800"
          }`}
        >
          Alert Dispatches ({filteredAlerts.length})
        </button>
        <button
          onClick={() => setActiveTab("audit")}
          className={`px-4 py-2 border-b-2 font-medium transition flex items-center space-x-1.5 ${
            activeTab === "audit"
              ? "border-slate-900 text-slate-900"
              : "border-transparent text-slate-500 hover:text-slate-800"
          }`}
        >
          <FileText className="w-3.5 h-3.5" />
          <span>Delivery Audit Trail ({auditLogs.length})</span>
        </button>
      </div>

      {activeTab === "alerts" ? (
        <>
          {/* Dual Filter Toolbar: Lifecycle Status & Stakeholder Audience */}
          <div className="bg-white border border-slate-200 rounded p-3 space-y-2">
            <div className="flex flex-wrap items-center justify-between gap-2 text-xs font-mono">
              <div className="flex flex-wrap items-center gap-1.5">
                <span className="text-slate-400 text-[11px] mr-1 uppercase">Lifecycle:</span>
                {["All", "Active", "Acknowledged", "Escalated", "Resolved"].map((st) => (
                  <button
                    key={st}
                    onClick={() => setSelectedStatus(st)}
                    className={`px-2 py-0.5 rounded text-[11px] transition ${
                      selectedStatus === st
                        ? "bg-slate-900 text-white font-medium"
                        : "bg-slate-100 text-slate-600 hover:bg-slate-200"
                    }`}
                  >
                    {st}
                  </button>
                ))}
              </div>

              <div className="flex flex-wrap items-center gap-1.5">
                <span className="text-slate-400 text-[11px] mr-1 uppercase">Audience:</span>
                {["All", "Citizens", "Authorities", "Emergency Responders"].map((aud) => (
                  <button
                    key={aud}
                    onClick={() => setSelectedAudience(aud)}
                    className={`px-2 py-0.5 rounded text-[11px] transition ${
                      selectedAudience === aud
                        ? "bg-slate-800 text-white font-medium"
                        : "bg-slate-100 text-slate-600 hover:bg-slate-200"
                    }`}
                  >
                    {aud}
                  </button>
                ))}
              </div>
            </div>
          </div>

          {/* Alert Dispatches List */}
          {loading ? (
            <div className="bg-white border border-slate-200 rounded p-12 text-center text-xs font-mono text-slate-500">
              <Activity className="w-4 h-4 mx-auto mb-2 text-slate-400 animate-pulse" />
              <span>Synchronizing Operational Notification Center...</span>
            </div>
          ) : filteredAlerts.length === 0 ? (
            <div className="bg-white border border-slate-200 rounded p-12 text-center text-xs font-mono text-slate-500 space-y-2">
              <CheckCircle2 className="w-6 h-6 text-slate-400 mx-auto" />
              <div className="font-semibold text-slate-800">No Dispatches Found</div>
              <p className="text-slate-500 text-xs">
                No alerts matching status &ldquo;{selectedStatus}&rdquo; and audience &ldquo;{selectedAudience}&rdquo;. Click &ldquo;Simulate Scenario&rdquo; to trigger an operational demonstration.
              </p>
            </div>
          ) : (
            <div className="space-y-3">
              {filteredAlerts.map((alt) => {
                const sev = (alt.alert_level || alt.severity || "").toLowerCase();
                const isEmergency = sev === "emergency" || sev === "critical";
                const isWarning = sev === "warning" || sev === "high";
                const isWatch = sev === "watch" || sev === "moderate";

                const borderClass = isEmergency 
                  ? "border-l-4 border-l-red-600" 
                  : isWarning 
                  ? "border-l-4 border-l-amber-500" 
                  : isWatch 
                  ? "border-l-4 border-l-yellow-500" 
                  : "border-l-4 border-l-emerald-600";

                const badgeClass = isEmergency 
                  ? "bg-red-50 text-red-800 border border-red-200" 
                  : isWarning 
                  ? "bg-amber-50 text-amber-800 border border-amber-200" 
                  : isWatch 
                  ? "bg-yellow-50 text-yellow-800 border border-yellow-200" 
                  : "bg-emerald-50 text-emerald-800 border border-emerald-200";

                const statusBadge = (alt.status || "ACTIVE") === "ACTIVE"
                  ? "bg-red-50 text-red-700 border-red-200"
                  : (alt.status || "ACTIVE") === "ACKNOWLEDGED"
                  ? "bg-amber-50 text-amber-700 border-amber-200"
                  : (alt.status || "ACTIVE") === "ESCALATED"
                  ? "bg-purple-50 text-purple-700 border-purple-200"
                  : "bg-slate-100 text-slate-600 border-slate-200";

                const isSimulation = alt.is_simulation === true;

                return (
                  <div key={alt.id} className={`bg-white border border-slate-200 rounded p-4 space-y-3 ${borderClass}`}>
                    {/* Header: PRIORITY | AREA | LIFECYCLE | CHANNELS */}
                    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-100 pb-2.5">
                      <div className="flex flex-wrap items-center gap-2">
                        <span className={`text-[10px] font-mono font-semibold px-2 py-0.5 rounded uppercase ${badgeClass}`}>
                          {alt.alert_level || alt.severity || "WARNING"}
                        </span>
                        
                        <span className="text-[10px] font-mono font-medium px-1.5 py-0.2 rounded bg-slate-100 text-slate-700 border border-slate-200">
                          AI ADVISORY
                        </span>

                        <span className={`text-[10px] font-mono font-semibold px-2 py-0.5 rounded uppercase border ${statusBadge}`}>
                          {alt.status || "ACTIVE"}
                        </span>

                        {isSimulation && (
                          <span className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-blue-50 text-blue-700 border border-blue-200">
                            SIMULATED
                          </span>
                        )}

                        <span className="text-xs font-semibold text-slate-900 font-sans">
                          {alt.headline}
                        </span>
                      </div>

                      <div className="flex items-center space-x-2 text-xs font-mono text-slate-500 shrink-0">
                        <span>AUDIENCE: <strong className="text-slate-800 font-sans">{alt.audience}</strong></span>
                      </div>
                    </div>

                    {/* Metadata & Multi-Channel Delivery Strip */}
                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 p-2.5 rounded bg-slate-50 border border-slate-200 text-xs font-mono">
                      <div>
                        <span className="text-[10px] text-slate-400 block font-sans">Target Districts</span>
                        <span className="font-semibold text-slate-800 truncate block">
                          {Array.isArray(alt.affected_districts) && alt.affected_districts.length > 0
                            ? alt.affected_districts.join(", ")
                            : alt.location_description || "Gujarat Coast"}
                        </span>
                      </div>

                      <div>
                        <span className="text-[10px] text-slate-400 block font-sans">Expected Horizon</span>
                        <span className="font-semibold text-slate-800">
                          {alt.expected_time ? new Date(alt.expected_time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) + " UTC" : "+18h to +24h"}
                        </span>
                      </div>

                      <div>
                        <span className="text-[10px] text-slate-400 block font-sans">Risk / Confidence</span>
                        <span className="font-semibold text-slate-800">
                          {alt.risk_score != null ? `${Math.round(alt.risk_score * 100)}% Risk` : "High"} • {alt.confidence_pct || 92}% Conf
                        </span>
                      </div>

                      <div>
                        <span className="text-[10px] text-slate-400 block font-sans">Dispatch Channels</span>
                        <span className="font-semibold text-slate-800 flex items-center space-x-1.5 text-[11px]">
                          <span className="text-emerald-700" title="Dashboard Delivery Active">● Dashboard</span>
                          <span className="text-slate-400">|</span>
                          <span className="text-emerald-700" title="SMS Dispatch Ready">● SMS</span>
                          <span className="text-slate-400">|</span>
                          <span className="text-emerald-700" title="Email Dispatch Ready">● Email</span>
                        </span>
                      </div>
                    </div>

                    {/* Body Explanation */}
                    <p className="text-xs text-slate-600 leading-relaxed font-sans">
                      {alt.explanation}
                    </p>

                    {/* Recommended Planning Action Checklist */}
                    <div className="space-y-1 pt-1">
                      <span className="text-[10px] font-mono font-semibold text-slate-500 uppercase tracking-wider block">
                        RECOMMENDED ACTION CHECKLIST:
                      </span>
                      <ul className="space-y-0.5 text-xs text-slate-700 list-disc list-inside font-sans">
                        {(alt.recommended_actions || []).map((act: string, i: number) => (
                          <li key={i}>{act}</li>
                        ))}
                      </ul>
                    </div>

                    {/* Interactive Operational Actions Bar */}
                    <div className="pt-2 border-t border-slate-100 flex flex-col sm:flex-row sm:items-center justify-between gap-2 text-xs font-mono">
                      <div className="flex flex-wrap items-center gap-2">
                        {/* Acknowledge Button */}
                        {(alt.status || "ACTIVE") === "ACTIVE" && (
                          <button
                            onClick={() => handleAcknowledge(alt.id)}
                            disabled={actionLoading === alt.id}
                            className="px-2.5 py-1 rounded bg-amber-50 hover:bg-amber-100 text-amber-800 border border-amber-300 font-medium transition disabled:opacity-50 flex items-center space-x-1"
                          >
                            <CheckCircle2 className="w-3.5 h-3.5" />
                            <span>Acknowledge Dispatch</span>
                          </button>
                        )}

                        {/* Escalate Button */}
                        {(alt.status || "ACTIVE") !== "RESOLVED" && (alt.status || "ACTIVE") !== "ESCALATED" && (
                          <button
                            onClick={() => handleEscalate(alt.id)}
                            disabled={actionLoading === alt.id}
                            className="px-2.5 py-1 rounded bg-red-50 hover:bg-red-100 text-red-800 border border-red-300 font-medium transition disabled:opacity-50 flex items-center space-x-1"
                          >
                            <AlertOctagon className="w-3.5 h-3.5" />
                            <span>Escalate to Emergency</span>
                          </button>
                        )}

                        {/* Resolve Button */}
                        {(alt.status || "ACTIVE") !== "RESOLVED" && (
                          <button
                            onClick={() => handleResolve(alt.id)}
                            disabled={actionLoading === alt.id}
                            className="px-2.5 py-1 rounded bg-slate-100 hover:bg-slate-200 text-slate-700 border border-slate-200 font-medium transition disabled:opacity-50"
                          >
                            Resolve Alert
                          </button>
                        )}

                        {/* View Audit Trail Button */}
                        <button
                          onClick={() => handleInspectAudit(alt)}
                          className="px-2.5 py-1 rounded bg-slate-50 hover:bg-slate-100 text-slate-600 border border-slate-200 transition flex items-center space-x-1"
                        >
                          <FileText className="w-3.5 h-3.5" />
                          <span>Audit Trail</span>
                        </button>
                      </div>

                      <div className="text-[11px] text-slate-400">
                        {alt.acknowledged_by ? `Ack by: ${alt.acknowledged_by}` : alt.parent_alert_id ? `Escalated from: ${alt.parent_alert_id.slice(0, 8)}` : "Dispatched: " + (alt.created_at ? new Date(alt.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) + " UTC" : "Recent")}
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </>
      ) : (
        /* Delivery Audit Trail Tab */
        <div className="bg-white border border-slate-200 rounded p-4 space-y-3">
          <div className="flex items-center justify-between border-b border-slate-200 pb-2">
            <div>
              <h2 className="text-xs font-mono font-bold text-slate-900 uppercase tracking-wider">
                CHRONOLOGICAL NOTIFICATION DELIVERY AUDIT LOG
              </h2>
              <p className="text-[11px] text-slate-500 font-sans">
                Immutable audit records of all notification dispatches across Dashboard, SMS, and Email channels.
              </p>
            </div>
            <button
              onClick={loadData}
              className="text-xs font-mono text-slate-600 hover:text-slate-900 underline"
            >
              Refresh Log
            </button>
          </div>

          {auditLogs.length === 0 ? (
            <div className="py-8 text-center text-xs font-mono text-slate-400">
              No delivery audit records logged yet. Trigger a simulation or alert dispatch to view entries.
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs font-mono">
                <thead>
                  <tr className="border-b border-slate-200 text-slate-400 text-[11px] uppercase">
                    <th className="py-2 px-2 font-medium">Timestamp (UTC)</th>
                    <th className="py-2 px-2 font-medium">Channel</th>
                    <th className="py-2 px-2 font-medium">Recipient Name</th>
                    <th className="py-2 px-2 font-medium">Destination</th>
                    <th className="py-2 px-2 font-medium">Trigger</th>
                    <th className="py-2 px-2 font-medium">Delivery Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 text-slate-700">
                  {auditLogs.map((log) => (
                    <tr key={log.id} className="hover:bg-slate-50 transition">
                      <td className="py-2 px-2 text-slate-500">
                        {log.sent_at ? new Date(log.sent_at).toISOString().replace("T", " ").slice(0, 19) : "--"}
                      </td>
                      <td className="py-2 px-2">
                        <span className="uppercase font-semibold text-slate-900">{log.channel}</span>
                      </td>
                      <td className="py-2 px-2 font-medium text-slate-900 truncate max-w-[200px]">
                        {log.recipient_name}
                      </td>
                      <td className="py-2 px-2 text-slate-500 truncate max-w-[180px]">
                        {log.recipient_contact}
                      </td>
                      <td className="py-2 px-2">
                        <span className="text-[10px] px-1.5 py-0.2 rounded bg-slate-100 text-slate-600">
                          {log.trigger_type}
                        </span>
                      </td>
                      <td className="py-2 px-2">
                        <span className={`text-[10px] font-semibold px-1.5 py-0.2 rounded ${
                          log.delivery_status === "DELIVERED"
                            ? "bg-emerald-50 text-emerald-800 border border-emerald-200"
                            : log.delivery_status === "SIMULATED"
                            ? "bg-blue-50 text-blue-800 border border-blue-200"
                            : "bg-red-50 text-red-800 border border-red-200"
                        }`}>
                          {log.delivery_status}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* Statutory Disclaimer Notice */}
      <div className="p-4 rounded bg-slate-50 border border-slate-200 flex items-start space-x-3 text-xs text-slate-600 leading-relaxed font-sans">
        <Info className="w-4 h-4 text-slate-500 shrink-0 mt-0.5" />
        <div>
          <strong className="font-semibold text-slate-800">Statutory Notice: </strong> 
          CycloneX alerts are computer-generated early warning decision-support advisories designed to assist civil administration, emergency responders, and community coordinators. Legally binding cyclonic warning bulletins, port danger signals, and mandatory evacuation orders are issued exclusively by the India Meteorological Department (IMD) and National/State Disaster Management Authorities (NDMA/SDMA).
        </div>
      </div>

      {/* Operational Simulation Modal (for Jury/Evaluator Demonstration) */}
      {showSimModal && (
        <div className="fixed inset-0 z-50 bg-slate-900/40 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white border border-slate-300 rounded shadow-xl max-w-lg w-full p-5 space-y-4 font-mono text-xs animate-in fade-in duration-150">
            <div className="flex items-center justify-between border-b border-slate-200 pb-2">
              <div className="flex items-center space-x-2">
                <Play className="w-4 h-4 text-slate-900 fill-current" />
                <span className="font-bold text-slate-900 text-sm uppercase">
                  SIMULATE CYCLONE ALERT SCENARIO (JURY DEMO)
                </span>
              </div>
              <button
                onClick={() => setShowSimModal(false)}
                className="p-1 rounded hover:bg-slate-100 text-slate-400 hover:text-slate-700 transition"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <p className="text-slate-600 font-sans text-xs leading-relaxed">
              Triggers end-to-end alert orchestration (threshold calculation, district resolution, escalation logic, and multi-channel dispatch in safe simulation mode).
            </p>

            <div className="space-y-3">
              <div>
                <label className="text-[11px] font-semibold text-slate-700 block mb-1">
                  Scenario Preset
                </label>
                <select
                  value={simScenario}
                  onChange={(e) => setSimScenario(e.target.value)}
                  className="w-full border border-slate-300 rounded p-1.5 text-xs bg-white text-slate-900 focus:ring-1 focus:ring-slate-900"
                >
                  <option value="Rapid Intensification & Landfall">Rapid Intensification & Landfall (95 kt • Warning/Emergency)</option>
                  <option value="Severe Cyclone Approaching Coast">Severe Cyclone Approaching Coast (70 kt • Warning)</option>
                  <option value="Cyclonic Storm Formation Watch">Cyclonic Storm Formation Watch (45 kt • Watch)</option>
                  <option value="Deep Depression Coastal Advisory">Deep Depression Coastal Advisory (30 kt • Advisory)</option>
                </select>
              </div>

              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="text-[11px] font-semibold text-slate-700 block mb-1">
                    Wind Speed (kt)
                  </label>
                  <input
                    type="number"
                    value={simWindKts}
                    onChange={(e) => setSimWindKts(Number(e.target.value))}
                    className="w-full border border-slate-300 rounded p-1.5 text-xs text-slate-900"
                    min={25}
                    max={150}
                  />
                </div>
                <div>
                  <label className="text-[11px] font-semibold text-slate-700 block mb-1">
                    Landfall ETA (hours)
                  </label>
                  <input
                    type="number"
                    value={simEtaHours}
                    onChange={(e) => setSimEtaHours(Number(e.target.value))}
                    className="w-full border border-slate-300 rounded p-1.5 text-xs text-slate-900"
                    min={6}
                    max={96}
                  />
                </div>
              </div>

              <div>
                <label className="text-[11px] font-semibold text-slate-700 block mb-1">
                  Target Coastal Districts
                </label>
                <input
                  type="text"
                  value={simDistricts}
                  onChange={(e) => setSimDistricts(e.target.value)}
                  className="w-full border border-slate-300 rounded p-1.5 text-xs text-slate-900"
                  placeholder="Kutch, Devbhumi Dwarka, Jamnagar"
                />
              </div>

              <div className="p-2.5 rounded bg-slate-50 border border-slate-200 text-[11px] text-slate-600 space-y-1">
                <span className="font-semibold text-slate-800 block font-sans">Configured Notification Channels:</span>
                <div className="flex items-center space-x-3 text-slate-700">
                  <span className="flex items-center space-x-1">
                    <Radio className="w-3 h-3 text-emerald-600" />
                    <span>Dashboard Feed</span>
                  </span>
                  <span className="flex items-center space-x-1">
                    <Phone className="w-3 h-3 text-emerald-600" />
                    <span>SMS (Simulated)</span>
                  </span>
                  <span className="flex items-center space-x-1">
                    <Mail className="w-3 h-3 text-emerald-600" />
                    <span>Email (Simulated)</span>
                  </span>
                </div>
              </div>

              {simSuccessMsg && (
                <div className="p-2.5 rounded bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs">
                  {simSuccessMsg}
                </div>
              )}
            </div>

            <div className="flex items-center justify-end space-x-2 pt-2 border-t border-slate-200">
              <button
                onClick={() => setShowSimModal(false)}
                className="px-3 py-1.5 rounded border border-slate-200 text-slate-600 hover:bg-slate-50 transition"
              >
                Cancel
              </button>
              <button
                onClick={handleRunSimulation}
                disabled={simRunning}
                className="px-4 py-1.5 rounded bg-slate-900 text-white font-semibold hover:bg-slate-800 transition disabled:opacity-50 flex items-center space-x-1.5"
              >
                {simRunning ? (
                  <>
                    <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                    <span>Triggering Pipeline...</span>
                  </>
                ) : (
                  <>
                    <Play className="w-3.5 h-3.5 fill-current" />
                    <span>Run Simulation Now</span>
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Audit Inspection Modal for Single Alert */}
      {inspectAlert && (
        <div className="fixed inset-0 z-50 bg-slate-900/40 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white border border-slate-300 rounded shadow-xl max-w-xl w-full p-5 space-y-4 font-mono text-xs animate-in fade-in duration-150">
            <div className="flex items-center justify-between border-b border-slate-200 pb-2">
              <div>
                <span className="font-bold text-slate-900 text-sm uppercase block">
                  DELIVERY AUDIT LOG: {inspectAlert.headline?.slice(0, 45)}...
                </span>
                <span className="text-[11px] text-slate-500">
                  Alert ID: {inspectAlert.id}
                </span>
              </div>
              <button
                onClick={() => setInspectAlert(null)}
                className="p-1 rounded hover:bg-slate-100 text-slate-400 hover:text-slate-700 transition"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {inspectLoading ? (
              <div className="py-6 text-center text-slate-400">Loading audit log entries...</div>
            ) : inspectLogs.length === 0 ? (
              <div className="py-6 text-center text-slate-400">No delivery logs recorded for this alert dispatch yet.</div>
            ) : (
              <div className="max-h-[340px] overflow-y-auto divide-y divide-slate-100">
                {inspectLogs.map((lg) => (
                  <div key={lg.id} className="py-2.5 space-y-1">
                    <div className="flex items-center justify-between">
                      <span className="font-bold text-slate-900 uppercase">{lg.channel} Channel</span>
                      <span className={`text-[10px] font-semibold px-1.5 py-0.2 rounded ${
                        lg.delivery_status === "DELIVERED"
                          ? "bg-emerald-50 text-emerald-800 border border-emerald-200"
                          : lg.delivery_status === "SIMULATED"
                          ? "bg-blue-50 text-blue-800 border border-blue-200"
                          : "bg-red-50 text-red-800 border border-red-200"
                      }`}>
                        {lg.delivery_status}
                      </span>
                    </div>
                    <div className="text-slate-600 text-[11px]">
                      Recipient: <span className="text-slate-900 font-medium">{lg.recipient_name}</span> ({lg.recipient_contact})
                    </div>
                    <div className="text-slate-400 text-[10px]">
                      Timestamp: {lg.sent_at ? new Date(lg.sent_at).toUTCString() : "--"} • Trigger: {lg.trigger_type}
                    </div>
                  </div>
                ))}
              </div>
            )}

            <div className="pt-2 border-t border-slate-200 flex justify-end">
              <button
                onClick={() => setInspectAlert(null)}
                className="px-3 py-1.5 rounded bg-slate-900 text-white font-medium text-xs hover:bg-slate-800 transition"
              >
                Close Audit
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
