import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

import { Layout } from './components/Layout';
import PackageSearch from './pages/PackageSearch';
import GraphViewer from './pages/GraphViewer';
import TopRisk from './pages/TopRisk';

// Global HTTP Cache Client
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      staleTime: 5 * 60 * 1000, // 5 minutes standard cache
    },
  },
});

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Layout>
          <Routes>
            <Route path="/" element={<PackageSearch />} />
            <Route path="/graph" element={<GraphViewer />} />
            <Route path="/analytics" element={<TopRisk />} />
          </Routes>
        </Layout>
      </BrowserRouter>
    </QueryClientProvider>
  );
}

export default App;
