// backend/api/locations.js

const express = require('express');
const router = express.Router();
const db = require('../db');

// GET /api/locations
router.get('/', async (req, res) => {
  try {
    const [locations] = await db.query(`
      SELECT 
        id,
        hospital_name,
        city,
        state,
        postal_code,
        latitude,
        longitude
      FROM hospital_locations
      WHERE latitude IS NOT NULL AND longitude IS NOT NULL
    `);

    res.json(locations);
  } catch (err) {
    console.error("❌ Error fetching hospital locations:", err);
    res.status(500).json({ error: 'Failed to fetch hospital locations' });
  }
});

module.exports = router;
