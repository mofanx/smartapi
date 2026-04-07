import { BrowserRouter, Routes, Route } from 'react-router-dom';
import Layout from './components/Layout';
import Dashboard from './pages/Dashboard';
import Cases from './pages/Cases';
import Execution from './pages/Execution';
import Reports from './pages/Reports';
import Environments from './pages/Environments';
import Mock from './pages/Mock';

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<Layout />}>
          <Route path="/" element={<Dashboard />} />
          <Route path="/cases" element={<Cases />} />
          <Route path="/execution" element={<Execution />} />
          <Route path="/reports" element={<Reports />} />
          <Route path="/environments" element={<Environments />} />
          <Route path="/mock" element={<Mock />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

export default App;
