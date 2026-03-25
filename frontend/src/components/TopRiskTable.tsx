import { useState } from 'react';
import { ArrowRight, ChevronLeft, ChevronRight } from 'lucide-react';
import { Link } from 'react-router-dom';
import type { TopRiskItem } from '../types/api';

interface TopRiskTableProps {
  items: TopRiskItem[];
}

export default function TopRiskTable({ items }: TopRiskTableProps) {
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);

  if (!items.length) {
    return (
      <div className="text-center py-12 bg-white rounded-xl shadow-sm border border-gray-100">
        <p className="text-gray-500">No high-risk dependencies found in this ecosystem.</p>
      </div>
    );
  }

  // Calculate pagination
  const totalPages = Math.ceil(items.length / pageSize);
  // Ensure current page is valid when items or page size changes
  const validCurrentPage = Math.min(currentPage, Math.max(1, totalPages));
  
  const startIndex = (validCurrentPage - 1) * pageSize;
  const paginatedItems = items.slice(startIndex, startIndex + pageSize);

  // Percentile thresholds for colour coding
  const getPercentileColor = (pct: number) => {
    if (pct >= 90) return { bar: 'bg-red-500', badge: 'text-red-700 bg-red-50 ring-red-200' };
    if (pct >= 70) return { bar: 'bg-amber-500', badge: 'text-amber-700 bg-amber-50 ring-amber-200' };
    return { bar: 'bg-blue-500', badge: 'text-blue-700 bg-blue-50 ring-blue-200' };
  };

  // Ordinal suffix helper
  const ordinal = (n: number) => {
    const s = ['th', 'st', 'nd', 'rd'];
    const v = n % 100;
    return n + (s[(v - 20) % 10] ?? s[v] ?? s[0]);
  };

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-200 flex flex-col">
      <div className="overflow-x-auto custom-scrollbar">
        <table className="w-full text-left text-sm whitespace-nowrap">
          <thead className="bg-slate-50 border-b border-gray-200 text-gray-600 font-semibold tracking-wide uppercase text-xs">
            <tr>
              <th className="px-6 py-4">Package</th>
              <th className="px-6 py-4">Version</th>
              <th className="px-6 py-4 w-64">
                Bottleneck Score
                <span className="font-normal text-gray-400 lowercase ml-1">(percentile rank)</span>
              </th>
              <th className="px-6 py-4 text-right">Fan-In <span className="font-normal text-gray-400 lowercase">(Ecosystem)</span></th>
              <th className="px-6 py-4 text-right">Fan-Out</th>
              <th className="px-6 py-4 text-right">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {paginatedItems.map((item) => {
              const colors = getPercentileColor(item.bottleneckPercentile);
              const pct = item.bottleneckPercentile;

              return (
                <tr key={item.id} className="hover:bg-slate-50 transition-colors group">
                  <td className="px-6 py-4">
                    <div className="font-bold text-gray-900">{item.name}</div>
                    <div className="text-xs text-gray-400 mt-0.5">{item.ecosystem}</div>
                  </td>
                  <td className="px-6 py-4 font-mono text-xs text-gray-600">
                    v{item.version}
                  </td>
                  <td className="px-6 py-4 min-w-[200px]">
                    <div className="flex flex-col gap-1.5">
                      <div className="flex items-center gap-2">
                        <span className={`text-xs font-semibold px-2 py-0.5 rounded-full ring-1 ring-inset tabular-nums ${colors.badge}`}>
                          {ordinal(Math.round(pct))} pct
                        </span>
                        <span className="text-[10px] text-gray-400 tabular-nums">
                          raw: {item.bottleneckScore.toLocaleString(undefined, { maximumFractionDigits: 0 })}
                        </span>
                      </div>
                      <div className="h-1.5 w-full bg-gray-100 rounded-full overflow-hidden">
                        <div
                          className={`h-full rounded-full ${colors.bar}`}
                          style={{ width: `${Math.max(2, pct)}%` }}
                        />
                      </div>
                    </div>
                  </td>
                  <td className="px-6 py-4 text-right tabular-nums">
                    <div className="flex flex-col items-end gap-1">
                      <div className="flex items-center gap-2">
                        <span className="text-gray-700">{item.fanIn.toLocaleString()}</span>
                        <span className="text-[10px] text-gray-400 uppercase tracking-wider">All Vers.</span>
                      </div>
                      <div className="flex items-center gap-2" title="Exact reverse-dependency resolution requires full ecosystem SemVer parsing.">
                        <span className="text-gray-400 font-medium text-xs">N/A*</span>
                        <span className="text-[10px] text-blue-500/80 bg-blue-50 px-1.5 py-0.5 rounded font-mono">v{item.version}</span>
                      </div>
                    </div>
                  </td>
                  <td className="px-6 py-4 text-right tabular-nums">
                    <div className="flex flex-col items-end gap-1">
                      <div className="flex items-center gap-2">
                        <span className="text-gray-700">{item.fanOut.toLocaleString()}</span>
                        <span className="text-[10px] text-gray-400 uppercase tracking-wider">All Vers.</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <span className="text-gray-500 font-medium">{item.versionFanOut.toLocaleString()}</span>
                        <span className="text-[10px] text-blue-500/80 bg-blue-50 px-1.5 py-0.5 rounded font-mono">v{item.version}</span>
                      </div>
                    </div>
                  </td>
                  <td className="px-6 py-4 text-right">
                    <Link
                      to={`/graph?ecosystem=${item.ecosystem}&package=${item.name}&version=${item.version}`}
                      className="inline-flex items-center justify-center p-2 text-blue-600 hover:text-blue-800 hover:bg-blue-50 rounded-lg transition-colors opacity-0 group-hover:opacity-100 focus:opacity-100"
                      title="View Graph"
                    >
                      <ArrowRight className="w-4 h-4" />
                    </Link>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      
      {/* Pagination Footer */}
      {totalPages > 1 && (
        <div className="px-6 py-4 border-t border-gray-200 flex items-center justify-between bg-white rounded-b-xl shrink-0">
          <div className="flex items-center gap-3">
            <span className="text-sm text-gray-500">Rows per page:</span>
            <select
              value={pageSize}
              onChange={(e) => {
                setPageSize(Number(e.target.value));
                setCurrentPage(1); // Reset to first page
              }}
              className="text-sm border-gray-300 rounded focus:ring-blue-500 focus:border-blue-500 py-1 pl-2 pr-6"
            >
              <option value={10}>10</option>
              <option value={20}>20</option>
              <option value={50}>50</option>
              <option value={100}>100</option>
            </select>
          </div>
          
          <div className="flex items-center gap-6">
            <span className="text-sm text-gray-700">
              Showing <span className="font-medium">{startIndex + 1}</span> to <span className="font-medium">{Math.min(startIndex + pageSize, items.length)}</span> of <span className="font-medium">{items.length}</span> results
            </span>
            
            <div className="flex items-center gap-2">
              <button
                onClick={() => setCurrentPage(prev => Math.max(1, prev - 1))}
                disabled={validCurrentPage === 1}
                className="p-1 rounded hover:bg-gray-100 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                title="Previous Page"
              >
                <ChevronLeft className="w-5 h-5 text-gray-600" />
              </button>
              <button
                onClick={() => setCurrentPage(prev => Math.min(totalPages, prev + 1))}
                disabled={validCurrentPage === totalPages}
                className="p-1 rounded hover:bg-gray-100 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                title="Next Page"
              >
                <ChevronRight className="w-5 h-5 text-gray-600" />
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
