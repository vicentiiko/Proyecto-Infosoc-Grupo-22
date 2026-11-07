const express = require('express');
const db = require('../db');
const router = express.Router();

// Obtener cursos asignados a un docente
router.get('/cursos/:rut', async (req, res) => {
  const { rut } = req.params;

  try {
    const query = `
      SELECT c.id_curso, c.nivel, c.tamanio, pc.profesor_jefe
      FROM profesor_curso pc
      INNER JOIN curso c ON pc.id_curso = c.id_curso
      WHERE pc.rut_profesor = ?
    `;

    const [cursos] = await db.query(query, [rut]);
    res.json(cursos);
  } catch (error) {
    console.error('Error al obtener cursos:', error);
    res.status(500).json({ error: 'Error interno del servidor' });
  }
});

module.exports = router;