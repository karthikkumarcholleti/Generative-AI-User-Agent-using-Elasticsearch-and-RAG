const express = require('express');
const db = require('../db');
const router = express.Router();

router.get('/', async (req, res) => {
  try {
    const { q, limit = 100 } = req.query;
    
    let query = `
      SELECT patient_id, CONCAT(given_name, ' ', family_name) AS name 
      FROM patients
    `;
    const params = [];
    
    // If search query provided, filter by name or patient_id
    if (q && q.trim()) {
      query += ` WHERE 
        CONCAT(given_name, ' ', family_name) LIKE ? 
        OR patient_id LIKE ?
      `;
      const searchTerm = `%${q.trim()}%`;
      params.push(searchTerm, searchTerm);
    }
    
    query += ` ORDER BY patient_id LIMIT ?`;
    params.push(parseInt(limit));
    
    const [rows] = await db.query(query, params);
    res.json(rows);
  } catch (err) {
    console.error('❌ Error fetching patients:', err.message);
    res.status(500).json({ error: 'Server error' });
  }
});

module.exports = router;
