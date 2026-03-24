import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import axios from 'axios';
import { Network, Search, Loader2, AlertCircle, PlayCircle, BarChart3, Users } from 'lucide-react';
import { Link } from 'react-router-dom';

// Fetch the list of analyzed projects
const fetchProjects = async () => {
  const { data } = await axios.get('http://localhost:8000/methods/projects');
  return data as string[];
};

export default function MethodExplorer() {
  const [searchTerm, setSearchTerm] = useState('');

  const { data: projects, isLoading, error } = useQuery({
    queryKey: ['method-projects'],
    queryFn: fetchProjects,
  });

  const filteredProjects = projects?.filter(p => p.toLowerCase().includes(searchTerm.toLowerCase())) || [];

  return (
    <div className="max-w-5xl mx-auto p-8 h-full flex flex-col">
      <div className="text-center mb-10 mt-8">
        <div className="inline-flex items-center justify-center p-3 bg-indigo-100 rounded-full mb-4">
          <Network className="w-8 h-8 text-indigo-600" />
        </div>
        <h1 className="text-3xl font-extrabold text-gray-900 tracking-tight">Method Explorer</h1>
        <p className="mt-3 text-lg text-gray-500 max-w-2xl mx-auto">
          Analyze internal Python method topologies. Select a strictly analyzed project repository to browse architectural communities and hotspot blast limits.
        </p>
      </div>

      <div className="flex-1 bg-white rounded-2xl shadow-sm border border-gray-200 overflow-hidden flex flex-col">
        <div className="p-4 border-b border-gray-100 bg-slate-50 relative">
          <Search className="absolute left-7 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
          <input
            type="text"
            placeholder="Search analyzed project slugs..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-10 pr-4 py-3 bg-white border border-gray-300 rounded-lg shadow-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none transition-all"
          />
        </div>

        <div className="flex-1 overflow-y-auto p-4 bg-gray-50/50">
          {isLoading && (
            <div className="flex flex-col items-center justify-center h-full text-gray-500">
              <Loader2 className="w-8 h-8 animate-spin mb-3 text-indigo-500" />
              <p>Scanning registry for native runtimes...</p>
            </div>
          )}

          {error && (
            <div className="flex flex-col items-center justify-center h-full text-red-500">
              <AlertCircle className="w-10 h-10 mb-3" />
              <p className="font-semibold px-4 text-center">Failed to fetch analyzed applications.</p>
              <p className="text-xs text-red-400 mt-2 font-mono">{(error as any).message}</p>
            </div>
          )}

          {!isLoading && !error && filteredProjects.length === 0 && (
            <div className="flex flex-col items-center justify-center h-full text-gray-400">
              <p className="text-lg font-medium">No active runtime instances bound.</p>
              <p className="text-sm mt-1">Check your API search parameters or run local backend ingests.</p>
            </div>
          )}

          {!isLoading && !error && filteredProjects.length > 0 && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {filteredProjects.map((slug) => (
                <div key={slug} className="bg-white p-5 rounded-xl border border-gray-200 shadow-sm hover:border-indigo-300 hover:shadow-md transition-all group">
                  <div className="flex justify-between items-start mb-4">
                    <div>
                      <h3 className="text-lg font-bold text-gray-900 group-hover:text-indigo-600 transition-colors font-mono">{slug}</h3>
                      <p className="text-xs text-gray-500 mt-1 uppercase tracking-wider font-semibold">Python Runtime</p>
                    </div>
                  </div>
                  
                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 mt-4 pt-4 border-t border-gray-100">
                    <Link
                      to={`/methods/graph?project=${slug}`}
                      className="flex items-center justify-center p-2 rounded-md bg-slate-50 hover:bg-indigo-50 text-slate-700 hover:text-indigo-700 font-medium text-xs transition-colors border border-slate-200"
                    >
                      <PlayCircle className="w-4 h-4 mr-1.5" />
                      Visualizer
                    </Link>
                    <Link
                      to={`/methods/hotspots?project=${slug}`}
                      className="flex items-center justify-center p-2 rounded-md bg-slate-50 hover:bg-rose-50 text-slate-700 hover:text-rose-700 font-medium text-xs transition-colors border border-slate-200"
                    >
                      <BarChart3 className="w-4 h-4 mr-1.5" />
                      Hotspots
                    </Link>
                    <Link
                      to={`/methods/communities?project=${slug}`}
                      className="flex items-center justify-center p-2 rounded-md bg-slate-50 hover:bg-emerald-50 text-slate-700 hover:text-emerald-700 font-medium text-xs transition-colors border border-slate-200"
                    >
                      <Users className="w-4 h-4 mr-1.5" />
                      Communities
                    </Link>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
