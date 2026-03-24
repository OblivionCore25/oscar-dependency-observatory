import { useState, useMemo } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import axios from 'axios';
import { ArrowLeft, Loader2, AlertCircle, PlayCircle } from 'lucide-react';
import MethodCallGraph from '../components/MethodCallGraph';

const fetchGraph = async (slug: string) => {
  try {
    const { data } = await axios.get(`http://localhost:8000/methods/${slug}/graph`);
    return data;
  } catch (err: any) {
    // Surface the backend's detail message instead of the generic Axios one
    const detail = err?.response?.data?.detail;
    if (detail) throw new Error(detail);
    throw err;
  }
};

export default function MethodGraphViewer() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const project = searchParams.get('project');
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);

  const { data, isLoading, error } = useQuery({
    queryKey: ['method-graph', project],
    queryFn: () => fetchGraph(project!),
    enabled: !!project,
  });

  const { data: blastRadiusData, isLoading: isLoadingBlastRadius } = useQuery({
    queryKey: ['method-blast-radius', project, selectedNodeId],
    queryFn: async () => {
      const { data } = await axios.get(`http://localhost:8000/methods/${project}/method/${encodeURIComponent(selectedNodeId!)}/blast-radius`);
      return data;
    },
    enabled: !!project && !!selectedNodeId,
  });

  const highlightedNodes = blastRadiusData ? blastRadiusData.nodes.map((n: any) => n.id) : undefined;
  
  const selectedNodeDetails = useMemo(() => {
    if (!selectedNodeId || !data) return null;
    return data.nodes.find((n: any) => n.id === selectedNodeId);
  }, [selectedNodeId, data]);

  return (
    <div className="flex flex-col h-full bg-slate-50">
      <header className="bg-white border-b border-gray-200 px-6 py-4 flex items-center justify-between shrink-0 shadow-sm z-10">
        <div className="flex items-center">
          <button onClick={() => navigate('/methods')} className="mr-4 p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-full transition-colors">
            <ArrowLeft className="w-5 h-5" />
          </button>
          <div>
            <h1 className="text-xl font-bold text-gray-900 flex items-center">
              <PlayCircle className="w-6 h-6 text-indigo-500 mr-2" />
              Dynamic Execution Canvas
            </h1>
            <p className="text-sm text-gray-500 font-mono mt-0.5">
              {project ? `Project: ${project}` : 'Awaiting Selection'}
            </p>
          </div>
        </div>
        
        {data && (
           <div className="flex items-center gap-3">
             <div className="bg-slate-100 px-3 py-1.5 rounded-lg border border-slate-200 flex flex-col items-center">
               <span className="text-[10px] uppercase font-bold text-slate-500 tracking-wider">Nodes</span>
               <span className="text-sm font-bold text-slate-800 font-mono">{data.node_count}</span>
             </div>
             <div className="bg-slate-100 px-3 py-1.5 rounded-lg border border-slate-200 flex flex-col items-center">
               <span className="text-[10px] uppercase font-bold text-slate-500 tracking-wider">Edges</span>
               <span className="text-sm font-bold text-slate-800 font-mono">{data.edge_count}</span>
             </div>
           </div>
        )}
      </header>

      <main className="flex-1 relative overflow-hidden bg-slate-100 flex">
        <div className={`flex-1 relative transition-all duration-300 ${selectedNodeId ? 'mr-80' : ''}`}>
          {!project && (
            <div className="absolute inset-0 flex flex-col items-center justify-center p-12 text-center h-full">
              <AlertCircle className="w-12 h-12 text-indigo-500 mb-4" />
              <h2 className="text-xl font-bold">No Project Selected</h2>
              <button onClick={() => navigate('/methods')} className="mt-4 px-4 py-2 bg-white border rounded shadow-sm hover:bg-gray-50">Back to Explorer</button>
            </div>
          )}

          {project && isLoading && (
            <div className="absolute inset-0 flex flex-col items-center justify-center bg-slate-50/80 backdrop-blur-sm z-20">
              <Loader2 className="w-10 h-10 animate-spin text-indigo-500 mb-4" />
              <p className="text-gray-600 font-medium">Booting WebGL graph topology...</p>
            </div>
          )}

          {project && error && (
            <div className="absolute inset-0 flex flex-col items-center justify-center bg-slate-50/80 z-20">
              <div className="bg-white p-8 rounded-xl shadow-sm border border-red-200 text-center max-w-md">
                <AlertCircle className="w-12 h-12 text-red-500 mx-auto mb-4" />
                <h2 className="text-lg font-bold">Topology Render Failed</h2>
                <p className="text-red-500 mt-2 font-mono text-xs bg-red-50 rounded p-2">{(error as any).message}</p>
                <p className="text-gray-400 mt-3 text-xs">
                  Looking for project: <span className="font-mono text-gray-600">{project}</span>
                </p>
                <div className="flex gap-2 mt-5 justify-center">
                  <button onClick={() => navigate('/methods')} className="px-4 py-2 border rounded hover:bg-gray-50 text-sm">Browse Projects</button>
                  <button onClick={() => window.location.reload()} className="px-4 py-2 bg-indigo-600 text-white rounded hover:bg-indigo-700 text-sm">Retry</button>
                </div>
              </div>
            </div>
          )}

          {project && data && !isLoading && !error && (
              <MethodCallGraph data={data} highlightedNodes={highlightedNodes} onNodeSelect={setSelectedNodeId} />
          )}
        </div>

        {/* Detail Panel */}
        {selectedNodeId && selectedNodeDetails && (
          <div className="absolute top-0 right-0 bottom-0 w-80 bg-white border-l border-gray-200 shadow-xl z-20 overflow-y-auto flex flex-col animate-in slide-in-from-right-8 duration-200">
            <div className="p-4 border-b border-gray-100 flex justify-between items-start bg-slate-50 sticky top-0">
               <div className="min-w-0 pr-2">
                 <h2 className="font-bold text-gray-900 text-sm truncate" title={selectedNodeDetails.name}>
                   {selectedNodeDetails.name}
                 </h2>
                 <p className="text-[10px] text-gray-500 font-mono mt-1 break-all" title={selectedNodeDetails.file_path}>
                   {selectedNodeDetails.file_path}:{selectedNodeDetails.start_line}
                 </p>
               </div>
               <button onClick={() => setSelectedNodeId(null)} className="shrink-0 text-gray-400 hover:text-gray-600 bg-white border border-gray-200 rounded p-1 transition-colors">
                 <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" /></svg>
               </button>
            </div>
            
            <div className="p-4 flex-1 space-y-6 bg-white">
              <div>
                <h3 className="text-[10px] uppercase font-bold text-gray-500 tracking-wider mb-2">Metrics</h3>
                <div className="grid grid-cols-2 gap-2">
                  <div className="bg-slate-50 p-2.5 rounded-lg border border-gray-100">
                    <span className="text-[10px] text-gray-500 block mb-1 leading-none font-medium">Complexity</span>
                    <span className={`font-mono text-sm leading-none font-bold ${selectedNodeDetails.complexity > 10 ? 'text-amber-600' : 'text-slate-700'}`}>{selectedNodeDetails.complexity || 0}</span>
                  </div>
                  <div className="bg-slate-50 p-2.5 rounded-lg border border-gray-100">
                    <span className="text-[10px] text-gray-500 block mb-1 leading-none font-medium">Centrality</span>
                    <span className="font-mono text-sm leading-none font-bold text-blue-600">{(selectedNodeDetails.betweenness_centrality || 0).toFixed(4)}</span>
                  </div>
                  <div className="bg-slate-50 p-2.5 rounded-lg border border-gray-100">
                    <span className="text-[10px] text-gray-500 block mb-1 leading-none font-medium">Fan In</span>
                    <span className="font-mono text-sm leading-none font-bold text-slate-700">{selectedNodeDetails.fan_in || 0}</span>
                  </div>
                  <div className="bg-slate-50 p-2.5 rounded-lg border border-gray-100">
                    <span className="text-[10px] text-gray-500 block mb-1 leading-none font-medium">Fan Out</span>
                    <span className="font-mono text-sm leading-none font-bold text-slate-700">{selectedNodeDetails.fan_out || 0}</span>
                  </div>
                </div>
              </div>

              <div>
                <div className="flex justify-between items-center mb-2">
                  <h3 className="text-[10px] uppercase font-bold text-gray-500 tracking-wider">Blast Radius</h3>
                  {isLoadingBlastRadius && <Loader2 className="w-3.5 h-3.5 animate-spin text-purple-500" />}
                </div>
                <div className="bg-purple-50 p-4 rounded-xl border border-purple-100">
                  <span className="text-4xl font-black text-purple-700 block mb-2 leading-none">{selectedNodeDetails.blast_radius || 0}</span>
                  <span className="text-[11px] font-medium text-purple-600/80 leading-snug block">Transitively affected methods downstream when modified.</span>
                </div>
              </div>

              {selectedNodeDetails.community_id !== undefined && selectedNodeDetails.community_id !== null && (
                <div>
                  <h3 className="text-[10px] uppercase font-bold text-gray-500 tracking-wider mb-2">Architecture</h3>
                  <div className="flex items-center gap-2 text-sm font-medium text-slate-700">
                    <div className="w-2.5 h-2.5 rounded-full bg-emerald-500" />
                    Community Cluster #{selectedNodeDetails.community_id}
                  </div>
                </div>
              )}
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
