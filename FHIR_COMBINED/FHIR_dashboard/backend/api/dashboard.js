// routes/dashboard.js
const express = require('express');
const router = express.Router();
const db = require('../db');

// Comprehensive condition categorization based on your Python script
const CONDITION_CATEGORIES = {
  // Diabetes & Metabolic
  "307496006": { name: "Diabetes", category: "Metabolic", priority: "high" },
  "44054006": { name: "Type 2 Diabetes", category: "Metabolic", priority: "high" },
  
  // Cardiovascular
  "38341003": { name: "Hypertension", category: "Cardiovascular", priority: "high" },
  "56265001": { name: "Heart Disease", category: "Cardiovascular", priority: "high" },
  "25064002": { name: "Heart Failure", category: "Cardiovascular", priority: "high" },
  
  // Respiratory
  "195967001": { name: "Asthma", category: "Respiratory", priority: "high" },
  "13645005": { name: "COPD", category: "Respiratory", priority: "high" },
  "233604007": { name: "Chronic Obstructive Pulmonary Disease", category: "Respiratory", priority: "high" },
  
  // Musculoskeletal
  "3723001": { name: "Arthritis", category: "Musculoskeletal", priority: "medium" },
  "203082005": { name: "Fibromyalgia", category: "Musculoskeletal", priority: "medium" },
  "64859006": { name: "Osteoporosis", category: "Musculoskeletal", priority: "medium" },
  
  // Mental Health
  "35489007": { name: "Depression", category: "Mental Health", priority: "medium" },
  "197480006": { name: "Anxiety", category: "Mental Health", priority: "medium" },
  "55822004": { name: "Major Depression", category: "Mental Health", priority: "high" },
  
  // Neurological
  "26929004": { name: "Alzheimer's Disease", category: "Neurological", priority: "high" },
  "49049000": { name: "Parkinson's Disease", category: "Neurological", priority: "high" },
  "24700007": { name: "Multiple Sclerosis", category: "Neurological", priority: "high" },
  "230690007": { name: "Stroke", category: "Neurological", priority: "high" },
  
  // Metabolic & Endocrine
  "414916001": { name: "Obesity", category: "Metabolic", priority: "medium" },
  "709044004": { name: "Chronic Kidney Disease", category: "Renal", priority: "high" },
  
  // Oncology
  "363346000": { name: "Cancer", category: "Oncology", priority: "high" },
  
  // Additional common conditions
  "44054006": { name: "Diabetes Mellitus", category: "Metabolic", priority: "high" },
  "38341003": { name: "Essential Hypertension", category: "Cardiovascular", priority: "high" },
  "195967001": { name: "Bronchial Asthma", category: "Respiratory", priority: "high" },
  "13645005": { name: "Chronic Obstructive Pulmonary Disease", category: "Respiratory", priority: "high" }
};

