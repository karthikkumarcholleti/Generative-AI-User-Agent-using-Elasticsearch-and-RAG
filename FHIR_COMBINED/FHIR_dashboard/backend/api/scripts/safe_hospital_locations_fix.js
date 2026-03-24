// backend/api/scripts/safe_hospital_locations_fix.js
// Safely fix hospital_locations without breaking foreign key constraints

const fs = require('fs');
const path = require('path');
const axios = require('axios');
const db = require('../../db');
const dotenv = require('dotenv');
dotenv.config();

class SafeHospitalLocationFixer {
  constructor() {
    this.stats = {
      total_records: 0,
      updated: 0,
      failed: 0,
      skipped: 0,
      duplicates_consolidated: 0
    };
    this.hospitalMappings = {
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
  }

  async fixHospitalLocations() {
    console.log('🔧 Starting Safe Hospital Locations Fix Process\n');

    try {
      // Step 1: Extract real hospital names from filenames
      const realHospitals = await this.extractRealHospitalNames();
      console.log(`✅ Found ${realHospitals.length} real hospital names from filenames`);

      // Step 2: Create a mapping of cities to real hospitals
      const cityHospitalMap = await this.createCityHospitalMapping(realHospitals);

      // Step 3: Update existing records with real data
      await this.updateExistingRecords(cityHospitalMap);

      // Step 4: Consolidate duplicates
      await this.consolidateDuplicates();

      // Step 5: Generate final report
      await this.generateReport();

      console.log('\n✅ Safe hospital locations fix completed successfully!');

    } catch (error) {
      console.error('❌ Error fixing hospital locations:', error.message);
      throw error;
    }
  }

  async extractRealHospitalNames() {
    console.log('🏥 Extracting real hospital names from filenames...');

    const dataDirectories = [
      'C:/Users/kasar/CoCM_Platform/UI Updates FHIR/backend/data/Converted_data/ADT',
      'C:/Users/kasar/CoCM_Platform/UI Updates FHIR/backend/data/Converted_data/CCDA',
      'C:/Users/kasar/CoCM_Platform/UI Updates FHIR/backend/data/Converted_data/ORU'
    ];

    const hospitalNames = new Set();

    for (const directory of dataDirectories) {
      if (fs.existsSync(directory)) {
        console.log(`  📂 Processing: ${path.basename(directory)}`);
        const files = this.getAllJsonFiles(directory);
        
        for (const filePath of files) {
          const filename = path.basename(filePath);
          const hospitalName = this.extractHospitalFromFilename(filename);
          if (hospitalName) {
            hospitalNames.add(hospitalName);
          }
        }
      }
    }

    return Array.from(hospitalNames).sort();
  }

  extractHospitalFromFilename(filename) {
    // ADT pattern: TEST_ASPIRH_A01_20250701042422247_fhir.json
    const adtMatch = filename.match(/TEST_([A-Z_]+)_A\d+_\d+_fhir\.json$/i);
    if (adtMatch) {
      return this.hospitalMappings[adtMatch[1]] || this.expandCode(adtMatch[1]);
    }

    // CCDA pattern: fhir_output_TEST_ccd_uphieaspirus_20250701000000.json
    const ccdaMatch = filename.match(/fhir_output_TEST_ccd_([a-z]+)_\d+\.json$/i);
    if (ccdaMatch) {
      return this.hospitalMappings[ccdaMatch[1]] || this.expandCode(ccdaMatch[1]);
    }

    // ORU pattern: TEST_Aspirus_LAB_2025-07-01-06-21-18-746_fhir.json
    const oruMatch = filename.match(/TEST_([A-Za-z_]+)_LAB_\d{4}-\d{2}-\d{2}-\d{2}-\d{2}-\d{2}-\d{3}_fhir\.json$/i);
    if (oruMatch) {
      return this.hospitalMappings[oruMatch[1]] || this.expandCode(oruMatch[1]);
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

  async createCityHospitalMapping(realHospitals) {
    console.log('\n🗺️ Creating city to hospital mapping...');

    const cityHospitalMap = {};

    // Map cities to likely hospitals based on common patterns
    const cityMappings = {
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

    // Use real hospitals from filenames first, then fall back to city mappings
    for (const [city, hospital] of Object.entries(cityMappings)) {
      if (realHospitals.includes(hospital)) {
        cityHospitalMap[city] = hospital;
      } else {
        cityHospitalMap[city] = hospital; // Use mapping even if not in real hospitals
      }
    }

    console.log(`  ✅ Created mapping for ${Object.keys(cityHospitalMap).length} cities`);
    return cityHospitalMap;
  }

  async updateExistingRecords(cityHospitalMap) {
    console.log('\n🔄 Updating existing records with real data...');

    // Get all records that need updating
    const [records] = await db.query(`
      SELECT id, hospital_name, city, state, postal_code, latitude, longitude
      FROM hospital_locations 
      WHERE (latitude = 0 OR longitude = 0 OR latitude IS NULL OR longitude IS NULL)
         OR hospital_name LIKE '% General Hospital'
      ORDER BY id
    `);

    this.stats.total_records = records.length;
    console.log(`  📊 Found ${records.length} records to update`);

    for (const record of records) {
      console.log(`  🔍 Processing: ${record.hospital_name} (${record.city})`);
      
      try {
        const realHospitalName = cityHospitalMap[record.city] || record.hospital_name;
        const locationData = await this.findHospitalLocation(realHospitalName, record.city, record.state);
        
        if (locationData) {
          await this.updateRecord(record.id, realHospitalName, locationData);
          this.stats.updated++;
          console.log(`    ✅ Updated: ${realHospitalName} → (${locationData.latitude}, ${locationData.longitude})`);
        } else {
          this.stats.failed++;
          console.log(`    ❌ Could not find coordinates`);
        }
      } catch (error) {
        this.stats.failed++;
        console.error(`    ❌ Error: ${error.message}`);
      }

      // Rate limiting
      await this.delay(300);
    }
  }

  async findHospitalLocation(hospitalName, city, state) {
    // Strategy 1: Try NPI API
    const npiResult = await this.searchNPI(hospitalName, state);
    if (npiResult && npiResult.latitude && npiResult.longitude) {
      return npiResult;
    }

    // Strategy 2: Try Google Geocoding
    const googleResult = await this.geocodeWithGoogle(hospitalName, city, state);
    if (googleResult && googleResult.latitude && googleResult.longitude) {
      return googleResult;
    }

    return null;
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
          address: result.formatted_address,
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

  async updateRecord(recordId, hospitalName, locationData) {
    await db.execute(`
      UPDATE hospital_locations 
      SET 
        hospital_name = ?,
        address = ?,
        city = ?,
        state = ?,
        postal_code = ?,
        latitude = ?,
        longitude = ?
      WHERE id = ?
    `, [
      hospitalName,
      locationData.address,
      locationData.city,
      locationData.state,
      locationData.postal_code,
      locationData.latitude,
      locationData.longitude,
      recordId
    ]);
  }

  async consolidateDuplicates() {
    console.log('\n🔄 Consolidating duplicates...');

    // Find duplicate hospital names and keep the one with the best data
    const [duplicates] = await db.query(`
      SELECT hospital_name, COUNT(*) as count, 
             GROUP_CONCAT(id ORDER BY 
               CASE WHEN latitude != 0 AND longitude != 0 THEN 1 ELSE 2 END,
               CASE WHEN address IS NOT NULL AND address != '' THEN 1 ELSE 2 END,
               id
             ) as ids
      FROM hospital_locations 
      GROUP BY hospital_name 
      HAVING COUNT(*) > 1
    `);

    for (const dup of duplicates) {
      const ids = dup.ids.split(',').map(id => parseInt(id));
      const keepId = ids[0]; // Keep the first (best) record
      const deleteIds = ids.slice(1); // Delete the rest

      // Update patients table to point to the kept record
      for (const deleteId of deleteIds) {
        await db.execute(`
          UPDATE patients 
          SET location_id = ? 
          WHERE location_id = ?
        `, [keepId, deleteId]);

        // Now safe to delete the duplicate
        await db.execute(`
          DELETE FROM hospital_locations WHERE id = ?
        `, [deleteId]);

        this.stats.duplicates_consolidated++;
      }

      console.log(`  ✅ Consolidated ${dup.hospital_name}: kept ID ${keepId}, removed ${deleteIds.length} duplicates`);
    }
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
    console.log(`  Duplicates consolidated: ${this.stats.duplicates_consolidated}`);

    // Save report
    const report = {
      timestamp: new Date().toISOString(),
      processing_stats: this.stats,
      final_stats: finalStats[0]
    };

    fs.writeFileSync(
      path.join(__dirname, 'safe_hospital_fix_report.json'),
      JSON.stringify(report, null, 2)
    );

    console.log(`\n📄 Report saved to: safe_hospital_fix_report.json`);
  }
}

// Main execution
async function main() {
  const fixer = new SafeHospitalLocationFixer();
  
  try {
    await fixer.fixHospitalLocations();
    process.exit(0);
  } catch (error) {
    console.error('❌ Safe hospital locations fix failed:', error);
    process.exit(1);
  }
}

if (require.main === module) {
  main();
}

module.exports = { SafeHospitalLocationFixer };
