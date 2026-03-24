// backend/api/scripts/fix_hospital_locations.js
// Fix existing hospital_locations table with real hospital names and coordinates

const fs = require('fs');
const path = require('path');
const axios = require('axios');
const db = require('../../db');
const dotenv = require('dotenv');
dotenv.config();

class HospitalLocationFixer {
  constructor() {
    this.stats = {
      total_records: 0,
      processed: 0,
      geocoded: 0,
      failed: 0,
      duplicates_removed: 0
    };
  }

  async fixHospitalLocations() {
    console.log('🔧 Starting Hospital Locations Fix Process\n');

    try {
      // Step 1: Analyze current data
      await this.analyzeCurrentData();

      // Step 2: Extract real hospital names from filenames
      const realHospitals = await this.extractRealHospitalNames();

      // Step 3: Clean and deduplicate existing data
      await this.cleanExistingData();

      // Step 4: Geocode real hospital names
      await this.geocodeRealHospitals(realHospitals);

      // Step 5: Generate final report
      await this.generateReport();

      console.log('\n✅ Hospital locations fix completed successfully!');

    } catch (error) {
      console.error('❌ Error fixing hospital locations:', error.message);
      throw error;
    }
  }

  async analyzeCurrentData() {
    console.log('📊 Analyzing current hospital_locations data...');

    const [totalCount] = await db.query('SELECT COUNT(*) as count FROM hospital_locations');
    const [coordsCount] = await db.query('SELECT COUNT(*) as count FROM hospital_locations WHERE latitude != 0 AND longitude != 0');
    const [duplicatesCount] = await db.query(`
      SELECT COUNT(*) as count FROM (
        SELECT hospital_name, COUNT(*) as cnt 
        FROM hospital_locations 
        GROUP BY hospital_name 
        HAVING cnt > 1
      ) as duplicates
    `);

    this.stats.total_records = totalCount[0].count;

    console.log(`  Total records: ${totalCount[0].count}`);
    console.log(`  Records with coordinates: ${coordsCount[0].count}`);
    console.log(`  Duplicate hospital names: ${duplicatesCount[0].count}`);
  }

  async extractRealHospitalNames() {
    console.log('\n🏥 Extracting real hospital names from filenames...');

    const dataDirectories = [
      'C:/Users/kasar/CoCM_Platform/UI Updates FHIR/backend/data/Converted_data/ADT',
      'C:/Users/kasar/CoCM_Platform/UI Updates FHIR/backend/data/Converted_data/CCDA',
      'C:/Users/kasar/CoCM_Platform/UI Updates FHIR/backend/data/Converted_data/ORU'
    ];

    const hospitalNames = new Set();
    const hospitalMappings = {
      // ADT patterns
      'ASPIRH': 'Aspirus Iron River Hospital',
      'ASPIRW': 'Aspirus Ironwood Hospital',
      'ASPIKH': 'Aspirus Keweenaw Hospital',
      'ASPIHC': 'Aspirus Houghton Clinic',
      'BCMH': 'Baraga County Memorial Hospital',
      'BSC': 'BayCare Clinic',
      'BCH': 'Bronson Battle Creek Hospital',
      'BSH': 'Bon Secours Hospital',
      'CORE': 'Corewell Health',
      'CORET': 'Corewell Health Troy Hospital',
      'DCHS': 'Dickinson County Healthcare System',
      'HFCC': 'HFCC Center for Family Health',
      'HFH': 'Henry Ford Hospital',
      'HFJ': 'Henry Ford Jackson Hospital',
      'HFM': 'Henry Ford Macomb Hospital',
      'MCL': 'McLaren Macomb',
      'MICH': 'Michigan Medicine',
      'MMH': 'Munising Memorial Hospital',
      
      // CCDA patterns
      'uphieaspirus': 'Aspirus Uphie',
      'aspirus': 'Aspirus Health System',
      'corewell': 'Corewell Health',
      'henryford': 'Henry Ford Health System',
      'mclaren': 'McLaren Health Care',
      'michigan': 'Michigan Medicine',
      
      // ORU patterns
      'Aspirus': 'Aspirus Health System',
      'Corewell': 'Corewell Health',
      'Henry_Ford': 'Henry Ford Health System',
      'McLaren': 'McLaren Health Care',
      'Michigan_Medicine': 'Michigan Medicine',
      'Bronson': 'Bronson Healthcare',
      'Munising': 'Munising Memorial Hospital'
    };

    for (const directory of dataDirectories) {
      if (fs.existsSync(directory)) {
        console.log(`  📂 Processing: ${path.basename(directory)}`);
        const files = this.getAllJsonFiles(directory);
        
        for (const filePath of files) {
          const filename = path.basename(filePath);
          const hospitalName = this.extractHospitalFromFilename(filename, hospitalMappings);
          if (hospitalName) {
            hospitalNames.add(hospitalName);
          }
        }
      }
    }

    const hospitalList = Array.from(hospitalNames).sort();
    console.log(`  ✅ Extracted ${hospitalList.length} unique hospital names`);

    return hospitalList;
  }