// Comprehensive condition patterns for better matching
const CONDITION_PATTERNS = {
  // Diabetes & Metabolic variations
  "diabetes": { category: "Metabolic", priority: "high" },
  "diabetic": { category: "Metabolic", priority: "high" },
  "dm": { category: "Metabolic", priority: "high" },
  "diabetes mellitus": { category: "Metabolic", priority: "high" },
  "type 2 diabetes": { category: "Metabolic", priority: "high" },
  "type 1 diabetes": { category: "Metabolic", priority: "high" },
  
  // Hypertension variations
  "hypertension": { category: "Cardiovascular", priority: "high" },
  "htn": { category: "Cardiovascular", priority: "high" },
  "high blood pressure": { category: "Cardiovascular", priority: "high" },
  "essential hypertension": { category: "Cardiovascular", priority: "high" },
  
  // Heart conditions
  "heart": { category: "Cardiovascular", priority: "high" },
  "cardiac": { category: "Cardiovascular", priority: "high" },
  "coronary": { category: "Cardiovascular", priority: "high" },
  "myocardial": { category: "Cardiovascular", priority: "high" },
  "heart disease": { category: "Cardiovascular", priority: "high" },
  "heart failure": { category: "Cardiovascular", priority: "high" },
  "congestive heart failure": { category: "Cardiovascular", priority: "high" },
  
  // Respiratory conditions
  "copd": { category: "Respiratory", priority: "high" },
  "asthma": { category: "Respiratory", priority: "high" },
  "pneumonia": { category: "Respiratory", priority: "high" },
  "bronchitis": { category: "Respiratory", priority: "medium" },
  "bronchial asthma": { category: "Respiratory", priority: "high" },
  "chronic obstructive": { category: "Respiratory", priority: "high" },
  
  // Mental health
  "depression": { category: "Mental Health", priority: "medium" },
  "anxiety": { category: "Mental Health", priority: "medium" },
  "bipolar": { category: "Mental Health", priority: "high" },
  "ptsd": { category: "Mental Health", priority: "high" },
  "major depression": { category: "Mental Health", priority: "high" },
  "depressive": { category: "Mental Health", priority: "medium" },
  
  // Neurological
  "stroke": { category: "Neurological", priority: "high" },
  "epilepsy": { category: "Neurological", priority: "high" },
  "seizure": { category: "Neurological", priority: "high" },
  "dementia": { category: "Neurological", priority: "high" },
  "alzheimer": { category: "Neurological", priority: "high" },
  "parkinson": { category: "Neurological", priority: "high" },
  "multiple sclerosis": { category: "Neurological", priority: "high" },
  "ms": { category: "Neurological", priority: "high" },
  
  // Musculoskeletal
  "arthritis": { category: "Musculoskeletal", priority: "medium" },
  "osteoarthritis": { category: "Musculoskeletal", priority: "medium" },
  "rheumatoid": { category: "Musculoskeletal", priority: "high" },
  "fibromyalgia": { category: "Musculoskeletal", priority: "medium" },
  "osteoporosis": { category: "Musculoskeletal", priority: "medium" },
  "bone disease": { category: "Musculoskeletal", priority: "medium" },
  
  // Gastrointestinal
  "crohn": { category: "Gastrointestinal", priority: "high" },
  "colitis": { category: "Gastrointestinal", priority: "high" },
  "ibd": { category: "Gastrointestinal", priority: "high" },
  "ibs": { category: "Gastrointestinal", priority: "medium" },
  "gastroenteritis": { category: "Gastrointestinal", priority: "medium" },
  
  // Renal
  "kidney": { category: "Renal", priority: "high" },
  "renal": { category: "Renal", priority: "high" },
  "ckd": { category: "Renal", priority: "high" },
  "chronic kidney": { category: "Renal", priority: "high" },
  "nephropathy": { category: "Renal", priority: "high" },
  
  // Metabolic & Endocrine
  "obesity": { category: "Metabolic", priority: "medium" },
  "obese": { category: "Metabolic", priority: "medium" },
  "thyroid": { category: "Endocrine", priority: "medium" },
  "hypothyroid": { category: "Endocrine", priority: "medium" },
  "hyperthyroid": { category: "Endocrine", priority: "medium" },
  
  // Oncology
  "cancer": { category: "Oncology", priority: "high" },
  "tumor": { category: "Oncology", priority: "high" },
  "malignancy": { category: "Oncology", priority: "high" },
  "neoplasm": { category: "Oncology", priority: "high" },
  
  // Common ICD-10 patterns
  "e86": { category: "Metabolic", priority: "medium" }, // Dehydration
  "e87": { category: "Metabolic", priority: "medium" }, // Electrolyte imbalance
  "g43": { category: "Neurological", priority: "medium" }, // Migraine
  "k52": { category: "Gastrointestinal", priority: "medium" }, // Gastroenteritis
  "i10": { category: "Cardiovascular", priority: "high" }, // Essential hypertension
  "e11": { category: "Metabolic", priority: "high" }, // Type 2 diabetes
  "j44": { category: "Respiratory", priority: "high" }, // COPD
  "j45": { category: "Respiratory", priority: "high" }  // Asthma
};

function getMonths2024() {
  const months = {};
  for (let i = 1; i <= 12; i++) {
    months[`2024-${String(i).padStart(2, '0')}`] = 0;
  }
  return months;
}

function isoDayFromAny(dateInput) {
  if (!dateInput) return null;
  const d = new Date(dateInput);
  return isNaN(d.getTime()) ? null : d.toISOString().slice(0, 10); // YYYY-MM-DD
}

