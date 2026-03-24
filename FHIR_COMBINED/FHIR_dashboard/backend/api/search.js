// backend/api/search.js
const express = require('express');
const router = express.Router();
const elasticsearchService = require('../services/elasticsearch');

// GET /api/search/patients?q=query
router.get('/patients', async (req, res) => {
  try {
    const { q = '', limit = 20 } = req.query;
    
    if (!q || q.trim() === '') {
      // Return empty if no query
      return res.json([]);
    }

    const results = await elasticsearchService.searchPatients(q, parseInt(limit));
    res.json(results);
  } catch (error) {
    console.error('Error in patient search:', error);
    // Fallback to empty array if ElasticSearch fails
    res.json([]);
  }
});

// GET /api/search/observations?patient_id=123&q=glucose
router.get('/observations', async (req, res) => {
  try {
    const { patient_id, q = '', date_from, date_to, observation_type } = req.query;
    
    if (!patient_id) {
      return res.status(400).json({ error: 'patient_id is required' });
    }

    const filters = {};
    if (date_from) filters.dateFrom = date_from;
    if (date_to) filters.dateTo = date_to;
    if (observation_type) filters.observationType = observation_type;

    const results = await elasticsearchService.searchObservations(patient_id, q, filters);
    res.json(results);
  } catch (error) {
    console.error('Error in observations search:', error);
    res.status(500).json({ error: error.message });
  }
});

// GET /api/search/conditions?patient_id=123&q=diabetes
router.get('/conditions', async (req, res) => {
  try {
    const { patient_id, q = '', status } = req.query;
    
    if (!patient_id) {
      return res.status(400).json({ error: 'patient_id is required' });
    }

    const filters = {};
    if (status) filters.status = status;

    const results = await elasticsearchService.searchConditions(patient_id, q, filters);
    res.json(results);
  } catch (error) {
    console.error('Error in conditions search:', error);
    res.status(500).json({ error: error.message });
  }
});

// GET /api/search/notes?patient_id=123&q=query
router.get('/notes', async (req, res) => {
  try {
    const { patient_id, q = '', date_from, date_to } = req.query;
    
    const filters = {};
    if (date_from) filters.dateFrom = date_from;
    if (date_to) filters.dateTo = date_to;

    const results = await elasticsearchService.searchNotes(patient_id, q, filters);
    res.json(results);
  } catch (error) {
    console.error('Error in notes search:', error);
    res.status(500).json({ error: error.message });
  }
});

// GET /api/search/statistics?patient_id=123
router.get('/statistics', async (req, res) => {
  try {
    const { patient_id } = req.query;
    
    if (!patient_id) {
      return res.status(400).json({ error: 'patient_id is required' });
    }

    const stats = await elasticsearchService.getPatientStatistics(patient_id);
    res.json(stats);
  } catch (error) {
    console.error('Error getting statistics:', error);
    res.status(500).json({ error: error.message });
  }
});

module.exports = router;

