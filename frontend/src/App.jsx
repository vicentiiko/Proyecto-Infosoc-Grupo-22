import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import Login from './views/login';
import PortalDocente from './views/PortalDocente'; 
import ListaAlumnos from './views/ListaAlumnos';

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<Login />} />
        <Route path="/portal-docente" element={<PortalDocente />} />
        <Route path="/alumnos" element={<ListaAlumnos />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Router>
  );
}

export default App;