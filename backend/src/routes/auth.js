const express = require('express');
const bcrypt = require('bcryptjs');
const jwt = require('jsonwebtoken');
const db = require('../db');

const router = express.Router();

router.post('/login', async (req, res) => {
  const { rut, contraseña, tipoUsuario } = req.body; 

  if (!rut || !contraseña || !tipoUsuario) {
    return res.status(400).json({ error: 'RUT, contraseña y tipo de usuario son obligatorios' });
  }

  try {
    // 1. Verificar qué datos exactos llegan desde el frontend
    console.log('--- INTENTO DE LOGIN ---');
    console.log('Datos recibidos:', { rut, contraseña, tipoUsuario });

    // Determinar la tabla de rol según la opción seleccionada ('docente' -> 'profesor', 'apoderado' -> 'apoderado')
    const tablaRol = tipoUsuario === 'docente' ? 'profesor' : 'apoderado';
    const campoFK = tipoUsuario === 'docente' ? 'rut_profesor' : 'rut_apoderado';

    // Consulta con JOIN para autenticar credenciales y validar el rol simultáneamente
    const query = `
      SELECT u.rut_usuario, u.nombre, u.email, u.contrasenia
      FROM usuario u
      INNER JOIN ${tablaRol} r ON u.rut_usuario = r.${campoFK}
      WHERE u.rut_usuario = ?
    `;

    // 2. Verificar la consulta y lo que responde MySQL
    console.log('Query a ejecutar:', query);
    const [usuarios] = await db.query(query, [rut]);
    console.log('Usuario devuelto por MySQL:', usuarios);

    if (usuarios.length === 0) {
      console.log('❌ FALLO: La consulta devolvió 0 filas (RUT no existe o no tiene el rol asignado).');
      return res.status(401).json({ error: 'RUT o contraseña incorrectos, o no posee el rol seleccionado' });
    }

    const usuario = usuarios[0];
    
    // 3. Comparación en texto plano (TEMPORAL PARA DESARROLLO)
    const esCorrecta = (contraseña === usuario.contrasenia);
    console.log('¿La contraseña coincide (texto plano)?:', esCorrecta);

    if (!esCorrecta) {
      console.log('❌ FALLO: La contraseña ingresada no coincide con la guardada en BD.');
      return res.status(401).json({ error: 'RUT o contraseña incorrectos' });
    }

    // Generar token JWT de sesión usando rut_usuario
    const token = jwt.sign(
      { rut: usuario.rut_usuario, rol: tipoUsuario },
      process.env.JWT_SECRET,
      { expiresIn: '8h' }
    );

    console.log('✅ LOGIN EXITOSO para:', usuario.rut_usuario);

    // Respuesta adaptada a la estructura de la BD
    res.json({
      mensaje: 'Inicio de sesión exitoso',
      token,
      usuario: {
        rut: usuario.rut_usuario,
        nombre: usuario.nombre,
        email: usuario.email,
        rol: tipoUsuario
      }
    });

  } catch (error) {
    console.error('Error en /login:', error);
    res.status(500).json({ error: 'Error interno del servidor' });
  }
});

module.exports = router;