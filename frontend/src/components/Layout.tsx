import type { ReactNode } from 'react';
import { NavLink } from 'react-router-dom';
import { Network, AlertTriangle, FlaskConical, Search } from 'lucide-react';

interface LayoutProps {
  children: ReactNode;
}

export function Layout({ children }: LayoutProps) {
  return (
    <div className="flex bg-gray-50 h-screen w-screen overflow-hidden text-gray-900 font-sans">
      {/* Sidebar Navigation */}
      <aside className="w-64 bg-white border-r border-gray-200 flex flex-col shrink-0">
        <div className="h-16 flex items-center px-5 border-b border-gray-200 gap-3">
          <img src="/oscar-logo.png" alt="OSCAR Logo" className="w-8 h-8 shrink-0" />
          <div className="leading-tight">
            <span className="font-bold text-sm tracking-tight text-gray-900 block">OSCAR</span>
            <span className="text-[10px] text-gray-500 tracking-wide block">Dependency Graph Observatory</span>
          </div>
        </div>
        
        <nav className="flex-1 py-6 px-4 space-y-2">
          <NavLink 
            to="/" 
            className={({ isActive }) => 
              `flex items-center px-4 py-3 rounded-md transition-colors ${
                isActive ? 'bg-blue-50 text-blue-700 font-medium' : 'text-gray-600 hover:bg-gray-100'
              }`
            }
          >
            <Search className="w-5 h-5 mr-3" />
            Package Search
          </NavLink>
          
          <NavLink 
            to="/graph" 
            className={({ isActive }) => 
              `flex items-center px-4 py-3 rounded-md transition-colors ${
                isActive ? 'bg-blue-50 text-blue-700 font-medium' : 'text-gray-600 hover:bg-gray-100'
              }`
            }
          >
            <Network className="w-5 h-5 mr-3" />
            Graph Viewer
          </NavLink>
          
          <NavLink 
            to="/analytics" 
            className={({ isActive }) => 
              `flex items-center px-4 py-3 rounded-md transition-colors ${
                isActive ? 'bg-blue-50 text-blue-700 font-medium' : 'text-gray-600 hover:bg-gray-100'
              }`
            }
          >
            <AlertTriangle className="w-5 h-5 mr-3" />
            Top Risk
          </NavLink>

          <NavLink
            to="/snapshots"
            className={({ isActive }) =>
              `flex items-center px-4 py-3 rounded-md transition-colors ${
                isActive ? 'bg-indigo-50 text-indigo-700 font-medium' : 'text-gray-600 hover:bg-gray-100'
              }`
            }
          >
            <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="w-5 h-5 mr-3 lucide lucide-history"><path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"/><path d="M3 3v5h5"/><path d="M12 7v5l4 2"/></svg>
            Snapshots
          </NavLink>

          <NavLink 
            to="/methods" 
            className={({ isActive }) => 
              `flex items-center px-4 py-3 rounded-md transition-colors ${
                isActive ? 'bg-purple-50 text-purple-700 font-medium' : 'text-gray-600 hover:bg-gray-100'
              }`
            }
          >
            <FlaskConical className="w-5 h-5 mr-3" />
            Method Observatory
          </NavLink>
        </nav>
      </aside>

      {/* Main Content Area */}
      <main className="flex-1 flex flex-col min-w-0 h-full overflow-hidden">
        {children}
      </main>
    </div>
  );
}
