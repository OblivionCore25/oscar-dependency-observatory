import { useState } from 'react';
import { useAnalyticsQuery } from '../hooks/useAnalyticsQuery';
import TopRiskTable from '../components/TopRiskTable';
import { AlertTriangle, Loader2, AlertCircle } from 'lucide-react';

export default function TopRisk() {
  const [ecosystem, setEcosystem] = useState<'npm' | 'pypi'>('npm');
  const [limit, setLimit] = useState(500); // Fetch top 500 items to feed client pagination

  const { data, isLoading, error } = useAnalyticsQuery({
    ecosystem,
    limit,
  });

  return (
    <div className="h-full flex flex-col bg-slate-50 overflow-y-auto w-full">
      <div className="max-w-7xl mx-auto w-full px-6 py-8">
        
        {/* Header section with controls */}
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
        
      </div>
    </div>
  );
}
