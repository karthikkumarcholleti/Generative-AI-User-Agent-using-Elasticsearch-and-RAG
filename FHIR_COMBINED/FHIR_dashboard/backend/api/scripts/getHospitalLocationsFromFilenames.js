/* backend/api/scripts/fetchHospitalLocationsFromList.js
 */

const fs = require("fs");
const path = require("path");

if (typeof fetch === "undefined") {
  global.fetch = (...args) =>
    import("node-fetch").then(({ default: f }) => f(...args));
}

const INPUT_FILE  = path.join(__dirname, "hospital_locations.json");
const OUTPUT_FILE = path.join(__dirname, "hospital_locations_resolved.json");


const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

function normalize(str) {
  return (str || "")
    .toLowerCase()
    .replace(/\./g, "")
    .replace(/-/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

function nameCandidates(original) {
  
  const base = original.trim();
  const variants = new Set([base]);

  // St. -> Saint
  variants.add(base.replace(/\bSt\.\b/g, "Saint"));
  // Collapse hyphens to spaces
  variants.add(base.replace(/-/g, " "));
  // Add/remove "Hospital"
  if (!/hospital/i.test(base)) variants.add(base + " Hospital");

  return [...variants].filter(Boolean);
}

function npiUrl(orgName) {
  const params = new URLSearchParams({
    version: "2.1",
    enumeration_type: "NPI-2",
    organization_name: orgName,
    limit: "50",
  });
  return `https://npiregistry.cms.hhs.gov/api/?${params.toString()}`;
}

function scoreNameMatch(query, candidate) {
  const q = normalize(query);
  const c = normalize(candidate);
  if (!q || !c) return 0;

  const qt = new Set(q.split(" "));
  const ct = new Set(c.split(" "));
  const inter = [...qt].filter((t) => ct.has(t)).length;
  const score = inter / Math.max(qt.size, 1);

  return c.includes(q) ? Math.max(score, 0.8) : score;
}

function selectBestResult(hospitalName, results) {
  let best = null;
  let bestScore = 0;

  for (const r of results) {
    const orgName =
      r?.basic?.organization_name ||
      r?.basic?.name ||
      r?.basic?.authorized_official_organization_name ||
      "";

    const s = scoreNameMatch(hospitalName, orgName);
    if (s > bestScore) {
      best = r;
      bestScore = s;
    }
  }

  return bestScore >= 0.4 ? best : null;
}

function pickAddress(result) {
  const addrs = Array.isArray(result?.addresses) ? result.addresses : [];
  return (
    addrs.find((a) => a.address_purpose === "LOCATION") ||
    addrs.find((a) => a.address_purpose === "PRIMARY") ||
    addrs[0] ||
    null
  );
}

async function resolveOne(h) {
  const name = h.hospital;
  const variants = nameCandidates(name);

  for (const variant of variants) {
    try {
      const url = npiUrl(variant);
      const res = await fetch(url);
      if (!res.ok) {
        console.error(`❌ HTTP ${res.status} for ${variant}`);
        continue;
      }
      const data = await res.json();

      if (data.results && data.results.length > 0) {
        const best = selectBestResult(name, data.results);
        if (best) {
          const addr = pickAddress(best);
          return {
            hospital: name,
            address: addr
              ? `${addr.address_1}, ${addr.city}, ${addr.state}, ${addr.postal_code}`
              : null,
            lat: addr?.latitude ? parseFloat(addr.latitude) : null,
            lon: addr?.longitude ? parseFloat(addr.longitude) : null,
          };
        }
      }
    } catch (err) {
      console.error(`❌ Error fetching for ${variant}:`, err.message);
    }
    await sleep(300); // avoid hitting API rate limits
  }

  return { hospital: name, address: null, lat: null, lon: null };
}

(async () => {
  if (!fs.existsSync(INPUT_FILE)) {
    console.error(`❌ Input file not found: ${INPUT_FILE}`);
    process.exit(1);
  }

  const hospitals = JSON.parse(fs.readFileSync(INPUT_FILE, "utf8"));
  const results = [];

  for (const h of hospitals) {
    console.log(`🔍 Resolving: ${h.hospital}`);
    const loc = await resolveOne(h);
    results.push(loc);
  }

  fs.writeFileSync(OUTPUT_FILE, JSON.stringify(results, null, 2));
  console.log(`📄 Saved ${results.length} resolved locations to ${OUTPUT_FILE}`);
})();
