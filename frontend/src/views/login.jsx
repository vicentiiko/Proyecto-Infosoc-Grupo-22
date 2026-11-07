import { useState } from 'react';
import { useNavigate } from 'react-router-dom';

function Login() {
  const [rut, setRut] = useState('');
  const [contraseña, setContraseña] = useState('');
  const [tipoUsuario, setTipoUsuario] = useState('docente');
  const [error, setError] = useState('');

  const navigate = useNavigate(); // Hook para la redirección

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');

    try {
      const response = await fetch('http://localhost:3000/api/login', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ 
          rut: rut.trim(), 
          contraseña, 
          tipoUsuario 
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || 'Error al iniciar sesión');
      }

      // 1. Almacenar sesión en localStorage
      localStorage.setItem('token', data.token);
      localStorage.setItem('usuario', JSON.stringify(data.usuario));

      // 2. Redireccionar según el rol recibido
      if (data.usuario.rol === 'docente') {
        navigate('/portal-docente');
      } else {
        navigate('/portal-apoderado');
      }
      
    } catch (err) {
      setError(err.message);
    }
  };

  return (
    <div className="login-container">
      <div className="tabs">
        <button 
          type="button"
          className={tipoUsuario === 'docente' ? 'active' : ''} 
          onClick={() => setTipoUsuario('docente')}
        >
          Docentes
        </button>
        <button 
          type="button"
          className={tipoUsuario === 'apoderado' ? 'active' : ''} 
          onClick={() => setTipoUsuario('apoderado')}
        >
          Apoderados
        </button>
      </div>

      <form onSubmit={handleSubmit}>
        <input
          type="text"
          placeholder="RUT (ej: 92000001-1)"
          value={rut}
          onChange={(e) => setRut(e.target.value)}
          required
        />
        <input
          type="password"
          placeholder="Contraseña"
          value={contraseña}
          onChange={(e) => setContraseña(e.target.value)}
          required
        />
        {error && <p style={{ color: 'red' }}>{error}</p>}
        <button type="submit">Ingreso</button>
      </form>
    </div>
  );
}

export default Login;