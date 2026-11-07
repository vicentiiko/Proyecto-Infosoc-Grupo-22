import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';

function PortalDocente() {
  const [docente, setDocente] = useState(null);
  const [cursos, setCursos] = useState([]);
  const [cargando, setCargando] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    const usuarioGuardado = localStorage.getItem('usuario');
    if (!usuarioGuardado) {
      navigate('/');
      return;
    }

    const usuarioData = JSON.parse(usuarioGuardado);
    setDocente(usuarioData);

    // Obtener cursos asignados desde el backend
    fetch(`http://localhost:3000/api/docentes/cursos/${usuarioData.rut}`)
      .then((res) => {
        if (!res.ok) throw new Error('Error al cargar cursos');
        return res.json();
      })
      .then((data) => {
        setCursos(data);
        setCargando(false);
      })
      .catch((err) => {
        console.error(err);
        setCargando(false);
      });
  }, [navigate]);

  const handleLogout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('usuario');
    navigate('/');
  };

  return (
    <div className="portal-container">
      {/* HEADER */}
      <header className="portal-header">
        <div className="header-brand">
          <div className="logo-placeholder">[Logo]</div>
          <h2>Escuela Especial Diversidad</h2>
        </div>
        <div className="header-user">
          <span>Profesor {docente?.nombre}</span>
          <button className="btn-logout" onClick={handleLogout}>
            Cerrar sesion
          </button>
        </div>
      </header>

      {/* CUERPO PRINCIPAL */}
      <div className="portal-body">
        {/* SIDEBAR */}
        <aside className="sidebar">
          <h3>MODULOS</h3>
          <button 
            className="btn-module" 
            onClick={() => navigate('/alumnos')} 
           >
             Alumnos
          </button>
          <button className="btn-module">Circulares</button>
          <button className="btn-module">Material</button>
        </aside>

        {/* PANEL PRINCIPAL */}
        <main className="main-content">
          <h1>PANEL PRINCIPAL</h1>

          {/* CURSOS ASIGNADOS */}
          <section className="dashboard-section">
            <h2>Mis cursos asignados</h2>
            <div className="section-box courses-box">
              {cargando ? (
                <p>Cargando cursos...</p>
              ) : cursos.length > 0 ? (
                cursos.map((curso) => (
                  <button 
                    key={curso.id_curso} 
                    className="btn-course"
                    onClick={() => alert(`Seleccionaste: ${curso.nivel}`)} // 2. Propiedad nivel
                  >
                    {curso.nivel} {/* 2. Propiedad nivel */}
                  </button>
                ))
              ) : (
                <p>No tienes cursos asignados.</p>
              )}
            </div>
          </section>

          {/* ACCIONES RÁPIDAS */}
          <section className="dashboard-section">
            <h2>Acciones rapidas</h2>
            <div className="section-box actions-box">
              <button className="btn-action">Crear Observacion</button>
              <button className="btn-action">Enviar Comunicado</button>
              <button className="btn-action">Cargar material</button>
            </div>
          </section>
        </main>
      </div>
    </div>
  );
}

export default PortalDocente;