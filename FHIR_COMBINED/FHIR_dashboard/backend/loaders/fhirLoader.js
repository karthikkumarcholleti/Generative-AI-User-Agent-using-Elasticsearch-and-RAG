const fs = require('fs');
const path = require('path');
const db = require('../db');
const { parseFHIRBundle } = require('./fhirParser');
const {
  insertPatient,
  insertObservations,
  insertConditions,
  insertEncounters
} = require('./dbInsert');

const DATA_FOLDER = path.resolve(__dirname, '../data/Converted_Data');

// Infer source_type from parent folder name instead of filename
function inferSourceType(filePath) {
  const folder = path.basename(path.dirname(filePath)).toLowerCase();
  if (folder.includes('ccd') || folder.includes('ccda')) return 'ccd';
  if (folder.includes('oru') || folder.includes('lab')) return 'oru';
  if (folder.includes('adt')) return 'adt';
  return 'unknown';
}

// Recursively collect all JSON files from a directory
function getAllJsonFiles(dir) {
  let results = [];
  const list = fs.readdirSync(dir);

  list.forEach(file => {
    const filePath = path.join(dir, file);
    const stat = fs.statSync(filePath);

    if (stat && stat.isDirectory()) {
      results = results.concat(getAllJsonFiles(filePath)); // recurse into subfolders
    } else if (filePath.endsWith('.json')) {
      results.push(filePath);
    }
  });

  return results;
}

// Parse & load one FHIR file
async function loadFHIRFromFile(filePath) {
  try {
    const fileOnly = path.basename(filePath);
    const sourceType = inferSourceType(filePath);
    const ctx = { filename: fileOnly, sourceType };

    console.log(`📂 Loading file: ${fileOnly} (source: ${sourceType})`);
    const rawData = fs.readFileSync(filePath, 'utf-8');
    const bundle = JSON.parse(rawData);
    const parsed = parseFHIRBundle(bundle);

    // Patients: insert/update based on source type rules
    if (parsed.patient) {
      if (sourceType === 'adt') {
        await insertPatient(parsed.patient, ctx); // always insert/update
      } else if (sourceType === 'ccd') {
        // only insert if not already in patients
        const [existing] = await db.query(
          `SELECT patient_id FROM patients WHERE patient_id = ?`,
          [parsed.patient.id]
        );
        if (existing.length === 0) {
          await insertPatient(parsed.patient, ctx);
        } else {
          console.log(`ℹ️ Skipping CCD demographics for existing patient ${parsed.patient.id}`);
        }
      } else if (sourceType === 'oru') {
        console.log(`ℹ️ Skipping ORU demographics for patient ${parsed.patient.id}`);
      }
    }

    // Observations, Conditions, Encounters: always insert
    if (parsed.observations?.length) await insertObservations(parsed.observations, ctx);
    if (parsed.conditions?.length)   await insertConditions(parsed.conditions, ctx);
    if (parsed.encounters?.length)   await insertEncounters(parsed.encounters, ctx);

    console.log(`✅ Done: ${fileOnly}\n`);
  } catch (err) {
    console.error(`❌ Failed to load ${path.basename(filePath)}:`, err.message);
  }
}

// Parse all files in the data folder (recursively)
async function loadAllFHIRFiles() {
  const files = getAllJsonFiles(DATA_FOLDER);

  console.log(`🔍 Found ${files.length} JSON files`);

  for (const filePath of files) {
    await loadFHIRFromFile(filePath);
  }

  console.log('🚀 All files processed.');
}

// Entry point if run directly
if (require.main === module) {
  loadAllFHIRFiles();
}

module.exports = { loadFHIRFromFile, loadAllFHIRFiles };
