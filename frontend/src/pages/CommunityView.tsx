import { useSearchParams, useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import axios from 'axios';
import { ArrowLeft, Loader2, AlertCircle, Users, Box } from 'lucide-react';

const fetchCommunities = async (slug: string) => {
  const { data } = await axios.get(`http://localhost:8000/methods/${slug}/communities`);
  return data as Record<string, any[]>;
};

export default function CommunityView() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const project = searchParams.get('project');

  const { data: communities, isLoading, error } = useQuery({
    queryKey: ['method-communities', project],
    queryFn: () => fetchCommunities(project!),
    enabled: !!project,
  });

  if (!project) {
    return (
      <div className="flex flex-col items-center justify-center p-12 text-center h-full">
        <AlertCircle className="w-12 h-12 text-emerald-500 mb-4" />
        <h2 className="text-xl font-bold">No Project Selected</h2>
        <button onClick={() => navigate('/methods')} className="mt-4 px-4 py-2 border rounded shadow-sm hover:bg-gray-50">Back to Explorer</button>
      </div>
    );
  }

  // Precompute sorted communities by size
  const sortedCommunities = communities
    ? Object.entries(communities).sort(([, a], [, b]) => b.length - a.length)
    : [];

  return (
    <div className="flex flex-col h-full bg-slate-50">
      <header className="bg-white border-b border-gray-200 px-6 py-4 flex items-center justify-between shrink-0">
        <div className="flex items-center">
          <button onClick={() => navigate('/methods')} className="mr-4 p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-full transition-colors">
            <ArrowLeft className="w-5 h-5" />
          </button>
          <div>
            <h1 className="text-xl font-bold text-gray-900 flex items-center">
              <Users className="w-6 h-6 text-emerald-500 mr-2" />
              Architectural Communities
            </h1>
            <p className="text-sm text-gray-500 font-mono mt-0.5">{project}</p>
          </div>
        </div>
      </header>

      <main className="flex-1 overflow-y-auto p-6">
        <div className="max-w-7xl mx-auto space-y-6">
          <div className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm flex items-start gap-4">
            <div className="p-3 bg-emerald-100 rounded-lg text-emerald-600 shrink-0">
              <Box className="w-6 h-6" />
            </div>
            <div>
              <h2 className="text-lg font-bold text-gray-800 mb-1">Subsystem Drift Detection</h2>
              <p className="text-sm text-gray-600 max-w-4xl">
                The Louvain community detection algorithm native to OSCAR automatically clusters method executions into logical functional groups based on topological cohesion. High cross-cluster chatter often indicates architectural drift exposing massive transitive vulnerability layers.
              </p>
            </div>
          </div>

          {isLoading && (
            <div className="flex flex-col items-center justify-center py-20">
              <Loader2 className="w-8 h-8 animate-spin text-emerald-500 mb-4" />
              <p className="text-gray-500 font-medium">Resolving algorithmic community constraints...</p>
            </div>
          )}

          {error && (
            <div className="bg-red-50 border border-red-200 p-6 rounded-xl text-center">
              <AlertCircle className="w-8 h-8 text-red-500 mx-auto mb-3" />
              <p className="text-red-700 font-medium">Failed to compute Louvain graphs.</p>
            </div>
          )}

          {sortedCommunities.length > 0 && (
            <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-6">
              {sortedCommunities.map(([cid, methods]) => {
                // Determine dominant file for this community
                const fileCounts: Record<string, number> = {};
                methods.forEach(m => {
                  const fp = m.method.file_path || 'unknown';
                  fileCounts[fp] = (fileCounts[fp] || 0) + 1;
                });
                const dominantFile = Object.entries(fileCounts).sort(([,a], [,b]) => b - a)[0][0];
                const cleanDominantPath = dominantFile.split('/').pop() || 'Dynamic Execution';

                return (
                  <div key={cid} className="bg-white border border-gray-200 rounded-xl shadow-sm flex flex-col h-[400px]">
                    <div className="p-4 border-b border-gray-100 shrink-0 bg-slate-50/50 rounded-t-xl">
                      <div className="flex justify-between items-center mb-1">
                        <h3 className="font-bold text-gray-800">Community #{cid}</h3>
                        <span className="bg-emerald-100 text-emerald-700 font-bold px-2 py-0.5 rounded-md text-xs">
                          {methods.length} methods
                        </span>
                      </div>
                      <p className="text-xs text-gray-500 font-mono truncate" title={dominantFile}>
                        Base: {cleanDominantPath}
                      </p>
                    </div>
                    
                    <div className="flex-1 overflow-y-auto p-3 space-y-2">
                      {methods.map(m => (
                        <div key={m.method.id} className="p-2 bg-slate-50 border border-gray-100 rounded text-[11px] font-mono hover:border-emerald-200 transition-colors">
                          <p className="font-bold text-gray-700 truncate">{m.method.name}</p>
                          <p className="text-gray-400 mt-0.5 truncate">{m.method.file_path?.split('/').pop()}:{m.method.start_line}</p>
                        </div>
                      ))}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
