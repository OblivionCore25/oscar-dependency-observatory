import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Search, Loader2, AlertCircle, Network, ArrowRight, FlaskConical } from 'lucide-react';
import { usePackageQuery } from '../hooks/usePackageQuery';

export default function PackageSearch() {
  const navigate = useNavigate();
  const [ecosystem, setEcosystem] = useState<string>('npm');
  const [packageName, setPackageName] = useState<string>('');
  const [version, setVersion] = useState<string>('');
  
  // Only trigger query when form is explicitly submitted
  const [queryParams, setQueryParams] = useState<{ ecosystem: string; packageName: string; version: string } | null>(null);

  const { data, isLoading, error } = usePackageQuery({
    ecosystem: queryParams?.ecosystem || '',
    packageName: queryParams?.packageName || '',
    version: queryParams?.version || '',
    enabled: !!queryParams,
  });

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (packageName && version) {
      setQueryParams({ ecosystem, packageName, version });
    }
  };

  const handleViewGraph = () => {
    if (data) {
      navigate(`/graph?ecosystem=${data.ecosystem}&package=${encodeURIComponent(data.name)}&version=${encodeURIComponent(data.version)}`);
    }
  };

  return (
    <div className="p-8 h-full flex flex-col overflow-y-auto">
      <header className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900 tracking-tight">Package Search</h1>
        <p className="text-gray-500 mt-2">Find and explore dependencies for any package.</p>
      </header>
      
      <div className="bg-white border border-gray-200 rounded-xl shadow-sm p-6 mb-8 shrink-0">
        <form onSubmit={handleSearch} className="flex flex-col md:flex-row gap-4 items-end">
          <div className="flex-1 min-w-[200px]">
            <label className="block text-sm font-medium text-gray-700 mb-1">Ecosystem</label>
            <select 
              value={ecosystem}
              onChange={(e) => setEcosystem(e.target.value)}
              className="w-full h-10 px-3 py-2 bg-white border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            >
              <option value="npm">NPM</option>
              <option value="pypi">PyPI</option>
            </select>
          </div>
          
          <div className="flex-[2] min-w-[200px]">
            <label className="block text-sm font-medium text-gray-700 mb-1">Package Name</label>
            <input 
              type="text" 
              value={packageName}
              onChange={(e) => setPackageName(e.target.value)}
              placeholder="e.g. react or fastapi"
              required
              className="w-full h-10 px-3 py-2 border border-gray-300 rounded-md shadow-sm placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            />
          </div>

          <div className="flex-1 min-w-[150px]">
            <label className="block text-sm font-medium text-gray-700 mb-1">Version</label>
            <input 
              type="text" 
              value={version}
              onChange={(e) => setVersion(e.target.value)}
              placeholder="e.g. 18.2.0"
              required
              className="w-full h-10 px-3 py-2 border border-gray-300 rounded-md shadow-sm placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            />
          </div>

          <button 
            type="submit"
            disabled={isLoading || !packageName || !version}
            className="h-10 px-6 bg-blue-600 text-white rounded-md font-medium hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed flex items-center transition-colors"
          >
            {isLoading ? <Loader2 className="w-5 h-5 animate-spin mr-2" /> : <Search className="w-5 h-5 mr-2" />}
            Search
          </button>
        </form>
      </div>

      {/* States */}
      {error && (
        <div className="bg-red-50 border-l-4 border-red-500 p-4 rounded-md mb-8 flex items-start">
          <AlertCircle className="w-5 h-5 text-red-500 mr-3 mt-0.5 shrink-0" />
          <div>
            <h3 className="text-red-800 font-medium">Search Failed</h3>
            <p className="text-red-700 mt-1 text-sm">
              {(error as any)?.response?.data?.detail || error.message || 'The specified package or version could not be found locally or on the upstream registry.'}
            </p>
          </div>
        </div>
      )}

      {/* Results Content */}
      {data && !isLoading && (
        <div className="bg-white border border-gray-200 rounded-xl shadow-sm overflow-hidden flex flex-col slide-in-bottom">
          <div className="border-b border-gray-200 bg-gray-50 px-6 py-4 flex items-center justify-between">
            <div>
              <h2 className="text-xl font-bold text-gray-900 flex items-center">
                <span className="bg-blue-100 text-blue-800 text-xs px-2 py-1 uppercase tracking-wide rounded-md mr-3 font-semibold">
                  {data.ecosystem}
                </span>
                {data.name} <span className="text-gray-400 font-normal ml-2">v{data.version}</span>
              </h2>
            </div>
            <div className="flex items-center gap-3">
              <button 
                onClick={() => navigate('/methods')}
                className="px-4 py-2 bg-purple-50 border border-purple-200 text-purple-700 rounded-md font-medium hover:bg-purple-100 focus:outline-none focus:ring-2 focus:ring-purple-500 flex items-center shadow-sm transition-colors"
              >
                <FlaskConical className="w-4 h-4 mr-2 text-purple-600" />
                Method Insights
              </button>
              <button 
                onClick={handleViewGraph}
                className="px-4 py-2 bg-white border border-gray-300 text-gray-700 rounded-md font-medium hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-blue-500 flex items-center shadow-sm transition-colors"
              >
                <Network className="w-4 h-4 mr-2 text-blue-600" />
                View Graph
                <ArrowRight className="w-4 h-4 ml-2 text-gray-400" />
              </button>
            </div>
          </div>
          
          <div className="p-6 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            <div className="bg-gray-50 rounded-lg p-4 border border-gray-100">
              <span className="text-gray-500 text-sm font-medium mb-1 block">Direct Dependencies</span>
              <span className="text-3xl font-bold text-gray-900">{data.metrics.directDependencies}</span>
            </div>
            
            <div className="bg-gray-50 rounded-lg p-4 border border-gray-100">
              <span className="text-gray-500 text-sm font-medium mb-1 block">Fan-Out (Graph Size)</span>
              <span className="text-3xl font-bold text-gray-900">{data.metrics.fanOut}</span>
            </div>
            
            <div className="bg-gray-50 rounded-lg p-4 border border-gray-100">
              <span className="text-gray-500 text-sm font-medium mb-1 block">Fan-In (Dependents)</span>
              <span className="text-3xl font-bold text-blue-600">{data.metrics.fanIn}</span>
            </div>
            
            <div className="bg-gray-50 rounded-lg p-4 border border-gray-100 relative overflow-hidden">
              <div className="absolute top-0 right-0 w-16 h-16 bg-red-100 rounded-bl-full opacity-50 -mr-8 -mt-8"></div>
              <span className="text-gray-500 text-sm font-medium mb-1 block relative z-10">Bottleneck Score</span>
              <span className="text-3xl font-bold text-red-600 relative z-10">{data.metrics.bottleneckScore.toFixed(1)}</span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