// Enhanced condition categorization function based on your Python script logic
function categorizeCondition(code, display, clinicalStatus = null) {
  const cleanCode = code?.trim() || '';
  const cleanDisplay = display?.trim() || '';
  const cleanStatus = clinicalStatus?.trim() || '';
  const searchText = `${cleanCode} ${cleanDisplay}`.toLowerCase();
  
  // First, try exact code match (SNOMED CT codes)
  if (CONDITION_CATEGORIES[cleanCode]) {
    // Adjust priority based on clinical status
    let priority = CONDITION_CATEGORIES[cleanCode].priority;
    if (cleanStatus === 'active' && priority === 'low') {
      priority = 'medium'; // Active conditions are more important
    } else if (cleanStatus === 'unknown' && priority === 'high') {
      priority = 'medium'; // Unknown status reduces priority slightly
    }
    
    return {
      name: CONDITION_CATEGORIES[cleanCode].name,
      category: CONDITION_CATEGORIES[cleanCode].category,
      priority: priority,
      status: cleanStatus || 'unknown',
      originalDisplay: cleanDisplay,
      code: cleanCode
    };
  }
  
  // Handle ICD-10 codes (like E86.0, G43.909, K52.9)
  if (cleanCode.match(/^[A-Z]\d{2}(\.\d+)?/)) {
    const icd10Pattern = cleanCode.substring(0, 3).toLowerCase();
    if (CONDITION_PATTERNS[icd10Pattern]) {
      // Adjust priority based on clinical status
      let priority = CONDITION_PATTERNS[icd10Pattern].priority;
      if (cleanStatus === 'active' && priority === 'low') {
        priority = 'medium';
      }
      
      return {
        name: cleanDisplay || cleanCode,
        category: CONDITION_PATTERNS[icd10Pattern].category,
        priority: priority,
        status: cleanStatus || 'unknown',
        originalDisplay: cleanDisplay,
        code: cleanCode
      };
    }
  }
  
  // Try pattern matching on display text
  for (const [pattern, info] of Object.entries(CONDITION_PATTERNS)) {
    if (searchText.includes(pattern)) {
      // Clean up the display name (remove ICD codes, clean formatting)
      let cleanName = cleanDisplay;
      if (cleanName) {
        // Remove ICD-10 codes from display names (e.g., "E86.0^Dehydration^ICD10" -> "Dehydration")
        cleanName = cleanName.replace(/\^[^^]*\^ICD10$/, '').replace(/^\w+\.\d+\^/, '');
        // Remove extra formatting
        cleanName = cleanName.replace(/\^/g, ' ').trim();
      }
      
      // Adjust priority based on clinical status
      let priority = info.priority;
      if (cleanStatus === 'active' && priority === 'low') {
        priority = 'medium';
      }
      
      return {
        name: cleanName || pattern.charAt(0).toUpperCase() + pattern.slice(1),
        category: info.category,
        priority: priority,
        status: cleanStatus || 'unknown',
        originalDisplay: cleanDisplay,
        code: cleanCode
      };
    }
  }
  
  // Handle common medical terms
  if (searchText.includes('acute') || searchText.includes('infection')) {
    return {
      name: cleanDisplay || 'Acute Condition',
      category: 'Acute',
      priority: 'low',
      status: cleanStatus || 'unknown',
      originalDisplay: cleanDisplay,
      code: cleanCode
    };
  }
  
  // Handle drug therapy and long-term conditions
  if (searchText.includes('drug therapy') || searchText.includes('long term')) {
    return {
      name: cleanDisplay || 'Long-term Drug Therapy',
      category: 'Therapy',
      priority: 'low',
      status: cleanStatus || 'unknown',
      originalDisplay: cleanDisplay,
      code: cleanCode
    };
  }
  
  // Handle weakness and general symptoms
  if (searchText.includes('weakness') || searchText.includes('fatigue')) {
    return {
      name: cleanDisplay || 'General Weakness',
      category: 'Symptoms',
      priority: 'low',
      status: cleanStatus || 'unknown',
      originalDisplay: cleanDisplay,
      code: cleanCode
    };
  }
  
  // Default fallback - use display name if available, otherwise code
  const finalName = cleanDisplay || cleanCode || 'Unknown Condition';
  return {
    name: finalName,
    category: 'Other',
    priority: 'low',
    status: cleanStatus || 'unknown',
    originalDisplay: cleanDisplay,
    code: cleanCode
  };
}

