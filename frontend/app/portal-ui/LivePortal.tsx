"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { useLive } from "./LiveProvider";
import type { LivePage, LiveRecord } from "@/lib/live/client";
import s from "./live.module.css";

type ResourceKey = "institutions" | "applications" | "documents" | "evc" | "compliance" | "notifications" | "report-runs";

interface ResourceConfig {
  apiPath: string;
  title: string;
  singular: string;
  fields: { key: string; label: string }[];
}

const resourceConfigs: Record<ResourceKey, ResourceConfig> = {
  institutions: {
    apiPath: "/institutions",
    title: "Institutions",
    singular: "Institution",
    fields: [
      { key: "official_name", label: "Official Name" },
      { key: "institution_code", label: "Code" },
      { key: "institution_type", label: "Type" },
      { key: "status", label: "Status" },
    ],
  },
  applications: {
    apiPath: "/applications",
    title: "Applications",
    singular: "Application",
    fields: [
      { key: "application_number", label: "Application #" },
      { key: "academic_year", label: "Academic Year" },
      { key: "status", label: "Status" },
      { key: "submitted_at", label: "Submitted" },
    ],
  },
  documents: {
    apiPath: "/documents",
    title: "Document Registry",
    singular: "Document",
    fields: [
      { key: "id", label: "Document ID" },
      { key: "document_scope", label: "Scope" },
      { key: "status", label: "Status" },
      { key: "created_at", label: "Registered At" },
    ],
  },
  evc: {
    apiPath: "/evc-visits",
    title: "Expert Visits (EVC)",
    singular: "EVC Visit",
    fields: [
      { key: "id", label: "Visit ID" },
      { key: "visit_type", label: "Type" },
      { key: "status", label: "Status" },
      { key: "scheduled_start_at", label: "Scheduled Start" },
    ],
  },
  compliance: {
    apiPath: "/compliance-conditions",
    title: "Compliance Conditions",
    singular: "Condition",
    fields: [
      { key: "id", label: "Condition ID" },
      { key: "title", label: "Title" },
      { key: "condition_type", label: "Type" },
      { key: "status", label: "Status" },
      { key: "due_date", label: "Due Date" },
    ],
  },
  notifications: {
    apiPath: "/notifications",
    title: "Notifications & Outbox",
    singular: "Notification",
    fields: [
      { key: "id", label: "Notification ID" },
      { key: "notification_type", label: "Type" },
      { key: "channel", label: "Channel" },
      { key: "status", label: "Status" },
      { key: "recipient_email", label: "Recipient Email" },
    ],
  },
  "report-runs": {
    apiPath: "/report-runs",
    title: "Statutory Report Runs",
    singular: "Report Run",
    fields: [
      { key: "id", label: "Run ID" },
      { key: "report_code", label: "Report Code" },
      { key: "format", label: "Format" },
      { key: "status", label: "Status" },
      { key: "row_count", label: "Rows" },
      { key: "created_at", label: "Generated" },
    ],
  },
};

interface DashboardOverview {
  freshness?: string;
  summary?: {
    total_applications?: number;
    total_evc_visits?: number;
    total_compliance_conditions?: number;
  };
  applications?: {
    by_status?: Record<string, number>;
    sla?: {
      on_track?: number;
      breached?: number;
    };
  };
  evc?: {
    by_status?: Record<string, number>;
  };
  compliance?: {
    by_status?: Record<string, number>;
  };
  documents?: {
    by_verification_status?: Record<string, number>;
  };
  communications?: {
    sent?: number;
    failed?: number;
    queued?: number;
  };
  notifications?: {
    sent?: number;
    failed?: number;
    queued?: number;
  };
}

interface StatutoryReportDef {
  id: string;
  report_code: string;
  name: string;
  category: string;
  description: string;
  default_format: string;
}

interface StatutoryReportRun {
  id: string;
  report_code: string;
  status: string;
  format: string;
  row_count: number;
  created_at: string;
}

function matchResource(pathname: string): { resource: ResourceKey; id?: string } | null {
  const match = pathname.match(/^\/portal\/(institutions|applications|documents|evc|compliance|notifications|report-runs)(?:\/([^/]+))?\/?$/);
  if (!match) return null;
  return { resource: match[1] as ResourceKey, id: match[2] };
}

