// backend/api/scripts/simple_hospital_fix.js
// Simple fix for hospital_locations table - update existing columns only

const fs = require('fs');
const path = require('path');
const axios = require('axios');
const db = require('../../db');
const dotenv = require('dotenv');
dotenv.config();

class SimpleHospitalFixer {
  constructor() {
    this.stats = {
      total_records: 0,
      updated: 0,
      failed: 0,
      skipped: 0
    };
  }

  async fixHospitalLocations() {
    console.log('🔧 Starting Simple Hospital Locations Fix\n');

    try {
      // Step 1: Get all records that need updating
      const recordsToUpdate = await this.getRecordsToUpdate();
      this.stats.total_records = recordsToUpdate.length;

      console.log(`📊 Found ${recordsToUpdate.length} records to update`);

      // Step 2: Process each record
      for (const record of recordsToUpdate) {
        await this.updateRecord(record);
        await this.delay(300); // Rate limiting
      }

      // Step 3: Generate report
      await this.generateReport();

      console.log('\n✅ Simple hospital locations fix completed!');

    } catch (error) {
      console.error('❌ Error fixing hospital locations:', error.message);
      throw error;
    }
  }

  async getRecordsToUpdate() {
    // Get records that have zero coordinates or generic hospital names
    const [records] = await db.query(`
      SELECT id, hospital_name, city, state, postal_code, latitude, longitude
      FROM hospital_locations 
      WHERE (latitude = 0 OR longitude = 0 OR latitude IS NULL OR longitude IS NULL)
         OR hospital_name LIKE '% General Hospital'
      ORDER BY id
    `);

    return records;
  }

  async updateRecord(record) {
    console.log(`🔍 Processing: ${record.hospital_name} (${record.city}, ${record.state})`);

    try {
      // Try to find real hospital name and coordinates
      const realHospitalData = await this.findRealHospitalData(record);

      if (realHospitalData) {
        await this.updateDatabaseRecord(record.id, realHospitalData);
        this.stats.updated++;
        console.log(`  ✅ Updated: ${realHospitalData.hospital_name} → (${realHospitalData.latitude}, ${realHospitalData.longitude})`);
      } else {
        this.stats.failed++;
        console.log(`  ❌ Could not find coordinates`);
      }

    } catch (error) {
      this.stats.failed++;
      console.error(`  ❌ Error: ${error.message}`);
    }
  }

  async findRealHospitalData(record) {
    // Strategy 1: Try to find real hospital name from city
    const realHospitalName = this.findRealHospitalName(record.city);
    
    if (realHospitalName) {
      // Try NPI API first
      const npiResult = await this.searchNPI(realHospitalName, record.state);
      if (npiResult) return npiResult;

      // Try Google Geocoding
      const googleResult = await this.geocodeWithGoogle(realHospitalName, record.city, record.state);
      if (googleResult) return googleResult;
    }

    // Strategy 2: Try geocoding with city + state
    const cityGeocode = await this.geocodeWithGoogle(`${record.city} Hospital`, record.city, record.state);
    if (cityGeocode) return cityGeocode;

    return null;
  }

  findRealHospitalName(city) {
    // Map of cities to likely hospital names
    const cityHospitalMap = {
      'IRON RIVER': 'Aspirus Iron River Hospital',
      'IRONWOOD': 'Aspirus Ironwood Hospital',
      'HOUGHTON': 'Aspirus Houghton Clinic',
      'KEWEENAW': 'Aspirus Keweenaw Hospital',
      'CRYSTAL FALLS': 'Dickinson County Healthcare System',
      'BARAGA': 'Baraga County Memorial Hospital',
      'MUNISING': 'Munising Memorial Hospital',
      'MARQUETTE': 'UP Health System Marquette',
      'ESCANABA': 'OSF St. Francis Hospital',
      'MANISTIQUE': 'Schoolcraft Memorial Hospital',
      'GLADSTONE': 'OSF St. Francis Hospital',
      'ISHPEMING': 'Bell Memorial Hospital',
      'NEWBERRY': 'Helen Newberry Joy Hospital',
      'NEGAUNEE': 'UP Health System Marquette',
      'GWINN': 'UP Health System Marquette',
      'GULLIVER': 'Schoolcraft Memorial Hospital',
      'RAPID RIVER': 'OSF St. Francis Hospital',
      'GARDEN': 'Schoolcraft Memorial Hospital',
      'COOKS': 'Helen Newberry Joy Hospital',
      'BARK RIVER': 'OSF St. Francis Hospital',
      'GERMFASK': 'Schoolcraft Memorial Hospital',
      'WELLS': 'Helen Newberry Joy Hospital',
      'MC MILLAN': 'Helen Newberry Joy Hospital',
      'SAULT SAINTE MARIE': 'War Memorial Hospital',
      'CARNEY': 'OSF St. Francis Hospital',
      'ROCK': 'Schoolcraft Memorial Hospital',
      'WETMORE': 'Helen Newberry Joy Hospital',
      'POWERS': 'OSF St. Francis Hospital',
      'MENOMINEE': 'OSF St. Francis Hospital',
      'ONTONAGON': 'Aspirus Keweenaw Hospital',
      'LAURIUM': 'Aspirus Keweenaw Hospital',
      'BIG BAY': 'UP Health System Marquette',
      'CASPIAN': 'Dickinson County Healthcare System',
      'CALUMET': 'Aspirus Keweenaw Hospital',
      'KINGSFORD': 'Dickinson County Healthcare System',
      'WILSON': 'Schoolcraft Memorial Hospital',
      'DAGGETT': 'OSF St. Francis Hospital',
      'SENEY': 'Schoolcraft Memorial Hospital',
      'SAINT IGNACE': 'Mackinac Straits Health System',
      'NAUBINWAY': 'Mackinac Straits Health System',
      'EBEN JUNCTION': 'Schoolcraft Memorial Hospital',
      'CHAMPION': 'UP Health System Marquette'
    };

    return cityHospitalMap[city] || null;
  }

