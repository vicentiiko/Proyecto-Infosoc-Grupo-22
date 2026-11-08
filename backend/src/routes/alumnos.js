const express = require('express');
const db = require('../db');
const router = express.Router();

// 1. Obtener todos los alumnos pertenecientes a un curso específico (por id_curso)
router.get('/curso/:id_curso', async (req, res) => {
  const { id_curso } = req.params;

  try {
    const query = `
      SELECT 
        a.rut_alumno,
        a.nombre AS nombre_alumno,
        c.nivel AS curso,
        u_apod.nombre AS nombre_apoderado,
        apod.telefono AS contacto_apoderado,
        aa.parentesco
      FROM alumno a
      INNER JOIN curso c ON a.id_curso = c.id_curso
      LEFT JOIN alumno_apoderado aa ON a.rut_alumno = aa.rut_alumno AND aa.es_principal = TRUE
      LEFT JOIN apoderado apod ON aa.rut_apoderado = apod.rut_apoderado
      LEFT JOIN usuario u_apod ON apod.rut_apoderado = u_apod.rut_usuario
      WHERE a.id_curso = ?
      ORDER BY a.nombre ASC
    `;

    const [alumnos] = await db.query(query, [id_curso]);
    res.json(alumnos);
  } catch (error) {
    console.error('Error al obtener alumnos del curso:', error);
    res.status(500).json({ error: 'Error al consultar alumnos del curso' });
  }
});

// 2. Obtener los alumnos de TODOS los cursos asignados a un profesor (por rut_profesor)
router.get('/profesor/:rut', async (req, res) => {
  const { rut } = req.params;

  try {
    const query = `
      SELECT 
        a.rut_alumno,
        a.nombre AS nombre_alumno,
        c.nivel AS curso,
        u_prof.nombre AS profesor_asignado,
        u_apod.nombre AS nombre_apoderado,
        apod.telefono AS contacto_apoderado
      FROM profesor_curso pc
      INNER JOIN curso c ON pc.id_curso = c.id_curso
      INNER JOIN alumno a ON a.id_curso = c.id_curso
      INNER JOIN usuario u_prof ON pc.rut_profesor = u_prof.rut_usuario
      LEFT JOIN alumno_apoderado aa ON a.rut_alumno = aa.rut_alumno AND aa.es_principal = TRUE
      LEFT JOIN apoderado apod ON aa.rut_apoderado = apod.rut_apoderado
      LEFT JOIN usuario u_apod ON apod.rut_apoderado = u_apod.rut_usuario
      WHERE pc.rut_profesor = ?
      ORDER BY c.id_curso, a.nombre ASC
    `;

    const [alumnos] = await db.query(query, [rut]);
    res.json(alumnos);
  } catch (error) {
    console.error('Error al obtener alumnos del profesor:', error);
    res.status(500).json({ error: 'Error al consultar alumnos asignados' });
  }
});

router.get('/perfil/:rut', async (req, res) => {
  const { rut } = req.params;

  try {
    // A. Consultar alumno y su curso
    const [alumnoRows] = await db.query(
      `SELECT a.rut_alumno, a.nombre AS nombre_alumno, c.nivel AS curso
       FROM alumno a
       INNER JOIN curso c ON a.id_curso = c.id_curso
       WHERE a.rut_alumno = ?`,
      [rut]
    );

    if (alumnoRows.length === 0) {
      return res.status(404).json({ error: 'Alumno no encontrado' });
    }

    const alumno = alumnoRows[0];

    // B. Consultar contactos de apoderados (desde alumno_apoderado, apoderado y usuario)
    const [apoderados] = await db.query(
      `SELECT u.nombre AS nombre_apoderado, aa.parentesco, ap.telefono, aa.es_principal
       FROM alumno_apoderado aa
       INNER JOIN apoderado ap ON aa.rut_apoderado = ap.rut_apoderado
       INNER JOIN usuario u ON ap.rut_apoderado = u.rut_usuario
       WHERE aa.rut_alumno = ?
       ORDER BY aa.es_principal DESC`,
      [rut]
    );

    // C. Consultar observaciones del alumno
    const [observaciones] = await db.query(
      `SELECT o.id_observacion, o.contenido
       FROM observacion o
       WHERE o.rut_alumno = ?`,
      [rut]
    );

    res.json({
      ...alumno,
      contactos: apoderados,
      observaciones: observaciones
    });
  } catch (error) {
    console.error('Error al obtener perfil del alumno:', error);
    res.status(500).json({ error: 'Error al consultar perfil del alumno' });
  }
});

module.exports = router;