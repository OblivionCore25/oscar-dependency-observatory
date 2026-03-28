import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import axios from 'axios';
import { History, Plus, GitCompare, Loader2, Calendar, Database, AlertCircle } from 'lucide-react';
import type { Snapshot, SnapshotComparisonResponse } from '../types/api';

const fetchSnapshots = async (ecosystem: string) => {
  const { data } = await axios.get<Snapshot[]>(`http://localhost:8000/snapshots/${ecosystem}`);
  return data;
};

const createSnapshot = async ({ ecosystem, description }: { ecosystem: string, description: string }) => {
  const { data } = await axios.post<Snapshot>(`http://localhost:8000/snapshots/${ecosystem}`, { description });
  return data;
};

const compareSnapshots = async ({ ecosystem, snapshot1, snapshot2 }: { ecosystem: string, snapshot1: string, snapshot2: string }) => {
  const { data } = await axios.get<SnapshotComparisonResponse>(`http://localhost:8000/snapshots/${ecosystem}/compare`, {
    params: { snapshot_1: snapshot1, snapshot_2: snapshot2 }
  });
  return data;
};

export default function SnapshotsView() {
  const [ecosystem, setEcosystem] = useState('npm');
  const [description, setDescription] = useState('');
  const [compare1, setCompare1] = useState('');
  const [compare2, setCompare2] = useState('');
  const queryClient = useQueryClient();

  const { data: snapshots, isLoading } = useQuery({
    queryKey: ['snapshots', ecosystem],
    queryFn: () => fetchSnapshots(ecosystem),
  });

  const createMutation = useMutation({
    mutationFn: createSnapshot,
    onSuccess: () => {
      setDescription('');
      queryClient.invalidateQueries({ queryKey: ['snapshots', ecosystem] });
    },
  });

  const compareMutation = useMutation({
    mutationFn: compareSnapshots,
  });

  const handleCreate = (e: React.FormEvent) => {
    e.preventDefault();
    createMutation.mutate({ ecosystem, description });
  };

  const handleCompare = (e: React.FormEvent) => {
    e.preventDefault();
    if (compare1 && compare2) {
      compareMutation.mutate({ ecosystem, snapshot1: compare1, snapshot2: compare2 });
    }
  };

  return (
    <div className="p-8 h-full flex flex-col overflow-y-auto">
      <header className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900 tracking-tight flex items-center">
          <History className="w-8 h-8 mr-3 text-indigo-500" />
          Temporal Snapshots
        </h1>
        <p className="text-gray-500 mt-2">Capture and compare point-in-time states of the dependency graph.</p>
      </header>

      <div className="mb-6 flex gap-4 items-center">
        <label className="text-sm font-bold text-gray-700 uppercase tracking-wider">Ecosystem:</label>
        <select
          value={ecosystem}
          onChange={(e) => {
            setEcosystem(e.target.value);
            setCompare1('');
            setCompare2('');
            compareMutation.reset();
          }}
          className="h-10 px-4 bg-white border border-gray-300 rounded-md shadow-sm focus:ring-2 focus:ring-indigo-500"
        >
          <option value="npm">NPM</option>
          <option value="pypi">PyPI</option>
        </select>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Create Snapshot */}
        <div className="bg-white border border-gray-200 rounded-xl shadow-sm p-6 flex flex-col">
          <h2 className="text-lg font-bold text-gray-900 flex items-center mb-4">
            <Database className="w-5 h-5 mr-2 text-blue-500" />
            Capture New Snapshot
          </h2>
          <form onSubmit={handleCreate} className="flex flex-col flex-1">
            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-700 mb-1">Description (Optional)</label>
              <input
                type="text"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="e.g., Before React 19 upgrade..."
                className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div className="mt-auto">
              <button
                type="submit"
                disabled={createMutation.isPending}
                className="w-full flex items-center justify-center px-4 py-2 bg-blue-600 text-white rounded-md font-medium hover:bg-blue-700 disabled:opacity-50 transition-colors"
              >
                {createMutation.isPending ? <Loader2 className="w-5 h-5 mr-2 animate-spin" /> : <Plus className="w-5 h-5 mr-2" />}
                Capture State
              </button>
            </div>
          </form>
        </div>

        {/* Compare Snapshots */}
        <div className="bg-white border border-gray-200 rounded-xl shadow-sm p-6 flex flex-col">
          <h2 className="text-lg font-bold text-gray-900 flex items-center mb-4">
            <GitCompare className="w-5 h-5 mr-2 text-indigo-500" />
            Compare Snapshots
          </h2>
          <form onSubmit={handleCompare} className="flex flex-col flex-1">
            <div className="flex gap-4 mb-4">
              <div className="flex-1">
                <label className="block text-sm font-medium text-gray-700 mb-1">Base Snapshot</label>
                <select
                  value={compare1}
                  onChange={(e) => setCompare1(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:ring-2 focus:ring-indigo-500"
                  required
                >
                  <option value="" disabled>Select...</option>
                  {snapshots?.map(s => (
                    <option key={`c1-${s.snapshot_id}`} value={s.snapshot_id}>{new Date(s.created_at).toLocaleString()}</option>
                  ))}
                </select>
              </div>
              <div className="flex-1">
                <label className="block text-sm font-medium text-gray-700 mb-1">Target Snapshot</label>
                <select
                  value={compare2}
                  onChange={(e) => setCompare2(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:ring-2 focus:ring-indigo-500"
                  required
                >
                  <option value="" disabled>Select...</option>
                  {snapshots?.map(s => (
                    <option key={`c2-${s.snapshot_id}`} value={s.snapshot_id}>{new Date(s.created_at).toLocaleString()}</option>
                  ))}
                </select>
              </div>
            </div>

            {compareMutation.isSuccess && compareMutation.data && (
              <div className="mb-4 bg-slate-50 p-4 rounded-lg border border-slate-200 flex justify-around text-center">
                <div>
                  <span className="block text-xs uppercase font-bold tracking-wider text-green-600 mb-1">Added Edges</span>
                  <span className="text-2xl font-bold text-green-700">+{compareMutation.data.added_edges}</span>
                </div>
                <div>
                  <span className="block text-xs uppercase font-bold tracking-wider text-red-600 mb-1">Removed Edges</span>
                  <span className="text-2xl font-bold text-red-700">-{compareMutation.data.removed_edges}</span>
                </div>
              </div>
            )}

            <div className="mt-auto">
              <button
                type="submit"
                disabled={compareMutation.isPending || !compare1 || !compare2 || compare1 === compare2}
                className="w-full flex items-center justify-center px-4 py-2 bg-indigo-600 text-white rounded-md font-medium hover:bg-indigo-700 disabled:opacity-50 transition-colors"
              >
                {compareMutation.isPending ? <Loader2 className="w-5 h-5 mr-2 animate-spin" /> : <GitCompare className="w-5 h-5 mr-2" />}
                Compare Delta
              </button>
            </div>
          </form>
        </div>
      </div>

      {/* Snapshots List */}
      <div className="mt-8 bg-white border border-gray-200 rounded-xl shadow-sm overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-200 bg-slate-50">
          <h2 className="text-lg font-bold text-gray-900">History Log</h2>
        </div>
        <div className="p-0">
          {isLoading ? (
             <div className="p-8 text-center text-gray-500"><Loader2 className="w-6 h-6 animate-spin mx-auto" /></div>
          ) : snapshots?.length === 0 ? (
             <div className="p-8 text-center text-gray-500">No snapshots found for this ecosystem.</div>
          ) : (
            <table className="w-full text-left text-sm whitespace-nowrap">
              <thead className="bg-white border-b border-gray-100 text-gray-500">
                <tr>
                  <th className="px-6 py-3 font-medium">Timestamp</th>
                  <th className="px-6 py-3 font-medium">Snapshot ID</th>
                  <th className="px-6 py-3 font-medium">Description</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {snapshots?.map(s => (
                  <tr key={s.snapshot_id} className="hover:bg-slate-50">
                    <td className="px-6 py-4 font-mono text-xs">
                      <div className="flex items-center">
                        <Calendar className="w-3.5 h-3.5 mr-2 text-gray-400" />
                        {new Date(s.created_at).toLocaleString()}
                      </div>
                    </td>
                    <td className="px-6 py-4 font-mono text-xs text-gray-500">{s.snapshot_id}</td>
                    <td className="px-6 py-4 text-gray-700 truncate max-w-xs">{s.description || '-'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  );
}
