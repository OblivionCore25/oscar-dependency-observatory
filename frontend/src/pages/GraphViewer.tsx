import { useSearchParams, useNavigate } from 'react-router-dom';
import { useGraphQuery } from '../hooks/useGraphQuery';
import GraphCanvas from '../components/GraphCanvas';
import { Network, Loader2, ArrowLeft, AlertCircle, PanelRight, FlaskConical } from 'lucide-react';
import { useState } from 'react';

export default function GraphViewer() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [selectedEdge, setSelectedEdge] = useState<{ source: string; target: string } | null>(null);

  const ecosystem = searchParams.get('ecosystem');
  const packageName = searchParams.get('package');
  const version = searchParams.get('version');

  const hasParams = !!(ecosystem && packageName && version);

  const { data, isLoading, error } = useGraphQuery({
    ecosystem,
    packageName,
    version,
  });

  const getConstraintBadge = (constraint: string) => {
    if (!constraint || constraint === 'unconstrained') {
      return 'bg-red-100 text-red-700 border border-red-200';
    }
    if (constraint.startsWith('==') || constraint.includes('===')) {
      return 'bg-amber-100 text-amber-700 border border-amber-200';
    }
    return 'bg-green-100 text-green-700 border border-green-200';
  };

  const getConstraintIcon = (constraint: string) => {
    if (!constraint || constraint === 'unconstrained') return '⚠️';
    if (constraint.startsWith('==') || constraint.includes('===')) return '🔒';
    return '✓';
  };

  return (
    <div className="h-full flex flex-col bg-slate-50 relative overflow-hidden">
      {/* Overlay Header */}
      <header className="absolute top-0 left-0 right-0 p-4 z-10 flex justify-between items-start pointer-events-none">
        <div className="pointer-events-auto bg-white/90 backdrop-blur-sm border border-gray-200 shadow-sm rounded-lg px-4 py-3 flex items-center">
          <Network className="w-5 h-5 text-blue-600 mr-3" />
          <div>
            <h1 className="text-sm font-bold text-gray-900 leading-none">
              {hasParams ? `${packageName} v${version}` : 'Graph Viewer'}
            </h1>
            <p className="text-xs text-gray-500 mt-1 uppercase tracking-wider font-semibold">
              {hasParams ? ecosystem : 'Awaiting Selection'}
            </p>
          </div>
        </div>

        <div className="pointer-events-auto flex gap-2">
          {hasParams && (
            <button
              onClick={() => navigate(`/methods/graph?project=${packageName}-${version}`)}
              className="bg-white border border-indigo-200 shadow-sm text-indigo-700 px-3 py-2 rounded-lg font-medium text-sm hover:bg-indigo-50 flex items-center transition-colors"
            >
              <FlaskConical className="w-4 h-4 mr-2" />
              Method Call Graph
            </button>
          )}
          {data && (
            <button
              onClick={() => setSidebarOpen(o => !o)}
              className={`bg-white border shadow-sm px-3 py-2 rounded-lg font-medium text-sm flex items-center transition-colors gap-2 ${
                sidebarOpen
                  ? 'border-blue-300 text-blue-700 bg-blue-50'
                  : 'border-gray-200 text-gray-700 hover:bg-gray-50'
              }`}
            >
              <PanelRight className="w-4 h-4" />
              Edge Constraints
              {data.edges.length > 0 && (
                <span className="bg-blue-100 text-blue-700 text-xs font-bold px-1.5 py-0.5 rounded-full">
                  {data.edges.length}
                </span>
              )}
            </button>
          )}
          <button
            onClick={() => navigate('/')}
            className="bg-white border border-gray-200 shadow-sm text-gray-700 px-4 py-2 rounded-lg font-medium text-sm hover:bg-gray-50 flex items-center transition-colors"
          >
            <ArrowLeft className="w-4 h-4 mr-2" />
            Back to Search
          </button>
        </div>
      </header>

      {/* Main Content */}
      <div className="flex-1 flex overflow-hidden">

        {/* Graph Canvas */}
        <div className={`relative flex-1 transition-all duration-200 ${sidebarOpen && data ? 'mr-72' : ''}`}>

          {!hasParams && (
            <div className="absolute inset-0 flex flex-col items-center justify-center">
              <div className="bg-white p-8 rounded-xl shadow-sm border border-gray-200 max-w-md text-center">
                <Network className="w-12 h-12 text-gray-300 mx-auto mb-4" />
                <h2 className="text-xl font-bold text-gray-900 mb-2">No Package Selected</h2>
                <p className="text-gray-500 mb-6">Return to search to select a package to visualize.</p>
                <button
                  onClick={() => navigate('/')}
                  className="bg-blue-600 text-white px-6 py-2 rounded-md font-medium hover:bg-blue-700 transition-colors inline-flex items-center"
                >
                  Go to Search <ArrowLeft className="w-4 h-4 ml-2 rotate-180" />
                </button>
              </div>
            </div>
          )}

          {hasParams && isLoading && (
            <div className="absolute inset-0 flex flex-col items-center justify-center bg-slate-50/80 backdrop-blur-sm z-20">
              <Loader2 className="w-10 h-10 text-blue-600 animate-spin mb-4" />
              <h2 className="text-lg font-semibold text-gray-900">Resolving Transitive Graph...</h2>
              <p className="text-gray-500 text-sm mt-2 max-w-xs text-center">
                Fetching all indirect dependencies. This may take a few seconds for very large packages.
              </p>
            </div>
          )}

          {hasParams && error && (
            <div className="absolute inset-0 flex flex-col items-center justify-center bg-slate-50/80 z-20">
              <div className="bg-white p-8 rounded-xl shadow-sm border border-red-200 max-w-md text-center">
                <AlertCircle className="w-12 h-12 text-red-500 mx-auto mb-4" />
                <h2 className="text-xl font-bold text-gray-900 mb-2">Graph Resolution Failed</h2>
                <p className="text-red-600 mb-6 text-sm">
                  {(error as any)?.response?.data?.detail || error.message}
                </p>
                <button onClick={() => navigate('/')} className="bg-gray-100 text-gray-800 px-6 py-2 border border-gray-300 rounded-md font-medium">
                  Return to Search
                </button>
              </div>
            </div>
          )}

          {hasParams && data && !isLoading && !error && (
            <GraphCanvas data={data} onEdgeSelect={setSelectedEdge} />
          )}
        </div>

        {/* Edge Constraints Sidebar */}
        {data && sidebarOpen && (
          <div className="absolute top-0 right-0 bottom-0 w-72 bg-white border-l border-gray-200 shadow-md flex flex-col z-10">
            <div className="px-4 py-3 border-b border-gray-100 flex items-center justify-between shrink-0">
              <div>
                <h2 className="text-sm font-bold text-gray-900">Edge Constraints</h2>
                <p className="text-xs text-gray-500 mt-0.5">{data.edges.length} dependencies</p>
              </div>
              <div className="flex items-center gap-2">
                <div className="flex gap-1.5 text-[10px] font-semibold">
                  <span className="bg-red-100 text-red-700 px-1.5 py-0.5 rounded-full">
                    ⚠️ {data.edges.filter(e => !e.constraint).length}
                  </span>
                  <span className="bg-green-100 text-green-700 px-1.5 py-0.5 rounded-full">
                    ✓ {data.edges.filter(e => !!e.constraint && !e.constraint.startsWith('==')).length}
                  </span>
                </div>
                <button
                  onClick={() => setSidebarOpen(false)}
                  className="ml-1 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded p-0.5 transition-colors"
                  title="Close"
                >
                  <svg xmlns="http://www.w3.org/2000/svg" className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <line x1="18" y1="6" x2="6" y2="18"/>
                    <line x1="6" y1="6" x2="18" y2="18"/>
                  </svg>
                </button>
              </div>
            </div>

            <div className="overflow-y-auto flex-1 p-2 space-y-1.5">
              {data.edges.length === 0 ? (
                <p className="text-gray-400 text-xs text-center py-8">No dependencies found.</p>
              ) : (
                data.edges.map((edge, i) => {
                  const isSelected = selectedEdge?.source === edge.source && selectedEdge?.target === edge.target;
                  return (
                    <div
                      key={i}
                      className={`rounded-lg p-3 border transition-colors ${
                        isSelected
                          ? 'border-blue-300 bg-blue-50'
                          : 'border-gray-100 bg-gray-50 hover:border-gray-200'
                      }`}
                    >
                      <div className="flex items-start justify-between gap-2">
                        <div className="min-w-0 flex-1">
                          <p className="text-[11px] font-medium text-gray-800 truncate font-mono">{edge.target}</p>
                          <p className="text-[10px] text-gray-400 truncate mt-0.5">from {edge.source}</p>
                        </div>
                        <span className={`shrink-0 text-[10px] font-mono px-1.5 py-0.5 rounded-full font-semibold ${getConstraintBadge(edge.constraint || '')}`}>
                          {getConstraintIcon(edge.constraint || '')}
                        </span>
                      </div>
                      {edge.constraint && (
                        <code className="block mt-1.5 text-[10px] text-gray-600 bg-white rounded border border-gray-100 px-1.5 py-0.5 truncate">
                          {edge.constraint}
                        </code>
                      )}
                    </div>
                  );
                })
              )}
            </div>

            {/* Legend */}
            <div className="border-t border-gray-100 p-3 shrink-0 space-y-1">
              <p className="text-[10px] font-bold text-gray-500 uppercase tracking-wide mb-1.5">Legend</p>
              <div className="flex items-center gap-2 text-[10px] text-gray-500">
                <span className="bg-red-100 text-red-700 px-1.5 py-0.5 rounded-full font-semibold">⚠️</span>
                <span>Unconstrained — highest update risk</span>
              </div>
              <div className="flex items-center gap-2 text-[10px] text-gray-500">
                <span className="bg-amber-100 text-amber-700 px-1.5 py-0.5 rounded-full font-semibold">🔒</span>
                <span>Pinned — brittle, blocks patches</span>
              </div>
              <div className="flex items-center gap-2 text-[10px] text-gray-500">
                <span className="bg-green-100 text-green-700 px-1.5 py-0.5 rounded-full font-semibold">✓</span>
                <span>Range-bounded — healthy</span>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