export default function LivePortal({ children }: { children: React.ReactNode }) {
  const { identity, loading, error: identityError, get, post, download, signOut } = useLive();
  const pathname = usePathname();
  const router = useRouter();
  const matched = matchResource(pathname);
  const resource = matched?.resource;
  const id = matched?.id;

  // Resource list/detail state
  const [page, setPage] = useState<LivePage<LiveRecord> | null>(null);
  const [detail, setDetail] = useState<LiveRecord | null>(null);
  const [cursor, setCursor] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState("");
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");

  // Live Dashboard Overview state
  const [overview, setOverview] = useState<DashboardOverview | null>(null);
  const [overviewLoading, setOverviewLoading] = useState(false);

  // Live Reports state
  const [reportDefs, setReportDefs] = useState<StatutoryReportDef[]>([]);
  const [reportRuns, setReportRuns] = useState<StatutoryReportRun[]>([]);
  const [runningReport, setRunningReport] = useState<string | null>(null);
  const [reportMessage, setReportMessage] = useState<string | null>(null);

  useEffect(() => {
    if (!loading && !identity) {
      router.replace(`/login?returnTo=${encodeURIComponent(pathname)}`);
    }
  }, [identity, loading, pathname, router]);

  // Load Dashboard Overview when on /portal
  useEffect(() => {
    if (!identity || pathname !== "/portal") return;
    let active = true;
    setOverviewLoading(true);
    get<DashboardOverview>("/dashboards/overview")
      .then(res => {
        if (active) {
          setOverview(res);
          setOverviewLoading(false);
        }
      })
      .catch(err => {
        if (active) {
          setError(err instanceof Error ? err.message : "Unable to load dashboard metrics.");
          setOverviewLoading(false);
        }
      });
    return () => { active = false; };
  }, [identity, pathname, get]);

  // Load Reports Catalog & Runs when on /portal/reports
  useEffect(() => {
    if (!identity || pathname !== "/portal/reports") return;
    let active = true;
    Promise.all([
      get<{ data: StatutoryReportDef[] }>("/reports"),
      get<{ data: StatutoryReportRun[] }>("/report-runs"),
    ])
      .then(([catalogRes, runsRes]) => {
        if (active) {
          setReportDefs(catalogRes.data);
          setReportRuns(runsRes.data);
        }
      })
      .catch(err => {
        if (active) setError(err instanceof Error ? err.message : "Unable to load statutory reports.");
      });
    return () => { active = false; };
  }, [identity, pathname, get]);

  // Load generic resource list / detail
  useEffect(() => {
    if (!identity || !resource) return;
    let active = true;
    const cfg = resourceConfigs[resource];
    const query = new URLSearchParams({ limit: "25" });
    if (cursor && !id) query.set("cursor", cursor);
    if (statusFilter.trim() && !id) query.set("status", statusFilter.trim());
    const url = id ? `${cfg.apiPath}/${encodeURIComponent(id)}` : `${cfg.apiPath}?${query}`;

    get<LivePage<LiveRecord> | LiveRecord>(url)
      .then(result => {
        if (!active) return;
        if (id) {
          setDetail(result as LiveRecord);
          setPage(null);
        } else {
          setPage(result as LivePage<LiveRecord>);
          setDetail(null);
        }
        setError("");
        setPending(false);
      })
      .catch(cause => {
        if (active) {
          setError(cause instanceof Error ? cause.message : "Unable to load records.");
          setPending(false);
        }
      });
    return () => { active = false; };
  }, [identity, resource, id, cursor, statusFilter, get]);

  if (loading) return <main className={s.center} role="status">Checking your session…</main>;
  if (!identity) return <main className={s.center} role="status">{identityError || "Redirecting to sign-in…"}</main>;

  async function leave() {
    await signOut();
    router.replace("/login");
  }

  async function handleRunReport(code: string, format: "csv" | "json") {
    setRunningReport(code);
    setReportMessage(null);
    try {
      const res = await post<{ run_id: string; row_count: number }>(`/reports/${code}/runs`, {
        filters: {},
        format,
      });
      setReportMessage(`Report ${code} completed successfully: ${res.row_count} rows generated (Run ID: ${res.run_id})`);
      // Refresh runs
      const updatedRuns = await get<{ data: StatutoryReportRun[] }>("/report-runs");
      setReportRuns(updatedRuns.data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to execute report.");
    } finally {
      setRunningReport(null);
    }
  }

  async function handleDownloadReport(runId: string) {
    try {
      const { blob, filename } = await download(`/report-runs/${runId}/download`);
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Download failed.");
    }
  }

  const title = pathname === "/portal"
    ? "Live Statutory Dashboard"
    : pathname === "/portal/reports"
    ? "Statutory Reports & Downloads"
    : matched
    ? resourceConfigs[matched.resource]?.title ?? "Workspace"
    : pathname === "/portal/account"
    ? "Account & Assignments"
    : "Live Workspace";

  return (
    <div className={s.page}>
      <header className={s.header}>
        <Link href="/" className={s.brand}>AICTE Approval & Compliance</Link>
        <nav aria-label="Live workspace">
          <Link href="/portal">Overview</Link>
          <Link href="/portal/institutions">Institutions</Link>
          <Link href="/portal/applications">Applications</Link>
          <Link href="/portal/documents">Documents</Link>
          <Link href="/portal/evc">EVC</Link>
          <Link href="/portal/compliance">Compliance</Link>
          <Link href="/portal/notifications">Notifications</Link>
          <Link href="/portal/reports">Reports</Link>
          <Link href="/portal/account">Account</Link>
        </nav>
        <button type="button" onClick={leave}>Sign out</button>
      </header>

      <main className={s.main} id="main-content">
        <p className={s.kicker}>
          <span className={s.livePulse} />
          LIVE DATA · AUTHORISED SCOPE · POSTGRESQL 17
        </p>
        <h1>{title}</h1>
        <p>
          Signed in as <strong>{identity.user.display_name}</strong> ({identity.user.email}).
          Records are fetched live from the FastAPI backend and filtered by row-level security (RLS).
        </p>

        {error && <p role="alert" className={s.alert}>{error}</p>}
        {reportMessage && <p role="status" className={s.alert} style={{ background: "#ecfdf5", color: "#065f46", borderColor: "#10b981" }}>{reportMessage}</p>}

        {/* OVERVIEW DASHBOARD */}
        {pathname === "/portal" && (
          <>
            {overviewLoading && <p role="status">Loading live metrics from database…</p>}
            {overview && (() => {
              const summary = overview.summary ?? { total_applications: 0, total_evc_visits: 0, total_compliance_conditions: 0 };
              const appsByStatus = overview.applications?.by_status ?? {};
              const evcByStatus = overview.evc?.by_status ?? {};
              const compByStatus = overview.compliance?.by_status ?? {};
              const sla = overview.applications?.sla ?? { on_track: 0, breached: 0 };
              const notifs = overview.notifications ?? overview.communications ?? { sent: 0, failed: 0, queued: 0 };

              return (
                <>
                  <section className={s.statGrid}>
                    <div className={s.statCard}>
                      <span className={s.statLabel}>Applications</span>
                      <span className={s.statNumber}>{summary.total_applications ?? 0}</span>
                      <div className={s.statChips}>
                        {Object.entries(appsByStatus).map(([status, cnt]) => (
                          <span key={status} className={`${s.chip} ${status === "approved" ? s.chipSuccess : status === "rejected" ? s.chipDanger : s.chipWarning}`}>
                            {status}: {cnt}
                          </span>
                        ))}
                      </div>
                    </div>

                    <div className={s.statCard}>
                      <span className={s.statLabel}>EVC Committee Visits</span>
                      <span className={s.statNumber}>{summary.total_evc_visits ?? 0}</span>
                      <div className={s.statChips}>
                        {Object.entries(evcByStatus).map(([status, cnt]) => (
                          <span key={status} className={`${s.chip} ${status === "completed" ? s.chipSuccess : s.chipInfo}`}>
                            {status}: {cnt}
                          </span>
                        ))}
                      </div>
                    </div>

                    <div className={s.statCard}>
                      <span className={s.statLabel}>Compliance Conditions</span>
                      <span className={s.statNumber}>{summary.total_compliance_conditions ?? 0}</span>
                      <div className={s.statChips}>
                        {Object.entries(compByStatus).map(([status, cnt]) => (
                          <span key={status} className={`${s.chip} ${status === "closed" ? s.chipSuccess : status === "overdue" ? s.chipDanger : s.chipWarning}`}>
                            {status}: {cnt}
                          </span>
                        ))}
                      </div>
                    </div>

                    <div className={s.statCard}>
                      <span className={s.statLabel}>SLA Compliance</span>
                      <span className={s.statNumber}>{sla.on_track ?? 0}</span>
                      <div className={s.statChips}>
                        <span className={`${s.chip} ${s.chipSuccess}`}>On Track: {sla.on_track ?? 0}</span>
                        <span className={`${s.chip} ${(sla.breached ?? 0) > 0 ? s.chipDanger : s.chipSuccess}`}>
                          Breached: {sla.breached ?? 0}
                        </span>
                      </div>
                    </div>

                    <div className={s.statCard}>
                      <span className={s.statLabel}>Notification Outbox</span>
                      <span className={s.statNumber}>{notifs.sent ?? 0}</span>
                      <div className={s.statChips}>
                        <span className={`${s.chip} ${s.chipSuccess}`}>Sent: {notifs.sent ?? 0}</span>
                        <span className={`${s.chip} ${s.chipInfo}`}>Queued: {notifs.queued ?? 0}</span>
                        <span className={`${s.chip} ${(notifs.failed ?? 0) > 0 ? s.chipDanger : s.chipSuccess}`}>Failed: {notifs.failed ?? 0}</span>
                      </div>
                    </div>
                  </section>

                  <section className={s.grid}>
                    <Link className={s.card} href="/portal/institutions">
                      <h2>Institutions</h2>
                      <p>Review authorized institutional profiles, campuses, and accreditation data.</p>
                    </Link>
                    <Link className={s.card} href="/portal/applications">
                      <h2>Applications</h2>
                      <p>Track multi-stage approval intake, scrutiny, deficiencies, and statutory decisions.</p>
                    </Link>
                    <Link className={s.card} href="/portal/documents">
                      <h2>Document Vault & OCR</h2>
                      <p>Inspect encrypted files, immutable versions, and automated advisory extraction checks.</p>
                    </Link>
                    <Link className={s.card} href="/portal/evc">
                      <h2>EVC Committee & Visits</h2>
                      <p>Expert availability, slot recommendations, scheduling, and meeting records.</p>
                    </Link>
                    <Link className={s.card} href="/portal/compliance">
                      <h2>Compliance & Evidence</h2>
                      <p>Undertakings, evidence submissions, reason-backed officer verification, and closures.</p>
                    </Link>
                    <Link className={s.card} href="/portal/reports">
                      <h2>Statutory Reports & Exports</h2>
                      <p>Generate and download all 8 PRD statutory reports in CSV and JSON formats.</p>
                    </Link>
                  </section>
                  <p className={s.note}>Data freshness: {overview.freshness ?? "Live"}. All queries execute with RLS enabled.</p>
                </>
              );
            })()}
          </>
        )}

        {/* REPORTS CATALOG & RUNS */}
        {pathname === "/portal/reports" && (
          <>
            <section className={s.card}>
              <h2>Eight Official PRD Statutory Reports</h2>
              <p>Execute live analytical aggregations across the entire approval lifecycle.</p>
              <div className={s.grid}>
                {reportDefs.map(rep => (
                  <div key={rep.report_code} className={s.card}>
                    <h3>{rep.name}</h3>
                    <p style={{ fontSize: "0.85rem", color: "#475569" }}>{rep.description}</p>
                    <span className={`${s.chip} ${s.chipInfo}`} style={{ marginBottom: "0.8rem" }}>{rep.report_code}</span>
                    <div style={{ display: "flex", gap: "0.5rem", marginTop: "0.8rem" }}>
                      <button
                        type="button"
                        className={`${s.actionBtn} ${s.actionPrimary}`}
                        disabled={runningReport === rep.report_code}
                        onClick={() => handleRunReport(rep.report_code, "csv")}
                      >
                        {runningReport === rep.report_code ? "Running…" : "Run (CSV)"}
                      </button>
                      <button
                        type="button"
                        className={s.actionBtn}
                        disabled={runningReport === rep.report_code}
                        onClick={() => handleRunReport(rep.report_code, "json")}
                      >
                        Run (JSON)
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </section>

            <section className={s.card} style={{ marginTop: "2rem" }}>
              <h2>Recent Statutory Report Runs</h2>
              {reportRuns.length === 0 ? (
                <p>No report runs recorded yet. Generate one above.</p>
              ) : (
                <div className={s.tableWrap}>
                  <table>
                    <thead>
                      <tr>
                        <th>Report Code</th>
                        <th>Format</th>
                        <th>Status</th>
                        <th>Rows</th>
                        <th>Generated</th>
                        <th>Action</th>
                      </tr>
                    </thead>
                    <tbody>
                      {reportRuns.map(run => (
                        <tr key={run.id}>
                          <td><strong>{run.report_code}</strong></td>
                          <td>{run.format.toUpperCase()}</td>
                          <td>
                            <span className={`${s.chip} ${run.status === "completed" ? s.chipSuccess : s.chipWarning}`}>
                              {run.status}
                            </span>
                          </td>
                          <td>{run.row_count}</td>
                          <td>{run.created_at ? new Date(run.created_at).toLocaleString() : "—"}</td>
                          <td>
                            <button
                              type="button"
                              className={s.actionBtn}
                              onClick={() => handleDownloadReport(run.id)}
                            >
                              Download
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </section>
          </>
        )}

        {/* ACCOUNT AND PERMISSIONS */}
        {pathname === "/portal/account" && (
          <section className={s.card}>
            <h2>Identity & Scoped Assignments</h2>
            <p><strong>Email:</strong> {identity.user.email}</p>
            <p><strong>User ID:</strong> {identity.user.id}</p>
            <p><strong>Account Status:</strong> <span className={`${s.chip} ${s.chipSuccess}`}>{identity.user.status}</span></p>
            <h3>Active Role Assignments</h3>
            {identity.assignments.length ? (
              <div className={s.tableWrap}>
                <table>
                  <thead>
                    <tr>
                      <th>Role</th>
                      <th>Scope Type</th>
                      <th>Scope ID</th>
                      <th>Valid From</th>
                      <th>Valid Until</th>
                    </tr>
                  </thead>
                  <tbody>
                    {identity.assignments.map(a => (
                      <tr key={a.id}>
                        <td><strong>{a.role_code}</strong></td>
                        <td>{a.scope_type}</td>
                        <td>{a.scope_id || "Global"}</td>
                        <td>{a.valid_from ? new Date(a.valid_from).toLocaleDateString() : "—"}</td>
                        <td>{a.valid_until ? new Date(a.valid_until).toLocaleDateString() : "Indefinite"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <p>No active assignments.</p>
            )}
          </section>
        )}

        {/* GENERIC RESOURCE LIST / DETAIL */}
        {matched && pathname !== "/portal/reports" && (
          <section className={s.card}>
            {matched.id ? (
              <>
                <Link href={`/portal/${matched.resource}`}>← Back to {resourceConfigs[matched.resource]?.title}</Link>
                {detail ? (
                  <dl className={s.details}>
                    {Object.entries(detail).map(([key, value]) => (
                      <div key={key}>
                        <dt>{key.replaceAll("_", " ")}</dt>
                        <dd>{value === null || value === undefined ? "—" : String(value)}</dd>
                      </div>
                    ))}
                  </dl>
                ) : (
                  <p role="status">Loading record details…</p>
                )}
              </>
            ) : (
              <>
                <div className={s.filters}>
                  <label>
                    Filter Status
                    <input
                      value={statusFilter}
                      onChange={e => {
                        setStatusFilter(e.target.value);
                        setCursor(null);
                        setPage(null);
                      }}
                      placeholder="Optional status filter"
                    />
                  </label>
                  <button
                    type="button"
                    onClick={() => {
                      setCursor(null);
                      setStatusFilter("");
                      setPage(null);
                    }}
                  >
                    Clear Filter
                  </button>
                </div>

                {!page && !error && <p role="status">Loading records…</p>}
                {page && (
                  <>
                    <div className={s.tableWrap}>
                      <table>
                        <thead>
                          <tr>
                            {resourceConfigs[matched.resource].fields.map(f => (
                              <th key={f.key} scope="col">{f.label}</th>
                            ))}
                            <th scope="col">Action</th>
                          </tr>
                        </thead>
                        <tbody>
                          {page.data.map(row => (
                            <tr key={row.id}>
                              {resourceConfigs[matched.resource].fields.map(f => (
                                <td key={f.key}>
                                  {row[f.key] === null || row[f.key] === undefined ? "—" : String(row[f.key])}
                                </td>
                              ))}
                              <td>
                                <Link href={`/portal/${matched.resource}/${row.id}`} className={s.actionBtn}>
                                  View
                                </Link>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                    {page.data.length === 0 && (
                      <p style={{ marginTop: "1rem" }}>No records found in this scope.</p>
                    )}
                    <div className={s.pager}>
                      <button
                        type="button"
                        disabled={!cursor || pending}
                        onClick={() => {
                          setCursor(null);
                          setPage(null);
                        }}
                      >
                        First Page
                      </button>
                      <button
                        type="button"
                        disabled={!page.page.next_cursor || pending}
                        onClick={() => {
                          setPending(true);
                          setCursor(page.page.next_cursor);
                          setPage(null);
                        }}
                      >
                        Next Page
                      </button>
                    </div>
                  </>
                )}
              </>
            )}
          </section>
        )}
      </main>
      <div hidden inert aria-hidden="true">{children}</div>
    </div>
  );
}
