import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';

function ListaAlumnos() {
  const [alumnos, setAlumnos] = useState([]);
  const [docente, setDocente] = useState(null);
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

    fetch(`http://localhost:3000/api/alumnos/profesor/${usuarioData.rut}`)
      .then((res) => {
        if (!res.ok) throw new Error('Error al consultar alumnos');
        return res.json();
      })
      .then((data) => {
        setAlumnos(data);
        setCargando(false);
      })
      .catch((err) => {
        console.error(err);
        setCargando(false);
      });
  }, [navigate]);

  return (
    <div className="alumnos-container">
      {/* Header */}
      <header className="portal-header">
        <div className="header-brand">
          <div className="logo-placeholder">[Logo]</div>
          <h2>Escuela Especial Diversidad</h2>
        </div>
        <div className="header-user">
          <span>Profesor {docente?.nombre}</span>
          <button className="btn-logout" onClick={() => {
            localStorage.clear();
            navigate('/');
          }}>
            Cerrar sesion
          </button>
        </div>
      </header>

      {/* Título */}
      <h1 className="title-alumnos">ALUMNOS</h1>

      {/* Tabla de Alumnos */}
      <div className="table-wrapper">
        <table className="alumnos-table">
          <thead>
            <tr>
              <th>Nombre</th>
              <th>Curso</th>
              <th>Profesor asignado</th>
              <th>Contacto P</th>
            </tr>
          </thead>
          <tbody>
            {cargando ? (
              <tr><td colSpan="4">Cargando alumnos...</td></tr>
            ) : alumnos.length > 0 ? (
              alumnos.map((alum, idx) => (
                <tr key={idx}>
                  <td>
                    <span className="badge-name" 
                      style={{ cursor: 'pointer' }}
                      onClick={() => navigate(`/alumnos/perfil/${alum.rut_alumno}`)}
                    >
                      {alum.nombre_alumno}</span>
                  </td>
                  <td>{alum.curso}</td>
                  <td>{alum.profesor_asignado}</td>
                  <td>{alum.contacto_apoderado || 'Sin registro'}</td>
                </tr>
              ))
            ) : (
              <tr><td colSpan="4">No hay alumnos asignados a tus cursos.</td></tr>
            )}
          </tbody>
        </table>
      </div>

      {/* Botón Volver */}
      <footer className="footer-alumnos">
        <button className="btn-volver" onClick={() => navigate('/portal-docente')}>
          Volver al menu
        </button>
      </footer>
    </div>
  );
}

export default ListaAlumnos;