const fs = require('fs');
const path = require('path');

const DATA_DIR = path.resolve(__dirname, 'C:/Users/kasar/CoCM_Platform/backend/data/all_converted_files/All Converted Files');
const codeMap = {};

function extractCodesFromFile(filepath) {
  try {
    const raw = fs.readFileSync(filepath, 'utf8');
    const bundle = JSON.parse(raw);

    for (const entry of bundle.entry || []) {
      const res = entry.resource;
      if (res?.resourceType === 'Condition') {
        const code = res.code?.coding?.[0]?.code;
        const display = res.code?.coding?.[0]?.display || res.code?.text;
        if (code) {
          codeMap[code] = display || codeMap[code] || "Unknown";
        }
      }
    }
  } catch (err) {
    console.log(`❌ Failed to read ${filepath}: ${err.message}`);
  }
}

fs.readdirSync(DATA_DIR).forEach(file => {
  if (file.endsWith('.json')) {
    extractCodesFromFile(path.join(DATA_DIR, file));
  }
});

console.log("🧠 Unique Condition Codes Found:");
console.table(codeMap);