  extractHospitalFromFilename(filename, mappings) {
    // ADT pattern: TEST_ASPIRH_A01_20250701042422247_fhir.json
    const adtMatch = filename.match(/TEST_([A-Z_]+)_A\d+_\d+_fhir\.json$/i);
    if (adtMatch) {
      return mappings[adtMatch[1]] || this.expandCode(adtMatch[1]);
    }

    // CCDA pattern: fhir_output_TEST_ccd_uphieaspirus_20250701000000.json
    const ccdaMatch = filename.match(/fhir_output_TEST_ccd_([a-z]+)_\d+\.json$/i);
    if (ccdaMatch) {
      return mappings[ccdaMatch[1]] || this.expandCode(ccdaMatch[1]);
    }

    // ORU pattern: TEST_Aspirus_LAB_2025-07-01-06-21-18-746_fhir.json
    const oruMatch = filename.match(/TEST_([A-Za-z_]+)_LAB_\d{4}-\d{2}-\d{2}-\d{2}-\d{2}-\d{2}-\d{3}_fhir\.json$/i);
    if (oruMatch) {
      return mappings[oruMatch[1]] || this.expandCode(oruMatch[1]);
    }

    return null;
  }

  expandCode(code) {
    return code
      .replace(/_/g, ' ')
      .replace(/\b([A-Z])([A-Z]+)\b/g, (match, first, rest) => 
        first + rest.toLowerCase())
      .replace(/\b\w/g, l => l.toUpperCase());
  }

  getAllJsonFiles(dir) {
    let results = [];
    const list = fs.readdirSync(dir);

    list.forEach(file => {
      const filePath = path.join(dir, file);
      const stat = fs.statSync(filePath);

      if (stat && stat.isDirectory()) {
        results = results.concat(this.getAllJsonFiles(filePath));
      } else if (filePath.endsWith('.json')) {
        results.push(filePath);
      }
    });

    return results;
  }

  async cleanExistingData() {
    console.log('\n🧹 Cleaning existing data...');

    // Remove duplicates, keeping the one with the most complete data
    await db.execute(`
      DELETE h1 FROM hospital_locations h1
      INNER JOIN hospital_locations h2 
      WHERE h1.id > h2.id 
      AND h1.hospital_name = h2.hospital_name
      AND h1.city = h2.city
      AND h1.state = h2.state
    `);

    // Remove generic "General Hospital" entries
    await db.execute(`
      DELETE FROM hospital_locations 
      WHERE hospital_name LIKE '% General Hospital'
    `);

    console.log('  ✅ Removed duplicates and generic entries');
  }

  async geocodeRealHospitals(hospitalNames) {
    console.log('\n🌍 Geocoding real hospital names...');

    // Clear existing data
    await db.execute('TRUNCATE TABLE hospital_locations');

    for (const hospitalName of hospitalNames) {
      console.log(`  🔍 Processing: ${hospitalName}`);
      
      try {
        const locationData = await this.findHospitalLocation(hospitalName);
        
        if (locationData) {
          await this.insertHospitalLocation(hospitalName, locationData);
          this.stats.geocoded++;
          console.log(`    ✅ Found: ${locationData.latitude}, ${locationData.longitude}`);
        } else {
          this.stats.failed++;
          console.log(`    ❌ Not found`);
        }
      } catch (error) {
        this.stats.failed++;
        console.error(`    ❌ Error: ${error.message}`);
      }

      this.stats.processed++;
      
      // Rate limiting
      await new Promise(resolve => setTimeout(resolve, 300));
    }
  }

