// backend/api/stats.js
const express = require('express');
const db = require('../db');
const router = express.Router();

// 1. Summary Stats
router.get('/summary', async (req, res) => {
  try {
    const [[{ count: patients }]] = await db.query(`SELECT COUNT(*) AS count FROM patients`);
    const [[{ count: observations }]] = await db.query(`SELECT COUNT(*) AS count FROM observations`);
    const [[{ count: conditions }]] = await db.query(`SELECT COUNT(*) AS count FROM conditions`);
    const [[{ count: encounters }]] = await db.query(`SELECT COUNT(*) AS count FROM encounters`);
    res.json({ patients, observations, conditions, encounters });
  } catch (err) {
    res.status(500).json({ error: 'Failed to load summary stats.' });
  }
});

// 2. Average Age
router.get('/age', async (req, res) => {
  try {
    const [rows] = await db.query(`SELECT birth_date FROM patients WHERE birth_date IS NOT NULL`);
    const ages = rows.map(r => {
      const birthYear = new Date(r.birth_date).getFullYear();
      return new Date().getFullYear() - birthYear;
    });
    const avg = ages.length ? (ages.reduce((a, b) => a + b) / ages.length).toFixed(1) : 0;
    res.json({ averageAge: parseFloat(avg) });
  } catch (err) {
    res.status(500).json({ error: 'Failed to calculate average age.' });
  }
});

// 3. Gender Breakdown
router.get('/gender', async (req, res) => {
  try {
    const [rows] = await db.query(`SELECT gender, COUNT(*) AS count FROM patients GROUP BY gender`);
    const formatted = rows.map(r => ({ gender: r.gender || 'unknown', count: r.count }));
    res.json(formatted);
  } catch (err) {
    res.status(500).json({ error: 'Failed to load gender data.' });
  }
});

// 4. Chronic Conditions Frequency
// /routes/stats.js
const CHRONIC_CODES_MAP = {
  "307496006": "Diabetes",
  "38341003": "Hypertension",
  "195967001": "Asthma",
  "13645005": "COPD",
  "3723001": "Arthritis",
  "414916001": "Obesity",
  "35489007": "Depression",
  "197480006": "Anxiety",
  "56265001": "Heart disease",
  "363346000": "Cancer",
  "709044004": "Chronic kidney disease",
  "64859006": "Osteoporosis",
  "26929004": "Alzheimer's",
  "49049000": "Parkinson's",
  "24700007": "Multiple sclerosis",
  "203082005": "Fibromyalgia"
};
const CHRONIC_CODES = Object.keys(CHRONIC_CODES_MAP);

router.get('/chronic', async (req, res) => {
  try {
    if (CHRONIC_CODES.length === 0) return res.json([]);

    const placeholders = CHRONIC_CODES.map(() => '?').join(',');
    const sql = `
      SELECT code, COUNT(DISTINCT patient_id) AS patients
      FROM conditions
      WHERE code IN (${placeholders})
      GROUP BY code
    `;
    const [rows] = await db.query(sql, CHRONIC_CODES);

    // code -> count
    const counts = {};
    for (const r of rows || []) counts[String(r.code)] = Number(r.patients) || 0;

    // By default: return ONLY codes present in DB (non-zero), sorted desc
    let payload = Object.entries(counts)
      .map(([code, patients]) => ({
        code,
        condition: CHRONIC_CODES_MAP[code] || code,
        patients
      }))
      .sort((a, b) => b.patients - a.patients);

    if (req.query.includeZeros === '1') {
      payload = CHRONIC_CODES
        .map(code => ({
          code,
          condition: CHRONIC_CODES_MAP[code] || code,
          patients: counts[code] ?? 0
        }))
        .sort((a, b) => b.patients - a.patients);
    }

    res.json(payload);
  } catch (err) {
    console.error('Error fetching chronic condition stats:', err);
    res.status(500).json({ error: 'Failed to fetch chronic condition stats' });
  }
});

// Normalize long or inconsistent reasons
const REASON_LABELS_MAP = [
  { match: /humiliated or emotionally abused/i, label: "Abuse Screening" },
  { match: /adolescent depression screening/i, label: "Depression Screening" },
  { match: /urine drug screening/i, label: "Drug Screening" },
  { match: /fall risk/i, label: "Fall Risk" },
  { match: /xanax|overdose|drug|toxicity|withdrawal/i, label: "Drug Overdose" },
  { match: /\bchf\b|heart failure/i, label: "CHF" },
  { match: /shortness of breath|dyspnea|sob/i, label: "Shortness of Breath" },
  { match: /chest pain/i, label: "Chest Pain" },
  { match: /anemia|hemoglobin/i, label: "Anemia" },
  { match: /ams|altered mental/i, label: "AMS" },
  { match: /rib pain/i, label: "Rib Pain" },
  { match: /trauma|injury|fall/i, label: "Fall or Injury" }
];

// GET /api/stats/admissions
// Pure Year-1 logic: distinct patient counts per raw admission_reason, no mapping.
router.get('/admissions', async (req, res) => {
  try {
    const limit = Math.max(1, Math.min(parseInt(req.query.limit || '50', 10) || 50, 1000));

    // Pull patient and reason so we can de-dupe
    const [rows] = await db.query(`
      SELECT 
        patient_id,
        TRIM(COALESCE(admission_reason, '')) AS reason
      FROM encounters
    `);

    const seen = new Set();                  // to ensure patient counted once per reason
    const reasonCounts = Object.create(null); // { reason -> distinct patient count }

    for (const row of rows || []) {
      const pid = row.patient_id;
      if (!pid) continue;

      const reason = row.reason || 'Unknown';
      const key = `${pid}::${reason}`;
      if (seen.has(key)) continue;

      seen.add(key);
      reasonCounts[reason] = (reasonCounts[reason] || 0) + 1;
    }

    // Sort and limit
    const results = Object.entries(reasonCounts)
      .map(([reason, patients]) => ({ reason, patients }))
      .sort((a, b) => b.patients - a.patients)
      .slice(0, limit);

    res.json(results);
  } catch (err) {
    console.error('❌ Error fetching admission reasons:', err);
    res.status(500).json({ error: 'Failed to fetch admission reasons' });
  }
});






module.exports = router;
