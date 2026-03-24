const express = require('express');
const cors = require('cors');
const dotenv = require('dotenv');

dotenv.config();
const app = express();
app.use(cors());
app.use(express.json());

// Load route handlers
app.use('/api/patients', require('./api/patients'));
app.use('/api/observations', require('./api/observations'));
app.use('/api/conditions', require('./api/conditions'));
app.use('/api/encounters', require('./api/encounters'));
app.use('/api/stats', require('./api/stats'));
app.use('/api/metrics', require('./api/metrics'));
app.use('/api/dashboard', require('./api/dashboard'));
app.use('/api/locations', require('./api/locations'));
app.use('/api/search', require('./api/search')); // ElasticSearch search endpoints


const PORT = process.env.PORT || 5000;
app.listen(PORT, () => console.log(`🔥 API running on port ${PORT}`));
