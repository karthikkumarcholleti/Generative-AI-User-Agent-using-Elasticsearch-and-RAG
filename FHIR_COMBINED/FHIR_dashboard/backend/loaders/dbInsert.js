const db = require('../db');

// Normalize & validate source_type
function normalizeSourceType(st) {
  const v = String(st || '').trim().toLowerCase();
  return ['ccd', 'oru', 'adt'].includes(v) ? v : null;
}

// JS-level deduplication helper
function dedupeRecords(records, keyGen) {
  const seen = new Set();
  return records.filter(record => {
    const key = keyGen(record);
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });
}

/**
 * Context passed for every batch coming from a single file.
 * @typedef {{ filename?: string, sourceType?: 'ccd'|'oru'|'adt' }} SourceCtx
 */

// ---------------- Observations ----------------
async function insertObservations(observations, ctx = {}) {
  if (!observations?.length) return;

  const filename = ctx.filename ?? null;
  const source_type = normalizeSourceType(ctx.sourceType);

  // Ensure only patients that exist in patients table
  const patientIds = observations.map(o => o.patient_id);
  if (patientIds.length === 0) return;

  const [rows] = await db.query(
    `SELECT patient_id FROM patients WHERE patient_id IN (?)`,
    [patientIds]
  );
  const existingPatients = new Set(rows.map(r => r.patient_id));

  const filtered = observations.filter(o => existingPatients.has(o.patient_id));
  if (filtered.length === 0) return;

  const deduped = dedupeRecords(
    filtered,
    o => `${o.patient_id}_${o.code}_${o.effectiveDateTime}`
  );

  const values = deduped.map(o => [
    o.id,
    o.patient_id,
    o.code,
    o.display ?? null,
    o.value_numeric ?? null,
    o.value_string ?? null,
    o.unit ?? null,
    o.effectiveDateTime ?? null,
    o.status ?? null,
    o.source ?? null,
    filename,
    source_type
  ]);

  const sql = `
    INSERT IGNORE INTO observations
      (id, patient_id, code, display, value_numeric, value_string, unit, effectiveDateTime, status, source, filename, source_type)
    VALUES ?
  `;

  await db.query(sql, [values]);
}

// ---------------- Conditions ----------------
async function insertConditions(conditions, ctx = {}) {
  if (!conditions?.length) return;

  const filename = ctx.filename ?? null;
  const source_type = normalizeSourceType(ctx.sourceType);

  const patientIds = conditions.map(c => c.patient_id);
  if (patientIds.length === 0) return;

  const [rows] = await db.query(
    `SELECT patient_id FROM patients WHERE patient_id IN (?)`,
    [patientIds]
  );
  const existingPatients = new Set(rows.map(r => r.patient_id));

  const filtered = conditions.filter(c => existingPatients.has(c.patient_id));
  if (filtered.length === 0) return;

  const deduped = dedupeRecords(
    filtered,
    c => `${c.patient_id}_${c.code}_${c.effectiveDateTime}`
  );

  const values = deduped.map(c => [
    c.id,
    c.patient_id,
    c.code,
    c.display ?? null,
    c.clinical_status ?? null,
    c.effectiveDateTime ?? null,
    c.source ?? null,
    filename,
    source_type
  ]);

  const sql = `
    INSERT IGNORE INTO conditions
      (id, patient_id, code, display, clinical_status, effectiveDateTime, source, filename, source_type)
    VALUES ?
  `;

  await db.query(sql, [values]);
}

