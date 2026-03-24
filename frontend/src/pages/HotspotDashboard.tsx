import { useSearchParams, useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import axios from 'axios';
import { BarChart3, ArrowLeft, Loader2, AlertCircle } from 'lucide-react';

const fetchHotspots = async (slug: string) => {
  const { data } = await axios.get(`http://localhost:8000/methods/${slug}/hotspots?limit=50`);
  return data as any[];
};

export default function HotspotDashboard() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const project = searchParams.get('project');

  const { data: hotspots, isLoading, error } = useQuery({
    queryKey: ['method-hotspots', project],
    queryFn: () => fetchHotspots(project!),
    enabled: !!project,
  });

  if (!project) {
    return (
      <div className="flex flex-col items-center justify-center p-12 text-center h-full">
        <AlertCircle className="w-12 h-12 text-rose-500 mb-4" />
        <h2 className="text-xl font-bold">No Project Selected</h2>
        <button onClick={() => navigate('/methods')} className="mt-4 px-4 py-2 border rounded shadow-sm hover:bg-gray-50">Back to Explorer</button>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full bg-slate-50">
      <header className="bg-white border-b border-gray-200 px-6 py-4 flex items-center justify-between shrink-0">
        <div className="flex items-center">
          <button onClick={() => navigate('/methods')} className="mr-4 p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-full transition-colors">
            <ArrowLeft className="w-5 h-5" />
          </button>
          <div>
            <h1 className="text-xl font-bold text-gray-900 flex items-center">
              <BarChart3 className="w-6 h-6 text-rose-500 mr-2" />
              Method Hotspots
            </h1>
            <p className="text-sm text-gray-500 font-mono mt-0.5">{project}</p>
          </div>
        </div>
      </header>

      <main className="flex-1 overflow-y-auto p-6">
        <div className="max-w-6xl mx-auto space-y-6">
          <div className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm">
             <h2 className="text-lg font-bold text-gray-800 mb-2">Composite Risk Architecture</h2>
             <p className="text-sm text-gray-600 max-w-3xl">
               Methods designated as hotspots sit at critical junctions within the application.
               Their risk score is calculated via <code className="bg-slate-100 px-1 py-0.5 rounded text-rose-600">Complexity × Centrality × Blast Radius</code>.
               Refactoring these limits structural coupling constraints.
             </p>
          </div>

          {isLoading && (
            <div className="flex flex-col items-center justify-center py-20">
              <Loader2 className="w-8 h-8 animate-spin text-rose-500 mb-4" />
              <p className="text-gray-500 font-medium">Computing topological centrality rankings...</p>
            </div>
          )}

          {error && (
            <div className="bg-red-50 border border-red-200 p-6 rounded-xl text-center">
              <AlertCircle className="w-8 h-8 text-red-500 mx-auto mb-3" />
              <p className="text-red-700 font-medium">Failed to compute hotspot limits.</p>
            </div>
          )}

          {hotspots && (
            <div className="bg-white border border-gray-200 rounded-xl shadow-sm overflow-hidden">
              <table className="w-full text-left text-sm text-gray-600">
                <thead className="bg-slate-50 border-b border-gray-200 text-gray-900">
                  <tr>
                    <th className="px-6 py-4 font-semibold">Method Signature</th>
                    <th className="px-6 py-4 font-semibold text-right">Complexity</th>
                    <th className="px-6 py-4 font-semibold text-right">Blast Radius</th>
                    <th className="px-6 py-4 font-semibold text-right">Centrality</th>
                    <th className="px-6 py-4 font-semibold text-right">Risk Score</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {hotspots.map((item, i) => (
                    <tr key={item.method.id} className="hover:bg-slate-50/80 transition-colors">
                      <td className="px-6 py-4">
                        <div className="flex items-center">
                          <span className="font-bold text-gray-400 mr-3 w-4 text-xs">{i + 1}</span>
                          <div>
                            <p className="font-mono font-medium text-gray-800 text-xs">{item.method.name}</p>
                            <p className="text-[10px] text-gray-400 font-mono mt-0.5 max-w-sm truncate" title={item.method.file_path}>
                              {item.method.file_path}:{item.method.start_line}
                            </p>
                          </div>
                        </div>
                      </td>
                      <td className="px-6 py-4 text-right font-mono">
                        <div className="flex items-center justify-end gap-1.5">
                          {item.metrics.complexity > 10 ? <AlertCircle className="w-3.5 h-3.5 text-amber-500"/> : null}
                          {item.metrics.complexity}
                        </div>
                      </td>
                      <td className="px-6 py-4 text-right font-mono text-purple-600">{item.metrics.blast_radius || 0}</td>
                      <td className="px-6 py-4 text-right font-mono text-blue-600">{(item.metrics.betweenness_centrality || 0).toFixed(4)}</td>
                      <td className="px-6 py-4 text-right font-mono font-bold text-rose-600">
                         {item.composite_risk > 1000 ? (item.composite_risk / 1000).toFixed(1) + 'k' : Math.round(item.composite_risk)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
