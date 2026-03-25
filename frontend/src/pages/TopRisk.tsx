import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAnalyticsQuery, useCoverageQuery } from '../hooks/useAnalyticsQuery';
import TopRiskTable from '../components/TopRiskTable';
import { AlertTriangle, Loader2, AlertCircle, BarChart3, ArrowRight, DatabaseZap, Info } from 'lucide-react';

export default function TopRisk() {
  const navigate = useNavigate();
  const [viewMode, setViewMode] = useState<'ecosystem' | 'project'>('ecosystem');
  const [ecosystem, setEcosystem] = useState<'npm' | 'pypi'>('npm');
  const [limit, setLimit] = useState(500); // Fetch top 500 items to feed client pagination

  const { data, isLoading, error } = useAnalyticsQuery({
    ecosystem,
    limit,
  });

  const { data: coverage } = useCoverageQuery(ecosystem);

  return (
    <div className="h-full flex flex-col bg-slate-50 overflow-y-auto w-full">
      <div className="max-w-7xl mx-auto w-full px-6 py-8">
        
        {/* Tabs for switching views */}
        <div className="flex bg-slate-200/60 p-1.5 rounded-xl w-fit mb-8 border border-slate-200">
          <button 
            onClick={() => setViewMode('ecosystem')}
            className={`px-5 py-2 text-sm font-semibold rounded-lg transition-all ${viewMode === 'ecosystem' ? 'bg-white text-blue-700 shadow-sm border border-slate-200/50' : 'text-slate-600 hover:text-slate-900 hover:bg-slate-300/40'}`}
          >
            Ecosystem Risks
          </button>
          <button 
            onClick={() => setViewMode('project')}
            className={`px-5 py-2 text-sm font-semibold rounded-lg transition-all flex items-center ${viewMode === 'project' ? 'bg-white text-rose-600 shadow-sm border border-slate-200/50' : 'text-slate-600 hover:text-slate-900 hover:bg-slate-300/40'}`}
          >
            <BarChart3 className="w-4 h-4 mr-2" />
            Method Hotspots
          </button>
        </div>

        {viewMode === 'ecosystem' && (
          <>
            <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4 mb-8">
              <div className="flex-1">
                <div className="flex items-center gap-2 mb-2">
                  <AlertTriangle className="w-7 h-7 text-red-500" />
                  <h1 className="text-2xl font-bold text-gray-900 leading-none tracking-tight">Top Risk Dependencies</h1>
                </div>
                <p className="text-sm text-gray-500 max-w-2xl leading-relaxed">
                  Packages ranked by their ecosystem-wide bottleneck score. A high bottleneck score indicates 
                  a package is heavily depended upon (high fan-in) and acts as an exclusive bridge to other 
                  critical infrastructure in the dependency graph.
                </p>
              </div>

              <div className="flex items-center gap-3 shrink-0 bg-white p-1.5 rounded-lg border border-gray-200 shadow-sm">
                <div className="flex bg-slate-100 rounded-md p-1">
                  <button
                    onClick={() => setEcosystem('npm')}
                    className={`px-4 py-1.5 text-sm font-medium rounded ${
                      ecosystem === 'npm'
                        ? 'bg-white text-blue-700 shadow-sm'
                        : 'text-gray-500 hover:text-gray-700'
                    }`}
                  >
                    NPM
                  </button>
                  <button
                    onClick={() => setEcosystem('pypi')}
                    className={`px-4 py-1.5 text-sm font-medium rounded ${
                      ecosystem === 'pypi'
                        ? 'bg-white text-blue-700 shadow-sm'
                        : 'text-gray-500 hover:text-gray-700'
                    }`}
                  >
                    PyPI
                  </button>
                </div>
                
                <div className="h-6 w-px bg-gray-200 mx-1 border-r" />

                <select
                  value={limit}
                  onChange={(e) => setLimit(Number(e.target.value))}
                  className="bg-transparent text-sm font-medium text-gray-700 pl-2 pr-8 py-1.5 focus:outline-none cursor-pointer"
                >
                  <option value={100}>Fetch Top 100</option>
                  <option value={500}>Fetch Top 500</option>
                  <option value={1000}>Fetch Top 1000</option>
                </select>
              </div>
            </div>

            {/* Graph Coverage Banner */}
            {coverage && (
              <div className="mb-6 bg-white border border-slate-200 rounded-xl px-5 py-4 shadow-sm">
                <div className="flex flex-col sm:flex-row sm:items-center gap-4">
                  <div className="flex items-center gap-2.5 shrink-0">
                    <DatabaseZap className="w-5 h-5 text-indigo-500" />
                    <span className="text-sm font-semibold text-gray-800">Graph Coverage</span>
                    <span className="text-xs font-mono text-indigo-700 bg-indigo-50 px-2 py-0.5 rounded-full ring-1 ring-indigo-200">
                      {coverage.coveragePct < 0.01
                        ? `<0.01%`
                        : `${coverage.coveragePct.toFixed(2)}%`}
                    </span>
                  </div>

                  <div className="flex-1 flex flex-col gap-1.5">
                    <div className="h-2 w-full bg-slate-100 rounded-full overflow-hidden">
                      <div
                        className="h-full bg-indigo-500 rounded-full transition-all"
                        style={{ width: `${Math.max(0.4, Math.min(100, coverage.coveragePct))}%` }}
                      />
                    </div>
                    <div className="flex justify-between text-[11px] text-gray-400">
                      <span>{coverage.ingestedPackages.toLocaleString()} packages ingested</span>
                      <span>est. {(coverage.estimatedTotal / 1_000_000).toFixed(1)}M total in {coverage.ecosystem.toUpperCase()}</span>
                    </div>
                  </div>

                  <div className="flex items-start gap-1.5 text-[11px] text-amber-700 bg-amber-50 border border-amber-200 rounded-lg px-3 py-2 max-w-xs shrink-0">
                    <Info className="w-3.5 h-3.5 mt-0.5 shrink-0" />
                    <span>Fan-in accuracy improves as graph coverage increases. Percentile ranks are relative to ingested packages only.</span>
                  </div>
                </div>
              </div>
            )}

            {/* Content State Handling */}
            <div className="min-h-[400px]">
              {isLoading && (
                <div className="flex flex-col items-center justify-center h-64">
                  <Loader2 className="w-8 h-8 text-blue-600 animate-spin mb-4" />
                  <p className="text-gray-500 font-medium">Computing ecosystem risk variants...</p>
                </div>
              )}

              {error && (
                <div className="flex flex-col items-center justify-center h-64 bg-white rounded-xl shadow-sm border border-red-100">
                  <AlertCircle className="w-10 h-10 text-red-500 mb-4" />
                  <h3 className="text-lg font-bold text-gray-900 mb-1">Failed to load analytics</h3>
                  <p className="text-red-600 text-sm">{(error as any)?.response?.data?.detail || error.message}</p>
                </div>
              )}

              {data && !isLoading && !error && (
                <TopRiskTable items={data.items} />
              )}
            </div>
          </>
        )}

        {viewMode === 'project' && (
          <div className="bg-white p-12 rounded-2xl shadow-sm border border-gray-200 text-center max-w-2xl mx-auto mt-12">
            <div className="inline-flex items-center justify-center p-4 bg-rose-50 rounded-full mb-6">
              <BarChart3 className="w-10 h-10 text-rose-500" />
            </div>
            <h2 className="text-2xl font-bold text-gray-900 mb-4">Method-Level Hotspots</h2>
            <p className="text-gray-600 mb-8 max-w-lg mx-auto">
              Hotspots at the code level require static analysis of a specific project's functions to calculate internal blast radius and topological centrality.
            </p>
            <button
              onClick={() => navigate('/methods')}
              className="inline-flex items-center px-6 py-3 bg-rose-600 text-white font-medium rounded-lg hover:bg-rose-700 transition-colors shadow-sm"
            >
              Select an Analyzed Project <ArrowRight className="w-4 h-4 ml-2" />
            </button>
          </div>
        )}
        
      </div>
    </div>
  );
}