  async findHospitalLocation(hospitalName) {
    // Strategy 1: Try NPI API
    const npiResult = await this.searchNPI(hospitalName);
    if (npiResult && npiResult.latitude && npiResult.longitude) {
      return npiResult;
    }

    // Strategy 2: Try Google Geocoding
    const googleResult = await this.geocodeWithGoogle(hospitalName);
    if (googleResult && googleResult.latitude && googleResult.longitude) {
      return googleResult;
    }

    return null;
  }

  async searchNPI(hospitalName) {
    try {
      const url = `https://npiregistry.cms.hhs.gov/api/?version=2.1&organization_name=${encodeURIComponent(hospitalName)}&limit=10`;
      const response = await axios.get(url, { timeout: 10000 });
      
      if (response.data.results && response.data.results.length > 0) {
        const result = response.data.results[0];
        const address = result.addresses?.find(a => a.address_purpose === 'LOCATION') || result.addresses?.[0];
        
        if (address && address.latitude && address.longitude) {
          return {
            hospital_name: result.basic?.organization_name || hospitalName,
            address: address.address_1,
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

  async geocodeWithGoogle(hospitalName) {
    if (!process.env.GOOGLE_MAPS_API_KEY) {
      console.warn('    ⚠️ Google Maps API key not found');
      return null;
    }

    try {
      const url = `https://maps.googleapis.com/maps/api/geocode/json?address=${encodeURIComponent(hospitalName + ' Michigan')}&key=${process.env.GOOGLE_MAPS_API_KEY}`;
      const response = await axios.get(url, { timeout: 10000 });
      
      if (response.data.status === 'OK' && response.data.results.length > 0) {
        const result = response.data.results[0];
        const location = result.geometry.location;
        
        return {
          hospital_name: hospitalName,
          address: result.formatted_address,
          city: this.extractCityFromAddress(result.formatted_address),
          state: 'MI',
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

  extractCityFromAddress(address) {
    const parts = address.split(',');
    return parts.length >= 2 ? parts[1].trim() : null;
  }

  extractPostalCodeFromAddress(address) {
    const zipMatch = address.match(/\b\d{5}(-\d{4})?\b/);
    return zipMatch ? zipMatch[0] : null;
  }

  async insertHospitalLocation(hospitalName, locationData) {
    await db.execute(`
      INSERT INTO hospital_locations 
      (hospital_name, address, city, state, postal_code, latitude, longitude)
      VALUES (?, ?, ?, ?, ?, ?, ?)
    `, [
      locationData.hospital_name,
      locationData.address,
      locationData.city,
      locationData.state,
      locationData.postal_code,
      locationData.latitude,
      locationData.longitude
    ]);
  }

  async generateReport() {
    console.log('\n📊 Final Report:');
    
    const [finalStats] = await db.query(`
      SELECT 
        COUNT(*) as total_hospitals,
        COUNT(CASE WHEN latitude != 0 AND longitude != 0 THEN 1 END) as with_coordinates,
        COUNT(CASE WHEN source = 'npi' THEN 1 END) as npi_sourced,
        COUNT(CASE WHEN source = 'google' THEN 1 END) as google_sourced
      FROM hospital_locations
    `);

    console.log(`  Total hospitals: ${finalStats[0].total_hospitals}`);
    console.log(`  With coordinates: ${finalStats[0].with_coordinates}`);
    console.log(`  NPI sourced: ${finalStats[0].npi_sourced || 0}`);
    console.log(`  Google sourced: ${finalStats[0].google_sourced || 0}`);
    console.log(`  Success rate: ${((finalStats[0].with_coordinates / finalStats[0].total_hospitals) * 100).toFixed(1)}%`);

    // Save detailed report
    const report = {
      timestamp: new Date().toISOString(),
      statistics: finalStats[0],
      processing_stats: this.stats
    };

    fs.writeFileSync(
      path.join(__dirname, 'hospital_locations_fix_report.json'),
      JSON.stringify(report, null, 2)
    );

    console.log(`\n📄 Detailed report saved to: hospital_locations_fix_report.json`);
  }
}

// Main execution
async function main() {
  const fixer = new HospitalLocationFixer();
  
  try {
    await fixer.fixHospitalLocations();
    process.exit(0);
  } catch (error) {
    console.error('❌ Hospital locations fix failed:', error);
    process.exit(1);
  }
}

if (require.main === module) {
  main();
}

module.exports = { HospitalLocationFixer };