router.get('/:patientId', async (req, res) => {
  const patientId = req.params.patientId;

  try {
    let name = 'All Patients';
    const monthlyCounts = getMonths2024();

    let conditionQuery = `SELECT code, display, clinical_status FROM conditions`;
    // Used ONLY effectiveDateTime from observations
    let observationQuery = `
      SELECT patient_id, effectiveDateTime
      FROM observations
    `;
    const queryParams = [];

    if (patientId !== 'all') {
      const [[patient]] = await db.query(
        `SELECT CONCAT(given_name, ' ', family_name) AS name
         FROM patients
         WHERE patient_id = ?`,
        [patientId]
      );
      if (!patient) return res.status(404).json({ error: 'Patient not found' });

      name = patient.name;
      conditionQuery += ` WHERE patient_id = ?`;
      observationQuery += ` WHERE patient_id = ?`;
      queryParams.push(patientId);
    }

    const [conditions] = await db.query(conditionQuery, queryParams);
    const [observations] = await db.query(observationQuery, queryParams);

    // Enhanced condition processing
    const categorizedConditions = {};
    const conditionStats = {
      total: 0,
      byCategory: {},
      byPriority: { high: 0, medium: 0, low: 0 }
    };

    for (const cond of conditions) {
      const code = cond.code?.trim();
      const display = cond.display?.trim();
      const clinicalStatus = cond.clinical_status?.trim();
      
      if (!code && !display) continue;
      
      conditionStats.total++;
      
      const categorized = categorizeCondition(code, display, clinicalStatus);
      const category = categorized.category;
      const priority = categorized.priority;
      
      // Initialize category if not exists
      if (!categorizedConditions[category]) {
        categorizedConditions[category] = [];
        conditionStats.byCategory[category] = 0;
      }
      
      // Add condition to category
      categorizedConditions[category].push({
        name: categorized.name,
        code: code,
        originalDisplay: categorized.originalDisplay,
        priority: priority,
        status: categorized.status,
        category: category
      });
      
      conditionStats.byCategory[category]++;
      conditionStats.byPriority[priority]++;
    }

    // Convert to the format expected by frontend
    const groupedConditions = Object.entries(categorizedConditions).map(([category, conditions]) => ({
      category: category,
      conditions: conditions.sort((a, b) => {
        // Sort by priority first, then by name
        const priorityOrder = { high: 3, medium: 2, low: 1 };
        if (priorityOrder[a.priority] !== priorityOrder[b.priority]) {
          return priorityOrder[b.priority] - priorityOrder[a.priority];
        }
        return a.name.localeCompare(b.name);
      })
    })).sort((a, b) => {
      // Sort categories by total conditions (most conditions first)
      return b.conditions.length - a.conditions.length;
    });

    // ---- Hospital visit frequency using Observation dates ----
    const seenPatientDay = new Set();   // de-dup per patient per day
    const perPatientDays = new Map();   // pid -> Set('YYYY-MM-DD')

    for (const row of observations) {
      const pid = row.patient_id;
      if (!pid) continue;

      const day = isoDayFromAny(row.effectiveDateTime);
      if (!day) continue;

      const ym = day.slice(0, 7); // 'YYYY-MM'
      if (!ym.startsWith('2024')) continue;

      const key = `${pid}::${day}`;
      if (!seenPatientDay.has(key)) {
        seenPatientDay.add(key);
        monthlyCounts[ym] = (monthlyCounts[ym] || 0) + 1;
      }

      if (!perPatientDays.has(pid)) perPatientDays.set(pid, new Set());
      perPatientDays.get(pid).add(day);
    }

    // Average time between visits (in days)
    let totalGapDays = 0;
    let gapCount = 0;

    for (const daysSet of perPatientDays.values()) {
      const days = Array.from(daysSet).sort(); // 'YYYY-MM-DD' strings sort lexicographically
      for (let i = 1; i < days.length; i++) {
        const gap = (new Date(days[i]) - new Date(days[i - 1])) / (1000 * 60 * 60 * 24);
        if (gap > 0 && Number.isFinite(gap)) {
          totalGapDays += gap;
          gapCount++;
        }
      }
    }

    const avgTimeBetweenVisits = gapCount ? Number((totalGapDays / gapCount).toFixed(1)) : 0;

    // Kept for compatibility if UI expects it (placeholder)
    const avgLengthOfStay = seenPatientDay.size ? 1 : 0;

    res.json({
      patient_id: patientId,
      name,
      // Legacy format for backward compatibility
      conditions: Object.values(categorizedConditions).flat().map(c => c.name),
      comorbidities: [], // Will be handled by the new structure
      
      // New enhanced format
      groupedConditions: groupedConditions,
      conditionStats: conditionStats,
      
      monthly_visits: monthlyCounts,
      avg_time_between_visits: avgTimeBetweenVisits,
      avg_length_of_stay: avgLengthOfStay
    });

  } catch (err) {
    console.error("❌ Error in /api/dashboard/:patientId", err);
    res.status(500).json({ error: "Internal Server Error" });
  }
});

module.exports = router;

