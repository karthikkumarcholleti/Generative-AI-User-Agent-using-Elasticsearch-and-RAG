const fs = require('fs');
const path = require('path');
const axios = require('axios');
const db = require('../../db');
const dotenv = require('dotenv');
dotenv.config();

const GOOGLE_API_KEY = process.env.GOOGLE_MAPS_API_KEY;
if (!GOOGLE_API_KEY) {
  console.error('❌ Missing GOOGLE_MAPS_API_KEY in .env');
  process.exit(1);
}

const filePath = path.join(__dirname, 'hospital_locations_resolved.json');

async function fetchAddressFromNPI(hospitalName) {
  const url = `https://npiregistry.cms.hhs.gov/api/?version=2.1&organization_name=${encodeURIComponent(hospitalName)}`;
  try {
    const { data } = await axios.get(url);
    if (data.results && data.results.length > 0) {
      const addr = data.results[0].addresses?.find(a => a.address_purpose === 'LOCATION') || data.results[0].addresses?.[0];
      if (addr) {
        return {
          address: addr.address_1,
          city: addr.city,
          state: addr.state,
          postal_code: addr.postal_code
        };
      }
    }
  } catch (err) {
    console.warn(`⚠️ NPI lookup failed for ${hospitalName}: ${err.message}`);
  }
  return null;
}

async function geocodeAddress(addressObj) {
  const fullAddress = `${addressObj.address}, ${addressObj.city}, ${addressObj.state}, ${addressObj.postal_code}`;
  const url = `https://maps.googleapis.com/maps/api/geocode/json?address=${encodeURIComponent(fullAddress)}&key=${GOOGLE_API_KEY}`;

  try {
    const { data } = await axios.get(url);
    if (data.status === 'OK' && data.results.length > 0) {
      const loc = data.results[0].geometry.location;
      return { lat: loc.lat, lon: loc.lng };
    } else {
      console.warn(`⚠️ Geocode failed for: ${fullAddress}`);
    }
  } catch (err) {
    console.error(`❌ Geocode error for ${fullAddress}:`, err.message);
  }
  return { lat: null, lon: null };
}

(async () => {
  try {
    const jsonData = JSON.parse(fs.readFileSync(filePath, 'utf8'));
    console.log(`📄 Loaded ${jsonData.length} hospitals from JSON`);

    await db.execute(`
      CREATE TABLE IF NOT EXISTS hospital_locations_map (
        id INT AUTO_INCREMENT PRIMARY KEY,
        hospital_name VARCHAR(255) NOT NULL,
        address VARCHAR(255),
        city VARCHAR(100),
        state VARCHAR(50),
        postal_code VARCHAR(20),
        latitude DECIMAL(10,8),
        longitude DECIMAL(11,8)
      )
    `);

    await db.execute('TRUNCATE TABLE hospital_locations_map');

    for (const hospital of jsonData) {
      let { hospital: hospitalName, address, city, state, postal_code, lat, lon } = hospital;

      const hasAddressInfo = address && city && state && postal_code;

      // Step 1: Fetch missing address from NPI if incomplete
      if (!hasAddressInfo) {
        const npiData = await fetchAddressFromNPI(hospitalName);
        if (npiData) {
          address = address || npiData.address;
          city = city || npiData.city;
          state = state || npiData.state;
          postal_code = postal_code || npiData.postal_code;
        }
      }

      // Step 2: Geocode only if we now have address info
      if ((!lat || !lon) && address && city && state && postal_code) {
        const geo = await geocodeAddress({ address, city, state, postal_code });
        lat = geo.lat;
        lon = geo.lon;
      }

      // Step 3: Skip if still missing coords
      if (!lat || !lon) {
        console.warn(`⏭️ Skipping ${hospitalName} (no coords found)`);
        continue;
      }

      // Step 4: Insert into DB
      await db.execute(
        `INSERT INTO hospital_locations_map 
        (hospital_name, address, city, state, postal_code, latitude, longitude)
        VALUES (?, ?, ?, ?, ?, ?, ?)`,
        [hospitalName, address, city, state, postal_code, lat, lon]
      );

      console.log(`✅ Inserted ${hospitalName} → (${lat}, ${lon})`);
      await new Promise(res => setTimeout(res, 300)); // rate limit
    }

    console.log('🎯 All valid hospital locations inserted!');
    process.exit(0);
  } catch (err) {
    console.error('❌ Error:', err.message);
    process.exit(1);
  }
})();