  async searchNPI(hospitalName, state) {
    try {
      const url = `https://npiregistry.cms.hhs.gov/api/?version=2.1&organization_name=${encodeURIComponent(hospitalName)}&state=${state}&limit=5`;
      const response = await axios.get(url, { timeout: 10000 });
      
      if (response.data.results && response.data.results.length > 0) {
        const result = response.data.results[0];
        const address = result.addresses?.find(a => a.address_purpose === 'LOCATION') || result.addresses?.[0];
        
        if (address && address.latitude && address.longitude) {
          return {
            hospital_name: result.basic?.organization_name || hospitalName,
            city: address.city,
            state: address.state,
            postal_code: address.postal_code,
            latitude: parseFloat(address.latitude),
            longitude: parseFloat(address.longitude),
            source: 'npi'
          };
        }
      }
    } catch (error) {
      console.warn(`    ⚠️ NPI search failed for ${hospitalName}: ${error.message}`);
    }
    
    return null;
  }

  async geocodeWithGoogle(hospitalName, city, state) {
    if (!process.env.GOOGLE_MAPS_API_KEY) {
      return null;
    }

    try {
      const searchQuery = `${hospitalName}, ${city}, ${state}`;
      const url = `https://maps.googleapis.com/maps/api/geocode/json?address=${encodeURIComponent(searchQuery)}&key=${process.env.GOOGLE_MAPS_API_KEY}`;
      const response = await axios.get(url, { timeout: 10000 });
      
      if (response.data.status === 'OK' && response.data.results.length > 0) {
        const result = response.data.results[0];
        const location = result.geometry.location;
        
        return {
          hospital_name: hospitalName,
          city: city,
          state: state,
          postal_code: this.extractPostalCodeFromAddress(result.formatted_address),
          latitude: location.lat,
          longitude: location.lng,
          source: 'google'
        };
      }
    } catch (error) {
      console.warn(`    ⚠️ Google geocoding failed for ${hospitalName}: ${error.message}`);
    }
    
    return null;
  }

  extractPostalCodeFromAddress(address) {
    const zipMatch = address.match(/\b\d{5}(-\d{4})?\b/);
    return zipMatch ? zipMatch[0] : null;
  }

  async updateDatabaseRecord(recordId, hospitalData) {
    await db.execute(`
      UPDATE hospital_locations 
      SET 
        hospital_name = ?,
        city = ?,
        state = ?,
        postal_code = ?,
        latitude = ?,
        longitude = ?
      WHERE id = ?
    `, [
      hospitalData.hospital_name,
      hospitalData.city,
      hospitalData.state,
      hospitalData.postal_code,
      hospitalData.latitude,
      hospitalData.longitude,
      recordId
    ]);
  }

  async delay(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  async generateReport() {
    console.log('\n📊 Final Report:');
    
    const [finalStats] = await db.query(`
      SELECT 
        COUNT(*) as total_hospitals,
        COUNT(CASE WHEN latitude != 0 AND longitude != 0 THEN 1 END) as with_coordinates,
        COUNT(CASE WHEN latitude = 0 OR longitude = 0 THEN 1 END) as without_coordinates,
        COUNT(CASE WHEN hospital_name NOT LIKE '% General Hospital' THEN 1 END) as real_names
      FROM hospital_locations
    `);

    console.log(`  Total hospitals: ${finalStats[0].total_hospitals}`);
    console.log(`  With coordinates: ${finalStats[0].with_coordinates}`);
    console.log(`  Without coordinates: ${finalStats[0].without_coordinates}`);
    console.log(`  Real hospital names: ${finalStats[0].real_names}`);
    console.log(`  Success rate: ${((this.stats.updated / this.stats.total_records) * 100).toFixed(1)}%`);

    // Save report
    const report = {
      timestamp: new Date().toISOString(),
      processing_stats: this.stats,
      final_stats: finalStats[0]
    };

    fs.writeFileSync(
      path.join(__dirname, 'simple_hospital_fix_report.json'),
      JSON.stringify(report, null, 2)
    );

    console.log(`\n📄 Report saved to: simple_hospital_fix_report.json`);
  }
}

// Main execution
async function main() {
  const fixer = new SimpleHospitalFixer();
  
  try {
    await fixer.fixHospitalLocations();
    process.exit(0);
  } catch (error) {
    console.error('❌ Simple hospital locations fix failed:', error);
    process.exit(1);
  }
}

if (require.main === module) {
  main();
}

module.exports = { SimpleHospitalFixer };
