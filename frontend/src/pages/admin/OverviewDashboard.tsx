import React, { useEffect, useState } from "react";
import {
  Briefcase,
  Users,
  Clock,
  Zap,
  UserCheck,
  RefreshCw,
  TrendingUp,
  PieChart,
  CheckCircle2,
  AlertCircle,
} from "lucide-react";

interface SkillCoverageItem {
  skill_name: string;
  demand: number;
  supply: number;
  coverage_pct: number;
}

interface AuditLog {
  id: string | number;
  action: string;
  target: string;
  changed_by: string;
  timestamp: string;
}

interface DashboardData {
  kpis: {
    active_projects: number;
    total_projects: number;
    utilization_rate: number;
    allocated_hours: number;
    capacity_hours: number;
    avg_ai_match_score: number;
    total_employees: number;
    total_interns: number;
    pending_intern_reviews: number;
  };
  allocations_trend: { categories: string[]; series: Array<{ data: number[] }> };
  entity_allocation_breakdown: { labels: string[]; series: number[] };
  skill_coverage: SkillCoverageItem[];
  recent_logs: AuditLog[]; 
}

export default function DashboardOverview() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchDashboardData = async () => {
    setLoading(true);
    try {
      const response = await fetch("/api/dashboard/overview");
      if (!response.ok) throw new Error("Failed to fetch dashboard data");
      const result = await response.json();
      setData(result);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to fetch dashboard data");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDashboardData();
  }, []);

  if (loading) {
    return (
      <div style={styles.centerContainer}>
        <RefreshCw size={32} style={{ animation: "spin 1s linear infinite" }} />
        <p style={{ marginTop: 12, fontSize: 16, color: "var(--text-muted, #94a3b8)" }}>
          Loading Dashboard Metrics...
        </p>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div style={styles.centerContainer}>
        <AlertCircle size={40} color="var(--color-danger, #ef4444)" />
        <p style={{ marginTop: 12, color: "var(--color-danger, #ef4444)", fontWeight: 600 }}>
          {error || "Error loading metrics"}
        </p>
        <button onClick={fetchDashboardData} style={styles.retryButton}>
          Retry
        </button>
      </div>
    );
  }

  const { kpis, allocations_trend, entity_allocation_breakdown, skill_coverage, recent_logs } = data;

  const maxTrendValue = Math.max(...allocations_trend.series[0].data, ...allocations_trend.series[1].data, 10);
  const totalEntityHours = entity_allocation_breakdown.series.reduce((a, b) => a + b, 0) || 1;

  return (
    <div style={styles.dashboardLayout}>
      {/* HEADER */}
      <div style={styles.headerRow}>
        <div>
          <h1 style={styles.title}>Resource & Allocation Overview</h1>
          <p style={styles.subtitle}>Real-time telemetry across projects, candidates, AI engine, and engagements</p>
        </div>
        <button onClick={fetchDashboardData} style={styles.refreshBtn}>
          <RefreshCw size={16} /> Sync Live Data
        </button>
      </div>

      {/* KPI CARDS */}
      <div style={styles.kpiGrid}>
        <MetricCard
          title="Active Projects"
          value={`${kpis.active_projects} / ${kpis.total_projects}`}
          subtext="Total Tracked Projects"
          icon={<Briefcase color="#3b82f6" />}
          badgeColor="rgba(59, 130, 246, 0.15)"
        />
        <MetricCard
          title="Resource Utilization"
          value={`${kpis.utilization_rate}%`}
          subtext={`${kpis.allocated_hours} hrs / ${kpis.capacity_hours} hrs capacity`}
          icon={<Clock color="#10b981" />}
          badgeColor="rgba(16, 185, 129, 0.15)"
        />
        <MetricCard
          title="AI Match Quality"
          value={`${kpis.avg_ai_match_score}%`}
          subtext="Avg Suitability Rating"
          icon={<Zap color="#8b5cf6" />}
          badgeColor="rgba(139, 92, 246, 0.15)"
        />
        <MetricCard
          title="Talent Pool"
          value={`${kpis.total_employees} Emps | ${kpis.total_interns} Interns`}
          subtext={`${kpis.pending_intern_reviews} Pending Reviews`}
          icon={<Users color="#f59e0b" />}
          badgeColor="rgba(245, 158, 11, 0.15)"
        />
      </div>

      {/* CHARTS GRID */}
      <div style={styles.twoColumnGrid}>
        {/* ALLOCATION TRENDS */}
        <div style={styles.card}>
          <div style={styles.cardHeader}>
            <TrendingUp size={20} color="#3b82f6" />
            <h3 style={styles.cardTitle}>Monthly Allocation Hours Trend</h3>
          </div>
          <div style={styles.chartLegend}>
            <span style={{ display: "flex", alignItems: "center", gap: 6 }}>
              <span style={{ width: 12, height: 12, borderRadius: 2, backgroundColor: "#3b82f6" }}></span> Assigned Hours
            </span>
            <span style={{ display: "flex", alignItems: "center", gap: 6 }}>
              <span style={{ width: 12, height: 12, borderRadius: 2, backgroundColor: "var(--border-color, #64748b)" }}></span> Proposed Hours
            </span>
          </div>
          <div style={styles.barChartContainer}>
            {allocations_trend.categories.map((cat, idx) => {
              const assignedVal = allocations_trend.series[0].data[idx];
              const proposedVal = allocations_trend.series[1].data[idx];
              const assignedHeight = (assignedVal / maxTrendValue) * 140;
              const proposedHeight = (proposedVal / maxTrendValue) * 140;

              return (
                <div key={cat} style={styles.barGroup}>
                  <div style={styles.barTrack}>
                    <div
                      title={`Assigned: ${assignedVal} hrs`}
                      style={{ ...styles.bar, height: `${assignedHeight}px`, backgroundColor: "#3b82f6" }}
                    />
                    <div
                      title={`Proposed: ${proposedVal} hrs`}
                      style={{ ...styles.bar, height: `${proposedHeight}px`, backgroundColor: "var(--border-color, #64748b)" }}
                    />
                  </div>
                  <span style={styles.barLabel}>{cat}</span>
                </div>
              );
            })}
          </div>
        </div>

        {/* WORKLOAD BREAKDOWN */}
        <div style={styles.card}>
          <div style={styles.cardHeader}>
            <PieChart size={20} color="#10b981" />
            <h3 style={styles.cardTitle}>Assigned Hours by Work Type</h3>
          </div>
          <div style={{ marginTop: 16 }}>
            {entity_allocation_breakdown.series.map((hours, idx) => {
              const label = entity_allocation_breakdown.labels?.[idx] || `Work Type ${idx + 1}`;
              const pct = Math.round((hours / totalEntityHours) * 100);
              const colors = ["#3b82f6", "#10b981", "#f59e0b"];

              return (
                <div key={label} style={{ marginBottom: 16 }}>
                  <div style={styles.progressHeader}>
                    <span style={{ fontWeight: 600, color: "var(--text-main, currentColor)" }}>{label}</span>
                    <span style={{ color: "var(--text-muted, #64748b)" }}>{hours} hrs ({pct}%)</span>
                  </div>
                  <div style={styles.progressTrack}>
                    <div
                      style={{
                        height: "100%",
                        width: `${pct}%`,
                        backgroundColor: colors[idx % colors.length],
                        borderRadius: 4,
                        transition: "width 0.4s ease",
                      }}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* BOTTOM SECTION */}
      <div style={styles.twoColumnGrid}>
        {/* SKILL DEMAND VS SUPPLY */}
        <div style={styles.card}>
          <div style={styles.cardHeader}>
            <UserCheck size={20} color="#8b5cf6" />
            <h3 style={styles.cardTitle}>Top Demanded Skills & Supply Coverage</h3>
          </div>
          <div style={{ marginTop: 12 }}>
            {skill_coverage.length === 0 ? (
              <p style={{ color: "var(--text-muted, #94a3b8)", fontSize: 14 }}>No project skill requirements calculated yet.</p>
            ) : (
              skill_coverage.map((item) => (
                <div key={item.skill_name} style={{ marginBottom: 14 }}>
                  <div style={styles.progressHeader}>
                    <span style={{ fontWeight: 600, color: "var(--text-main, currentColor)" }}>{item.skill_name}</span>
                    <span style={{ fontSize: 13, color: "var(--text-muted, #64748b)" }}>
                      Demand: {item.demand} reqs | Supply: {item.supply} ({item.coverage_pct}%)
                    </span>
                  </div>
                  <div style={styles.progressTrack}>
                    <div
                      style={{
                        height: "100%",
                        width: `${item.coverage_pct}%`,
                        backgroundColor: item.coverage_pct >= 80 ? "#10b981" : item.coverage_pct >= 50 ? "#f59e0b" : "#ef4444",
                        borderRadius: 4,
                      }}
                    />
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        {/* AUDIT LOGS */}
        <div style={styles.card}>
          <div style={styles.cardHeader}>
            <CheckCircle2 size={20} color="#6366f1" />
            <h3 style={styles.cardTitle}>Recent Allocation Audit Trail</h3>
          </div>
          <div style={{ marginTop: 10 }}>
            {recent_logs.length === 0 ? (
              <p style={{ color: "var(--text-muted, #94a3b8)", fontSize: 14 }}>No recent logs recorded.</p>
            ) : (
              <div style={styles.logList}>
                {recent_logs.map((log) => (
                  <div key={log.id} style={styles.logItem}>
                    <div>
                      <div style={{ fontWeight: 600, fontSize: 14, color: "var(--text-main, currentColor)" }}>{log.action}</div>
                      <div style={{ fontSize: 12, color: "var(--text-muted, #64748b)" }}>
                        Target: {log.target} | By: {log.changed_by}
                      </div>
                    </div>
                    <span style={{ fontSize: 12, color: "var(--text-muted, #94a3b8)", whiteSpace: "nowrap" }}>{log.timestamp}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

function MetricCard({
  title,
  value,
  subtext,
  icon,
  badgeColor,
}: {
  title: string;
  value: React.ReactNode;
  subtext: React.ReactNode;
  icon: React.ReactNode;
  badgeColor: string;
}) {
  return (
    <div style={styles.kpiCard}>
      <div style={styles.kpiHeader}>
        <span style={styles.kpiTitle}>{title}</span>
        <div style={{ ...styles.iconBadge, backgroundColor: badgeColor }}>{icon}</div>
      </div>
      <div style={styles.kpiValue}>{value}</div>
      <div style={styles.kpiSubtext}>{subtext}</div>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  dashboardLayout: {
    padding: "24px",
    backgroundColor: "transparent",
    minHeight: "100vh",
    fontFamily: "inherit",
    color: "var(--text-main, currentColor)",
  },
  headerRow: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: "24px",
  },
  title: {
    fontSize: "24px",
    fontWeight: "700",
    color: "var(--text-main, currentColor)",
    margin: 0,
  },
  subtitle: {
    fontSize: "14px",
    color: "var(--text-muted, #64748b)",
    margin: "4px 0 0 0",
  },
  refreshBtn: {
    display: "flex",
    alignItems: "center",
    gap: "8px",
    padding: "8px 16px",
    backgroundColor: "var(--bg-card, rgba(255, 255, 255, 0.05))",
    border: "1px solid var(--border-color, rgba(255, 255, 255, 0.1))",
    borderRadius: "6px",
    fontWeight: "600",
    color: "var(--text-main, currentColor)",
    cursor: "pointer",
  },
  kpiGrid: {
    display: "grid",
    gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
    gap: "16px",
    marginBottom: "24px",
  },
  kpiCard: {
    backgroundColor: "var(--bg-card, rgba(255, 255, 255, 0.03))",
    borderRadius: "8px",
    padding: "16px",
    border: "1px solid var(--border-color, rgba(255, 255, 255, 0.1))",
  },
  kpiHeader: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
  },
  kpiTitle: {
    fontSize: "13px",
    fontWeight: "600",
    color: "var(--text-muted, #64748b)",
  },
  iconBadge: {
    padding: "8px",
    borderRadius: "8px",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
  },
  kpiValue: {
    fontSize: "20px",
    fontWeight: "700",
    color: "var(--text-main, currentColor)",
    marginTop: "12px",
  },
  kpiSubtext: {
    fontSize: "12px",
    color: "var(--text-muted, #64748b)",
    marginTop: "4px",
  },
  twoColumnGrid: {
    display: "grid",
    gridTemplateColumns: "repeat(auto-fit, minmax(360px, 1fr))",
    gap: "20px",
    marginBottom: "24px",
  },
  card: {
    backgroundColor: "var(--bg-card, rgba(255, 255, 255, 0.03))",
    borderRadius: "8px",
    padding: "20px",
    border: "1px solid var(--border-color, rgba(255, 255, 255, 0.1))",
  },
  cardHeader: {
    display: "flex",
    alignItems: "center",
    gap: "8px",
  },
  cardTitle: {
    fontSize: "16px",
    fontWeight: "600",
    color: "var(--text-main, currentColor)",
    margin: 0,
  },
  chartLegend: {
    display: "flex",
    gap: "16px",
    fontSize: "12px",
    color: "var(--text-muted, #64748b)",
    marginTop: "12px",
    marginBottom: "12px",
  },
  barChartContainer: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "flex-end",
    height: "170px",
    paddingTop: "20px",
  },
  barGroup: {
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    flex: 1,
  },
  barTrack: {
    display: "flex",
    alignItems: "flex-end",
    gap: "4px",
    height: "140px",
  },
  bar: {
    width: "12px",
    borderRadius: "4px 4px 0 0",
    transition: "height 0.3s ease",
  },
  barLabel: {
    fontSize: "12px",
    color: "var(--text-muted, #64748b)",
    marginTop: "8px",
  },
  progressHeader: {
    display: "flex",
    justifyContent: "space-between",
    fontSize: "13px",
    marginBottom: "6px",
  },
  progressTrack: {
    height: "8px",
    backgroundColor: "var(--bg-track, rgba(255, 255, 255, 0.1))",
    borderRadius: "4px",
    overflow: "hidden",
  },
  logList: {
    display: "flex",
    flexDirection: "column",
    gap: "10px",
  },
  logItem: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    padding: "8px 12px",
    backgroundColor: "var(--bg-item, rgba(255, 255, 255, 0.02))",
    borderRadius: "6px",
    borderLeft: "3px solid #6366f1",
  },
  centerContainer: {
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    justifyContent: "center",
    height: "60vh",
  },
  retryButton: {
    marginTop: "12px",
    padding: "8px 16px",
    backgroundColor: "#3b82f6",
    color: "#ffffff",
    border: "none",
    borderRadius: "6px",
    cursor: "pointer",
  },
};