import React, { useState, useEffect, useMemo } from 'react';
import Chart from 'react-apexcharts';
import { Card } from '../../components/common/Card';
import { Users, GitMerge, CheckCircle, AlertTriangle } from 'lucide-react';

interface AllocationsTrend {
  categories: string[];
  series: { name: string; data: number[] }[];
}

interface ProjectStatus {
  labels: string[];
  series: number[];
}

interface DashboardMetrics {
  totalProjects?: number;
  total_projects?: number;
  activeCandidates?: number;
  active_candidates?: number;
  allocationRate?: string;
  allocation_rate?: string;
  pendingApprovals?: number;
  pending_approvals?: number;
  allocationsTrend?: AllocationsTrend;
  allocations_trend?: AllocationsTrend;
  projectStatus?: ProjectStatus;
  project_status?: ProjectStatus;
}

export const OverviewDashboard: React.FC = () => {
  const [metricsData, setMetricsData] = useState<DashboardMetrics | null>(null);
  const [selectedMonth, setSelectedMonth] = useState<string | null>(null);
  const [isClient, setIsClient] = useState(false);

  useEffect(() => {
    setIsClient(true);
  }, []);

  useEffect(() => {
    const fetchDashboardData = async () => {
      try {
        const res = await fetch('/api/dashboard/overview');
        if (res.ok) {
          const data = await res.json();
          setMetricsData(data);
        } else {
          throw new Error('API request failed');
        }
      } catch {
        // Fallback default dataset if endpoint is unmapped or offline
        setMetricsData({
          totalProjects: 24,
          activeCandidates: 142,
          allocationRate: '89%',
          pendingApprovals: 3,
          allocationsTrend: {
            categories: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun'],
            series: [
              { name: 'Assigned', data: [12, 19, 15, 25, 22, 30] },
              { name: 'Proposed', data: [5, 8, 12, 6, 9, 4] },
            ],
          },
          projectStatus: {
            labels: ['In Progress', 'Open', 'Completed', 'Cancelled'],
            series: [12, 6, 4, 2],
          },
        });
      }
    };

    fetchDashboardData();
    const interval = setInterval(fetchDashboardData, 10000);
    return () => clearInterval(interval);
  }, []);

  // Safe extractors that work with both snake_case (FastAPI) and camelCase
  const trend = metricsData?.allocationsTrend || metricsData?.allocations_trend;
  const status = metricsData?.projectStatus || metricsData?.project_status;

  const categories = trend?.categories || [];
  const trendSeries = trend?.series || [];
  const statusLabels = status?.labels || [];
  const statusSeries = status?.series || [];

  const barChartOptions: ApexCharts.ApexOptions = useMemo(
    () => ({
      chart: {
        type: 'bar',
        stacked: true,
        background: 'transparent',
        toolbar: { show: false },
        events: {
          dataPointSelection: (event, chartContext, config) => {
            if (config && categories.length > config.dataPointIndex) {
              setSelectedMonth(categories[config.dataPointIndex]);
            }
          },
        },
      },
      theme: { mode: 'dark' },
      colors: ['#818cf8', '#64748b'],
      plotOptions: {
        bar: { borderRadius: 6, columnWidth: '40%' },
      },
      xaxis: {
        categories: categories,
        labels: { style: { colors: '#94a3b8' } },
        axisBorder: { color: '#334155' },
        axisTicks: { color: '#334155' },
      },
      yaxis: {
        labels: { style: { colors: '#94a3b8' } },
      },
      grid: { borderColor: '#1e293b' },
      legend: { labels: { colors: '#cbd5e1' }, position: 'top', horizontalAlign: 'right' },
      dataLabels: { enabled: false },
      tooltip: { theme: 'dark' },
    }),
    [categories]
  );

  const donutChartOptions: ApexCharts.ApexOptions = useMemo(
    () => ({
      chart: { background: 'transparent' },
      theme: { mode: 'dark' },
      labels: statusLabels,
      colors: ['#34d399', '#818cf8', '#fbbf24', '#f87171'],
      legend: { position: 'bottom', labels: { colors: '#cbd5e1' } },
      stroke: { colors: ['#020617'] },
      dataLabels: { enabled: true },
      tooltip: { theme: 'dark' },
    }),
    [statusLabels]
  );

  const metrics = [
    {
      label: 'Total Projects',
      value: metricsData?.totalProjects ?? metricsData?.total_projects ?? '24',
      icon: GitMerge,
      color: 'text-indigo-400',
    },
    {
      label: 'Active Candidates',
      value: metricsData?.activeCandidates ?? metricsData?.active_candidates ?? '142',
      icon: Users,
      color: 'text-emerald-400',
    },
    {
      label: 'Successful Allocations',
      value: metricsData?.allocationRate ?? metricsData?.allocation_rate ?? '89%',
      icon: CheckCircle,
      color: 'text-amber-400',
    },
    {
      label: 'Pending Approvals',
      value: metricsData?.pendingApprovals ?? metricsData?.pending_approvals ?? '3',
      icon: AlertTriangle,
      color: 'text-rose-400',
    },
  ];

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white">System Analytics & Overview</h1>
          <p className="text-slate-400 text-sm">High-level metrics across active projects, candidate availability, and match rates.</p>
        </div>

        {selectedMonth && (
          <button
            onClick={() => setSelectedMonth(null)}
            className="self-start sm:self-auto text-xs px-3 py-1.5 rounded-lg bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 hover:bg-indigo-500/20 transition-colors flex items-center gap-1.5"
          >
            Filtered Month: <span className="font-semibold">{selectedMonth}</span> ✕
          </button>
        )}
      </div>

      {/* Top Stat Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {metrics.map((m, i) => {
          const Icon = m.icon;
          return (
            <Card key={i}>
              <div className="flex items-center justify-between">
                <div>
                  <span className="text-xs text-slate-400">{m.label}</span>
                  <h3 className="text-2xl font-black text-white mt-1">{m.value}</h3>
                </div>
                <div className={`p-3 bg-slate-950 rounded-xl border border-slate-800 ${m.color}`}>
                  <Icon className="w-6 h-6" />
                </div>
              </div>
            </Card>
          );
        })}
      </div>

      {/* ApexCharts Visualizations */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Allocations Bar Chart */}
        <div className="lg:col-span-2">
          <Card>
            <div className="p-1">
              <div className="flex items-center justify-between mb-2">
                <div>
                  <h3 className="text-base font-semibold text-white">Allocation Trends</h3>
                  <p className="text-xs text-slate-400">Monthly breakdown of assigned vs proposed candidates</p>
                </div>
              </div>

              {isClient && trendSeries.length > 0 ? (
                <Chart
                  options={barChartOptions}
                  series={trendSeries}
                  type="bar"
                  height={320}
                />
              ) : (
                <div className="h-[320px] flex items-center justify-center text-slate-500 text-sm">Loading chart data...</div>
              )}
            </div>
          </Card>
        </div>

        {/* Project Status Donut Chart */}
        <div>
          <Card>
            <div className="p-1">
              <div className="mb-2">
                <h3 className="text-base font-semibold text-white">Project Breakdown</h3>
                <p className="text-xs text-slate-400">Distribution across active project statuses</p>
              </div>

              {isClient && statusSeries.length > 0 ? (
                <Chart
                  options={donutChartOptions}
                  series={statusSeries}
                  type="donut"
                  height={320}
                />
              ) : (
                <div className="h-[320px] flex items-center justify-center text-slate-500 text-sm">Loading chart data...</div>
              )}
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
};