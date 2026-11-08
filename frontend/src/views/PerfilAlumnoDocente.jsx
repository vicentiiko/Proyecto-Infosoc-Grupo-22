import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';

function PerfilAlumnoDocente() {
  const { rut } = useParams();
  const navigate = useNavigate();
  const [perfil, setPerfil] = useState(null);
  const [docente, setDocente] = useState(null);
  const [cargando, setCargando] = useState(true);

  useEffect(() => {
    const usuarioGuardado = localStorage.getItem('usuario');
    if (!usuarioGuardado) {
      navigate('/');
      return;
    }
    setDocente(JSON.parse(usuarioGuardado));

    fetch(`http://localhost:3000/api/alumnos/perfil/${rut}`)
      .then((res) => {
        if (!res.ok) throw new Error('Error al obtener perfil');
        return res.json();
      })
      .then((data) => {
        setPerfil(data);
        setCargando(false);
      })
      .catch((err) => {
        console.error(err);
        setCargando(false);
      });
  }, [rut, navigate]);

  if (cargando) {
    return <div style={{ padding: '20px', textAlign: 'center' }}>Cargando perfil...</div>;
  }

  return (
    <div className="perfil-container">
      {/* HEADER */}
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

      {/* CONTENIDO PRINCIPAL DEL PERFIL */}
      <main className="perfil-content">
        <div className="perfil-card">
          {/* HEADER DEL ALUMNO */}
          <div className="student-header-bar">
            <h2>{perfil?.nombre_alumno}</h2>
            <span className="student-course">{perfil?.curso}</span>
          </div>

          <div className="perfil-body-box">
            {/* SECCIÓN CONTACTOS */}
            <section className="perfil-section">
              <h3>Contactos</h3>
              <div className="contact-list">
                {perfil?.contactos && perfil.contactos.length > 0 ? (
                  perfil.contactos.map((contacto, idx) => (
                    <div key={idx} className="contact-row">
                      <span className="field-box">{contacto.nombre_apoderado}</span>
                      <span className="field-box">{contacto.parentesco}</span>
                      <span className="field-box">{contacto.telefono}</span>
                      {contacto.es_principal && <span className="badge-principal">Principal</span>}
                    </div>
                  ))
                ) : (
                  <p>No tiene contactos registrados.</p>
                )}
              </div>
            </section>

            {/* SECCIÓN OBSERVACIONES */}
            <section className="perfil-section">
              <div className="obs-header">
                <h3>Observaciones</h3>
                <button className="btn-crear-obs">Crear</button>
              </div>
              <div className="obs-list">
                {perfil?.observaciones && perfil.observaciones.length > 0 ? (
                  perfil.observaciones.map((obs) => (
                    <div key={obs.id_observacion} className="obs-box">
                      {obs.contenido}
                    </div>
                  ))
                ) : (
                  <div className="obs-box">Sin observaciones registradas.</div>
                )}
              </div>
            </section>
          </div>
        </div>
      </main>

      {/* FOOTER */}
      <footer className="footer-alumnos">
        <button className="btn-volver" onClick={() => navigate('/alumnos')}>
          Volver atras
        </button>
      </footer>
    </div>
  );
}

export default PerfilAlumnoDocente;