import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import axios from 'axios';
import { Network, Search, Loader2, AlertCircle, PlayCircle, BarChart3, Users, DownloadCloud } from 'lucide-react';
import { Link } from 'react-router-dom';

// Fetch the list of analyzed projects
const fetchProjects = async () => {
  const { data } = await axios.get('http://localhost:8000/methods/projects');
  return data as string[];
};

export default function MethodExplorer() {
  const [searchTerm, setSearchTerm] = useState('');
  const [packageName, setPackageName] = useState('');
  const [packageVersion, setPackageVersion] = useState('');
  const [excludeTests, setExcludeTests] = useState(true);
  const [lastAnalyzed, setLastAnalyzed] = useState<{ slug: string; methodCount: number; fileCount: number } | null>(null);
  const queryClient = useQueryClient();

  const { data: projects, isLoading, error } = useQuery({
    queryKey: ['method-projects'],
    queryFn: fetchProjects,
  });

  const analyzeMutation = useMutation({
    mutationFn: async () => {
      const { data } = await axios.post('http://localhost:8000/methods/analyze', {
        package_name: packageName,
        package_version: packageVersion,
        exclude_tests: excludeTests,
      });
      return data;
    },
    onSuccess: (data) => {
      setLastAnalyzed({
        slug: data.project_slug,
        methodCount: data.meta.method_count,
        fileCount: data.meta.file_count,
      });
      setPackageName('');
      setPackageVersion('');
      queryClient.invalidateQueries({ queryKey: ['method-projects'] });
    },
  });

  const handleAnalyze = (e: React.FormEvent) => {
    e.preventDefault();
    if (packageName && packageVersion) {
      analyzeMutation.mutate();
    }
  };

  const filteredProjects = projects?.filter((p: string) => p.toLowerCase().includes(searchTerm.toLowerCase())) || [];

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

      <div className="mb-8 bg-white p-6 rounded-2xl shadow-sm border border-gray-200">
        <h2 className="text-xl font-bold text-gray-900 mb-4 flex items-center">
          <DownloadCloud className="w-5 h-5 mr-2 text-indigo-500" />
          Automated Package Analysis
        </h2>
        <form onSubmit={handleAnalyze} className="flex flex-col sm:flex-row gap-4">
          <div className="flex-1">
            <label htmlFor="packageName" className="block text-sm font-medium text-gray-700 mb-1">PyPI Package Name</label>
            <input
              type="text"
              id="packageName"
              value={packageName}
              onChange={(e) => setPackageName(e.target.value)}
              placeholder="e.g., requests, boto3"
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none"
              required
              disabled={analyzeMutation.isPending}
            />
          </div>
          <div className="flex-1">
            <label htmlFor="packageVersion" className="block text-sm font-medium text-gray-700 mb-1">Version</label>
            <input
              type="text"
              id="packageVersion"
              value={packageVersion}
              onChange={(e) => setPackageVersion(e.target.value)}
              placeholder="e.g., 2.31.0"
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none"
              required
              disabled={analyzeMutation.isPending}
            />
          </div>
          <div className="flex items-end">
            <button
              type="submit"
              disabled={analyzeMutation.isPending || !packageName || !packageVersion}
              className="w-full sm:w-auto px-6 py-2 bg-indigo-600 text-white font-medium rounded-lg hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center transition-colors"
            >
              {analyzeMutation.isPending ? (
                <>
                  <Loader2 className="w-5 h-5 mr-2 animate-spin" />
                  Analyzing...
                </>
              ) : (
                'Download & Analyze'
              )}
            </button>
          </div>
        </form>

        <div className="mt-3 flex items-center gap-2">
          <input
            type="checkbox"
            id="excludeTests"
            checked={excludeTests}
            onChange={(e) => setExcludeTests(e.target.checked)}
            className="w-4 h-4 text-indigo-600 rounded border-gray-300 focus:ring-indigo-500"
            disabled={analyzeMutation.isPending}
          />
          <label htmlFor="excludeTests" className="text-sm text-gray-600 select-none cursor-pointer">
            Exclude test files <span className="text-gray-400">(recommended — prevents test helper methods from skewing results)</span>
          </label>
        </div>

        {lastAnalyzed && (
          <div className="mt-4 p-3 bg-green-50 text-green-800 rounded-lg text-sm flex items-start gap-2 border border-green-200">
            <span className="mt-0.5">✅</span>
            <div>
              <span className="font-semibold">{lastAnalyzed.slug}</span> analyzed — {lastAnalyzed.methodCount.toLocaleString()} methods across {lastAnalyzed.fileCount} files.
              <span className="ml-2 text-green-600">It now appears in the project list below.</span>
            </div>
          </div>
        )}

        {analyzeMutation.isError && (
          <div className="mt-4 p-3 bg-red-50 text-red-700 rounded-lg text-sm flex items-center">
            <AlertCircle className="w-4 h-4 mr-2" />
            {(analyzeMutation.error as any)?.response?.data?.detail || (analyzeMutation.error as Error)?.message || 'Analysis failed. Check package name and version.'}
          </div>
        )}
      </div>

      {/* Project List */}
      <div className="bg-white rounded-2xl shadow-sm border border-gray-200 overflow-hidden flex flex-col">

        {/* Search bar header */}
        <div className="px-5 py-4 border-b border-gray-100 bg-slate-50 flex items-center gap-3">
          <Search className="w-5 h-5 text-gray-400 shrink-0" />
          <input
            type="text"
            placeholder="Search projects by name..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="flex-1 bg-transparent text-sm text-gray-800 placeholder-gray-400 outline-none"
          />
          {filteredProjects.length > 0 && (
            <span className="text-xs text-gray-400 font-medium shrink-0">
              {filteredProjects.length} project{filteredProjects.length !== 1 ? 's' : ''}
            </span>
          )}
        </div>

        {/* Scrollable list */}
        <div
          className="overflow-y-scroll"
          style={{ maxHeight: '480px', scrollbarWidth: 'auto', scrollbarColor: '#c7d2fe #f1f5f9' }}
        >
          {/* Loading */}
          {isLoading && (
            <div className="flex flex-col items-center justify-center py-24 text-gray-500">
              <Loader2 className="w-8 h-8 animate-spin mb-3 text-indigo-500" />
              <p className="text-sm">Loading analyzed projects...</p>
            </div>
          )}

          {/* Error */}
          {error && (
            <div className="flex flex-col items-center justify-center py-24 text-red-500">
              <AlertCircle className="w-10 h-10 mb-3" />
              <p className="font-semibold text-center">Failed to load projects.</p>
              <p className="text-xs text-red-400 mt-2 font-mono">{(error as any).message}</p>
            </div>
          )}

          {/* Empty state */}
          {!isLoading && !error && filteredProjects.length === 0 && (
            <div className="flex flex-col items-center justify-center py-24 text-gray-400">
              <p className="text-base font-medium">No projects found.</p>
              <p className="text-sm mt-1">Try a different search term, or analyze your first package above.</p>
            </div>
          )}

          {/* Project rows */}
          {!isLoading && !error && filteredProjects.length > 0 && (
            <ul className="divide-y divide-gray-100">
              {filteredProjects.map((slug: string) => (
                <li
                  key={slug}
                  className="flex items-center gap-4 px-5 py-4 hover:bg-indigo-50/40 transition-colors group"
                >
                  {/* Icon */}
                  <div className="w-10 h-10 rounded-lg bg-indigo-100 flex items-center justify-center shrink-0 group-hover:bg-indigo-200 transition-colors">
                    <span className="text-lg" role="img" aria-label="package">📦</span>
                  </div>

                  {/* Slug + label */}
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-bold text-gray-900 font-mono group-hover:text-indigo-700 transition-colors truncate">
                      {slug}
                    </p>
                    <p className="text-xs text-gray-400 mt-0.5 uppercase tracking-wide font-medium">
                      Python · AST Static Analysis
                    </p>
                  </div>

                  {/* Action buttons */}
                  <div className="flex items-center gap-2 shrink-0">
                    <Link
                      to={`/methods/graph?project=${slug}`}
                      className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-white border border-slate-200 text-slate-700 hover:border-indigo-400 hover:text-indigo-700 hover:bg-indigo-50 text-xs font-medium transition-all shadow-sm"
                    >
                      <PlayCircle className="w-3.5 h-3.5" />
                      Visualizer
                    </Link>
                    <Link
                      to={`/methods/hotspots?project=${slug}`}
                      className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-white border border-slate-200 text-slate-700 hover:border-rose-400 hover:text-rose-700 hover:bg-rose-50 text-xs font-medium transition-all shadow-sm"
                    >
                      <BarChart3 className="w-3.5 h-3.5" />
                      Hotspots
                    </Link>
                    <Link
                      to={`/methods/communities?project=${slug}`}
                      className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-white border border-slate-200 text-slate-700 hover:border-emerald-400 hover:text-emerald-700 hover:bg-emerald-50 text-xs font-medium transition-all shadow-sm"
                    >
                      <Users className="w-3.5 h-3.5" />
                      Communities
                    </Link>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>

        {/* Footer hint if scrollable */}
        {filteredProjects.length > 5 && (
          <div className="px-5 py-2.5 bg-slate-50 border-t border-gray-100 flex items-center justify-center gap-1.5 text-xs text-gray-400">
            <span>↕</span>
            <span>Scroll to see all {filteredProjects.length} projects</span>
          </div>
        )}
      </div>
    </div>
  );
}
