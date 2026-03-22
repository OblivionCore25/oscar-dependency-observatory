export default function GraphViewer() {
  return (
    <div className="h-full flex flex-col bg-slate-50 relative">
      <header className="absolute top-0 left-0 right-0 p-6 z-10 pointer-events-none">
        <h1 className="text-2xl font-bold text-gray-800 tracking-tight drop-shadow-sm">Graph Viewer</h1>
      </header>
      
      <div className="flex-1 w-full flex items-center justify-center border-l border-gray-200">
        <p className="text-gray-400">Cytoscape visualization placeholder...</p>
      </div>
    </div>
  );
}
