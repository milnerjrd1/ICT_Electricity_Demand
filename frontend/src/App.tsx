import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BrowserRouter, Route, Routes } from 'react-router-dom';
import { Shell } from './components/layout/Shell';
import { DataQuality } from './pages/DataQuality';
import { DemandExplorer } from './pages/DemandExplorer';
import { Export } from './pages/Export';
import { MissionControl } from './pages/MissionControl';
import { ScenarioBuilder } from './pages/ScenarioBuilder';
import { ScenarioGuide } from './pages/ScenarioGuide';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      staleTime: 30_000,
    },
  },
});

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route element={<Shell />}>
            <Route path="/" element={<MissionControl />} />
            <Route path="/scenarios" element={<ScenarioBuilder />} />
            <Route path="/explorer" element={<DemandExplorer />} />
            <Route path="/quality" element={<DataQuality />} />
            <Route path="/export" element={<Export />} />
            <Route path="/guide" element={<ScenarioGuide />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  );
}