// ---------------- Encounters ----------------
async function insertEncounters(encounters, ctx = {}) {
  if (!encounters?.length) return;

  const filename = ctx.filename ?? null;
  const source_type = normalizeSourceType(ctx.sourceType);

  const patientIds = encounters.map(e => e.patient_id);
  if (patientIds.length === 0) return;

  const [rows] = await db.query(
    `SELECT patient_id FROM patients WHERE patient_id IN (?)`,
    [patientIds]
  );
  const existingPatients = new Set(rows.map(r => r.patient_id));

  const filtered = encounters.filter(e => existingPatients.has(e.patient_id));
  if (filtered.length === 0) return;

  const deduped = dedupeRecords(
    filtered,
    e => `${e.patient_id}_${e.date}_${e.admission_reason || ''}`
  );

  const values = deduped.map(e => [
    e.id,
    e.patient_id,
    e.class_code ?? null,
    e.class_display ?? null,
    e.type_code ?? null,
    e.type_display ?? null,
    e.date ?? null,
    e.source ?? null,
    e.admission_reason ?? null,
    filename,
    source_type
  ]);

  const sql = `
    INSERT IGNORE INTO encounters
      (id, patient_id, class_code, class_display, type_code, type_display, date, source, admission_reason, filename, source_type)
    VALUES ?
  `;

  await db.query(sql, [values]);
}

// ---------------- Patients ----------------
async function insertPatient(patient, ctx = {}) {
  if (!patient || !patient.id) return;

  const filename = ctx.filename ?? null;
  const source_type = normalizeSourceType(ctx.sourceType);

  // Defensive: skip ORU demographics
  if (source_type === 'oru') {
    console.log(`ℹ️ Skipping ORU demographics for patient ${patient.id}`);
    return;
  }

  let location_id = null;

  if (patient.city && patient.state && patient.postal_code) {
    const [existing] = await db.query(
      `SELECT id FROM hospital_locations WHERE city = ? AND state = ? AND postal_code = ?`,
      [patient.city, patient.state, patient.postal_code]
    );

    if (existing.length > 0) {
      location_id = existing[0].id;
    } else {
      const hospitalName = `${patient.city} General Hospital`;
      const result = await db.execute(
        `INSERT INTO hospital_locations (city, state, postal_code, hospital_name, latitude, longitude)
         VALUES (?, ?, ?, ?, 0, 0)`,
        [patient.city, patient.state, patient.postal_code, hospitalName]
      );
      location_id = result[0].insertId;
    }
  }

  if (source_type === 'adt') {
    // Always insert or update for ADT
    const sql = `
      INSERT INTO patients
        (patient_id, given_name, family_name, birth_date, gender, city, state, postal_code, location_id, filename, source_type)
      VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
      ON DUPLICATE KEY UPDATE
        given_name   = VALUES(given_name),
        family_name  = VALUES(family_name),
        birth_date   = VALUES(birth_date),
        gender       = VALUES(gender),
        city         = VALUES(city),
        state        = VALUES(state),
        postal_code  = VALUES(postal_code),
        location_id  = VALUES(location_id),
        filename     = VALUES(filename),
        source_type  = VALUES(source_type)
    `;
    await db.execute(sql, [
      patient.id,
      patient.given_name ?? null,
      patient.family_name ?? null,
      patient.birth_date ?? null,
      patient.gender ?? null,
      patient.city ?? null,
      patient.state ?? null,
      patient.postal_code ?? null,
      location_id,
      filename,
      source_type
    ]);
  } else if (source_type === 'ccd') {
    // CCD: insert only if patient does not exist
    const [exists] = await db.query(
      `SELECT patient_id FROM patients WHERE patient_id = ?`,
      [patient.id]
    );
    if (exists.length === 0) {
      const sql = `
        INSERT INTO patients
          (patient_id, given_name, family_name, birth_date, gender, city, state, postal_code, location_id, filename, source_type)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
      `;
      await db.execute(sql, [
        patient.id,
        patient.given_name ?? null,
        patient.family_name ?? null,
        patient.birth_date ?? null,
        patient.gender ?? null,
        patient.city ?? null,
        patient.state ?? null,
        patient.postal_code ?? null,
        location_id,
        filename,
        source_type
      ]);
    } else {
      console.log(`ℹ️ CCD patient ${patient.id} already exists, skipping demographics`);
    }
  }
}

module.exports = {
  insertPatient,
  insertObservations,
  insertConditions,
  insertEncounters
};
