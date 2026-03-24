// backend/api/metrics.js
const express = require('express');
const db = require('../db');
const path = require('path');
const { spawn } = require('child_process');
const router = express.Router();

const observationCodes = {
  heart_rate: '8867-4',
  resp_rate: '9279-1',
  bmi: '39156-5',
  bp_sys: '8480-6',
  bp_dia: '8462-4',
  oxygen: '59408-5',
};

// GET /api/metrics/patient-observations
router.get('/patient-observations', async (req, res) => {
  const { patient_id } = req.query;
  
  console.log('🔍 API Call - patient_id:', patient_id);
  console.log('🔍 Query params:', req.query);

  try {
    const results = {};

    for (const [key, code] of Object.entries(observationCodes)) {
      let query = `
        SELECT 
          patient_id,
          value_numeric AS value,
          effectiveDateTime AS timestamp
        FROM observations
        WHERE 
          code = ?
          AND effectiveDateTime IS NOT NULL
      `;

      const params = [code];

      if (patient_id && patient_id.trim() !== '') {
        query += ` AND patient_id = ?`;
        params.push(patient_id.trim());
      }

      query += ` ORDER BY effectiveDateTime`;

      console.log(`🔍 Query for ${key}:`, query);
      console.log(`🔍 Params for ${key}:`, params);

      const [rows] = await db.query(query, params);
      console.log(`🔍 Results for ${key}:`, rows.length, 'rows');
      
      // Additional filtering to ensure we only get the requested patient
      if (patient_id && patient_id.trim() !== '') {
        const filteredRows = rows.filter(row => row.patient_id === patient_id.trim());
        console.log(`🔍 Filtered results for ${key}:`, filteredRows.length, 'rows');
        results[key] = filteredRows;
      } else {
        results[key] = rows;
      }
    }

    console.log('🔍 Final results keys:', Object.keys(results));
    console.log('🔍 Total results:', JSON.stringify(results, null, 2).substring(0, 500) + '...');

    res.json(results);
  } catch (err) {
    console.error('❌ Error fetching patient observations:', err.message);
    res.status(500).json({ error: 'Failed to fetch patient observations' });
  }
});

router.get('/hotspot-models', async (_req, res) => {
  const pythonBinary = process.env.PYTHON_BIN || 'python3';
  const scriptPath = path.resolve(
    __dirname,
    '../services/ml-hotspots/scripts/compute_kmeans_metrics.py'
  );

  const child = spawn(pythonBinary, [scriptPath], {
    cwd: path.resolve(__dirname, '..'),
  });

  let stdout = '';
  let stderr = '';

  child.stdout.on('data', (data) => {
    stdout += data.toString();
  });

  child.stderr.on('data', (data) => {
    stderr += data.toString();
  });

  child.on('error', (error) => {
    console.error('❌ Failed to launch metrics script:', error.message);
    res.status(500).json({ error: 'Failed to compute model metrics' });
  });

  child.on('close', (code) => {
    if (code !== 0) {
      console.error('❌ Metrics script exited with code', code, stderr);
      return res
        .status(500)
        .json({ error: 'Metrics script failed', details: stderr.trim() });
    }

    try {
      const payload = JSON.parse(stdout.trim() || '{}');
      res.json(payload);
    } catch (err) {
      console.error('❌ Failed to parse metrics output:', err.message, stdout);
      res.status(500).json({ error: 'Invalid metrics output' });
    }
  });
});

module.exports = router;
