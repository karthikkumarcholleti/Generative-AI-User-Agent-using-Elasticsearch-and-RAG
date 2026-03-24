const express = require('express');
const db = require('../db');
const router = express.Router();

router.get('/', async (req, res) => {
  const { patient_id, code } = req.query;

  try {
    let sql = `SELECT * FROM observations WHERE 1=1`;
    const params = [];

    if (patient_id) {
      sql += ` AND patient_id = ?`;
      params.push(patient_id);
    }

    if (code) {
      sql += ` AND code = ?`;
      params.push(code);
    }

    const [rows] = await db.query(sql, params);
    res.json(rows);
  } catch (err) {
    console.error('❌ Error fetching observations:', err.message);
    res.status(500).json({ error: 'Server error' });
  }
});

module.exports = router;
