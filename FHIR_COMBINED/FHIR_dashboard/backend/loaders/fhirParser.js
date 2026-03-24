// backend/loaders/fhirParser.js
const { v4: uuidv4 } = require('uuid');

function formatDateTime(input) {
  if (!input || typeof input !== 'string') return null;

  const isoMatch = input.match(/^(\d{4})(\d{2})(\d{2})(\d{2})(\d{2})(\d{2})([-+]\d{4})?$/);
  if (isoMatch) {
    const [, y, m, d, h, min, s] = isoMatch;
    const month = Number(m), day = Number(d);
    if (month < 1 || month > 12 || day < 1 || day > 31) return null;
    return `${y}-${m}-${d} ${h}:${min}:${s}`;
  }

  const dateOnly = input.match(/^(\d{4})(\d{2})(\d{2})$/);
  if (dateOnly) {
    const [, y, m, d] = dateOnly;
    const month = Number(m), day = Number(d);
    if (month < 1 || month > 12 || day < 1 || day > 31) return null;
    return `${y}-${m}-${d} 00:00:00`;
  }

  const parsed = Date.parse(input);
  if (!isNaN(parsed)) {
    return new Date(parsed).toISOString().slice(0, 19).replace('T', ' ');
  }

  return null;
}

function normalizeSourceType(value) {
  const v = String(value || '').toLowerCase();
  if (v === 'ccd' || v === 'ccda') return 'ccd';
  if (v === 'oru') return 'oru';
  if (v === 'adt') return 'adt';
  return null;
}

/**
 * Parse a FHIR Bundle into app-friendly rows.
 * @param {Object} bundle FHIR Bundle JSON
 * @param {Object} [ctx] optional context
 * @param {string} [ctx.filename] original file name (stored in DB)
 * @param {string} [ctx.sourceType] 'ccd'|'oru'|'adt' (stored in DB)
 */
function parseFHIRBundle(bundle, ctx = {}) {
  const filename = ctx.filename || null;
  const source_type = normalizeSourceType(ctx.sourceType);

  const data = {
    patient: null,
    observations: [],
    conditions: [],
    encounters: []
  };

  const patientAdmissionReasons = {};

  const admissionKeywords = [
    "pain", "fall", "chest", "shortness", "confusion", "bleeding", "fever", "anxiety", "injury",
    "chf", "depression", "overdose", "ams", "sob", "headache", "infection", "abuse",
    "suicidal", "xanax", "drug", "toxicity", "withdrawal", "delirium", "trauma", "fatigue", "nausea"
  ];

  for (const { resource } of bundle.entry || []) {
    if (!resource || !resource.resourceType) continue;

    switch (resource.resourceType) {
      case 'Patient': {
        if (!resource.id) continue;
        const address = resource.address?.[0] || {};

        data.patient = {
          id: resource.id,
          given_name: resource.name?.[0]?.given?.[0] || null,
          family_name: resource.name?.[0]?.family || null,
          birth_date: resource.birthDate || null,
          gender: resource.gender || null,
          city: address.city || null,
          state: address.state || null,
          postal_code: address.postalCode || null,
          // NEW: audit fields
          filename,
          source_type
        };
        break;
      }

      case 'Observation': {
        const patientRef = resource.subject?.reference?.split('/')?.[1];
        if (!patientRef) break;

        const id = resource.id || `auto_obs_${uuidv4()}`;
        const displayText = resource.code?.text || resource.code?.coding?.[0]?.display || null;

        if (displayText) {
          const lower = displayText.toLowerCase();
          if (
            !patientAdmissionReasons[patientRef] &&
            admissionKeywords.some(keyword => lower.includes(keyword))
          ) {
            patientAdmissionReasons[patientRef] = displayText;
          }
        }

        const obs = {
          id,
          patient_id: patientRef,
          code: resource.code?.coding?.[0]?.code || null,
          display: displayText,
          value_numeric: resource.valueQuantity?.value || null,
          value_string: resource.valueString || null,
          unit: resource.valueQuantity?.unit || null,
          effectiveDateTime: formatDateTime(resource.effectiveDateTime),
          status: resource.status || null,
          source: id.startsWith('auto_obs_') ? 'generated' : 'fhir',
          // NEW: audit fields
          filename,
          source_type
        };

        if (!obs.code) break;
        data.observations.push(obs);
        break;
      }

      case 'Condition': {
        const patientRef = resource.subject?.reference?.split('/')?.[1];
        if (!patientRef) break;

        const id = resource.id || `auto_cond_${uuidv4()}`;
        const cond = {
          id,
          patient_id: patientRef,
          code: resource.code?.coding?.[0]?.code || null,
          display:
            resource.code?.coding?.[0]?.display ||
            resource.code?.text ||
            resource.code?.coding?.[0]?.code ||
            'Unknown',
          clinical_status: resource.clinicalStatus?.coding?.[0]?.code || null,
          effectiveDateTime: formatDateTime(resource.recordedDate),
          source: id.startsWith('auto_cond_') ? 'generated' : 'fhir',
          // NEW: audit fields
          filename,
          source_type
        };

        if (!cond.code) break;
        data.conditions.push(cond);
        break;
      }

      case 'Encounter': {
        const patientRef = resource.subject?.reference?.split('/')?.[1];
        if (!patientRef) break;

        const id = resource.id || `auto_enc_${uuidv4()}`;

        const admission_reason =
          resource.reasonCode?.[0]?.text ||
          resource.note?.[0]?.text ||
          patientAdmissionReasons[patientRef] || null;

        const enc = {
          id,
          patient_id: patientRef,
          class_code: resource.class?.code || null,
          class_display: resource.class?.display || null,
          type_code: resource.type?.[0]?.coding?.[0]?.code || null,
          type_display: resource.type?.[0]?.coding?.[0]?.display || null,
          date: formatDateTime(resource.period?.start),
          admission_reason,
          source: id.startsWith('auto_enc_') ? 'generated' : 'fhir',
          // NEW: audit fields
          filename,
          source_type
        };

        data.encounters.push(enc);
        break;
      }
    }
  }

  return data;
}

module.exports = { parseFHIRBundle };
