// scripts/geocode_locations.js

const axios = require('axios');
const db = require('../../db');
const dotenv = require('dotenv');
dotenv.config();

const GOOGLE_API_KEY = process.env.GOOGLE_MAPS_API_KEY;

if (!GOOGLE_API_KEY) {
  console.error('❌ Missing GOOGLE_MAPS_API_KEY in .env');
  process.exit(1);
}

async function geocodeAddress({ city, state, postal_code }) {
  const address = `${city}, ${state}, ${postal_code}`;
  const url = `https://maps.googleapis.com/maps/api/geocode/json?address=${encodeURIComponent(address)}&key=${GOOGLE_API_KEY}`;

  try {
    const { data } = await axios.get(url);
    if (data.status === 'OK' && data.results.length > 0) {
      return data.results[0].geometry.location;
    } else {
      console.warn(`⚠️ No result for: ${address}`);
      return null;
    }
  } catch (error) {
    console.error(`❌ Error geocoding ${address}:`, error.message);
    return null;
  }
}

async function updateHospitalLocations() {
  try {
    const [locations] = await db.query(`
      SELECT id, city, state, postal_code 
      FROM hospital_locations 
      WHERE (latitude IS NULL OR latitude = 0)
        AND (longitude IS NULL OR longitude = 0)
    `);

    console.log(`📍 Found ${locations.length} locations to geocode\n`);

    for (const loc of locations) {
      const coords = await geocodeAddress(loc);
      if (!coords) continue;

      await db.execute(
        `UPDATE hospital_locations SET latitude = ?, longitude = ? WHERE id = ?`,
        [coords.lat, coords.lng, loc.id]
      );

      console.log(`✅ ${loc.city} → (${coords.lat.toFixed(4)}, ${coords.lng.toFixed(4)})`);

      await new Promise(resolve => setTimeout(resolve, 250)); // rate limiting
    }

    console.log('\n🎯 All locations updated!');
  } catch (err) {
    console.error('❌ Database error:', err.message);
  } finally {
    process.exit(0);
  }
}

updateHospitalLocations();
