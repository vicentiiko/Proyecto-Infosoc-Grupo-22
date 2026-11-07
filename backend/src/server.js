const express = require('express');
const cors = require('cors');
require('dotenv').config();

const authRoutes = require('./routes/auth');
const app = express();

app.use(cors());
app.use(express.json());

app.use('/api', authRoutes);

app.get('/', (req, res) => {
    res.json({ mensaje: 'API corriendo correctamente' });
});

const docentesRoutes = require('./routes/docentes');
app.use('/api/docentes', docentesRoutes);

const alumnosRoutes = require('./routes/alumnos');
app.use('/api/alumnos', alumnosRoutes);

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
    console.log(`Servidor corriendo en http://localhost:${PORT}`);
});