// backend/api/scripts/check_hospital_locations_status.js
// Check current status of hospital_locations table and provide recommendations

const db = require('../../db');

class HospitalLocationStatusChecker {
  async checkStatus() {
    console.log('🔍 Checking Hospital Locations Status\n');

    try {
      // Get basic statistics
      const basicStats = await this.getBasicStatistics();
      
      // Get coordinate statistics
      const coordStats = await this.getCoordinateStatistics();
      
      // Get duplicate analysis
      const duplicateStats = await this.getDuplicateAnalysis();
      
      // Get hospital name analysis
      const nameStats = await this.getHospitalNameAnalysis();
      
      // Print comprehensive report
      this.printStatusReport(basicStats, coordStats, duplicateStats, nameStats);
      
      // Provide recommendations
      this.provideRecommendations(basicStats, coordStats, duplicateStats, nameStats);

    } catch (error) {
      console.error('❌ Error checking status:', error.message);
      throw error;
    }
  }

  async getBasicStatistics() {
    const [stats] = await db.query(`
      SELECT 
        COUNT(*) as total_records,
        COUNT(DISTINCT hospital_name) as unique_hospitals,
        COUNT(DISTINCT city) as unique_cities,
        COUNT(DISTINCT CONCAT(city, ', ', state)) as unique_locations
      FROM hospital_locations
    `);

    return stats[0];
  }

  async getCoordinateStatistics() {
    const [stats] = await db.query(`
      SELECT 
        COUNT(CASE WHEN latitude != 0 AND longitude != 0 THEN 1 END) as with_coordinates,
        COUNT(CASE WHEN latitude = 0 OR longitude = 0 THEN 1 END) as without_coordinates,
        COUNT(CASE WHEN latitude IS NULL OR longitude IS NULL THEN 1 END) as null_coordinates,
        ROUND(AVG(CASE WHEN latitude != 0 AND longitude != 0 THEN latitude END), 6) as avg_latitude,
        ROUND(AVG(CASE WHEN latitude != 0 AND longitude != 0 THEN longitude END), 6) as avg_longitude
      FROM hospital_locations
    `);

    return stats[0];
  }

  async getDuplicateAnalysis() {
    const [duplicates] = await db.query(`
      SELECT 
        hospital_name,
        COUNT(*) as count,
        GROUP_CONCAT(DISTINCT city ORDER BY city) as cities,
        GROUP_CONCAT(DISTINCT CONCAT(latitude, ',', longitude) ORDER BY latitude) as coordinates
      FROM hospital_locations 
      GROUP BY hospital_name 
      HAVING COUNT(*) > 1
      ORDER BY COUNT(*) DESC
      LIMIT 10
    `);

    return duplicates;
  }

  async getHospitalNameAnalysis() {
    const [genericNames] = await db.query(`
      SELECT 
        hospital_name,
        COUNT(*) as count
      FROM hospital_locations 
      WHERE hospital_name LIKE '% General Hospital'
      GROUP BY hospital_name
      ORDER BY COUNT(*) DESC
    `);

    const [realNames] = await db.query(`
      SELECT 
        hospital_name,
        COUNT(*) as count
      FROM hospital_locations 
      WHERE hospital_name NOT LIKE '% General Hospital'
         AND hospital_name NOT LIKE '%HOSPITAL%'
         AND hospital_name NOT LIKE '%HOSP%'
      GROUP BY hospital_name
      ORDER BY COUNT(*) DESC
      LIMIT 10
    `);

    return { genericNames, realNames };
  }

  printStatusReport(basicStats, coordStats, duplicateStats, nameStats) {
    console.log('📊 BASIC STATISTICS');
    console.log('==================');
    console.log(`Total records: ${basicStats.total_records}`);
    console.log(`Unique hospitals: ${basicStats.unique_hospitals}`);
    console.log(`Unique cities: ${basicStats.unique_cities}`);
    console.log(`Unique locations: ${basicStats.unique_locations}`);

    console.log('\n📍 COORDINATE STATISTICS');
    console.log('========================');
    console.log(`Records with coordinates: ${coordStats.with_coordinates}`);
    console.log(`Records without coordinates: ${coordStats.without_coordinates}`);
    console.log(`Records with NULL coordinates: ${coordStats.null_coordinates}`);
    console.log(`Average latitude: ${coordStats.avg_latitude || 'N/A'}`);
    console.log(`Average longitude: ${coordStats.avg_longitude || 'N/A'}`);

    if (duplicateStats.length > 0) {
      console.log('\n🔄 DUPLICATE HOSPITALS');
      console.log('=====================');
      duplicateStats.forEach((dup, index) => {
        console.log(`${index + 1}. ${dup.hospital_name} (${dup.count} records)`);
        console.log(`   Cities: ${dup.cities}`);
        console.log(`   Coordinates: ${dup.coordinates}`);
      });
    }

    if (nameStats.genericNames.length > 0) {
      console.log('\n🏥 GENERIC HOSPITAL NAMES');
      console.log('==========================');
      nameStats.genericNames.forEach((name, index) => {
        console.log(`${index + 1}. ${name.hospital_name} (${name.count} records)`);
      });
    }

    if (nameStats.realNames.length > 0) {
      console.log('\n✅ REAL HOSPITAL NAMES');
      console.log('======================');
      nameStats.realNames.forEach((name, index) => {
        console.log(`${index + 1}. ${name.hospital_name} (${name.count} records)`);
      });
    }
  }

  provideRecommendations(basicStats, coordStats, duplicateStats, nameStats) {
    console.log('\n💡 RECOMMENDATIONS');
    console.log('==================');

    const coordinateSuccessRate = (coordStats.with_coordinates / basicStats.total_records) * 100;
    const duplicateRate = (duplicateStats.length / basicStats.unique_hospitals) * 100;
    const genericNameRate = (nameStats.genericNames.length / basicStats.total_records) * 100;

    if (coordinateSuccessRate < 50) {
      console.log('🔴 HIGH PRIORITY: Coordinate success rate is very low');
      console.log('   → Run: node fix_hospital_locations.js (complete rebuild)');
      console.log('   → Or: node update_existing_locations.js (update existing)');
    } else if (coordinateSuccessRate < 80) {
      console.log('🟡 MEDIUM PRIORITY: Some records missing coordinates');
      console.log('   → Run: node update_existing_locations.js');
    } else {
      console.log('🟢 GOOD: Most records have coordinates');
    }

    if (duplicateRate > 20) {
      console.log('🔴 HIGH PRIORITY: High duplicate rate detected');
      console.log('   → Run: node fix_hospital_locations.js to deduplicate');
    } else if (duplicateRate > 10) {
      console.log('🟡 MEDIUM PRIORITY: Some duplicates found');
      console.log('   → Consider running deduplication script');
    } else {
      console.log('🟢 GOOD: Low duplicate rate');
    }

    if (genericNameRate > 50) {
      console.log('🔴 HIGH PRIORITY: Many generic hospital names');
      console.log('   → Run: node fix_hospital_locations.js to extract real names');
    } else if (genericNameRate > 20) {
      console.log('🟡 MEDIUM PRIORITY: Some generic names found');
      console.log('   → Consider updating hospital names');
    } else {
      console.log('🟢 GOOD: Most hospital names are specific');
    }

    console.log('\n📋 AVAILABLE SCRIPTS:');
    console.log('  • node check_hospital_locations_status.js - This status check');
    console.log('  • node fix_hospital_locations.js - Complete rebuild with real data');
    console.log('  • node update_existing_locations.js - Update existing records');
    console.log('  • node advanced_hospital_geocoder.js - Advanced geocoding');
    console.log('  • node filename_hospital_extractor.js - Extract from filenames');

    console.log('\n🎯 RECOMMENDED ACTION:');
    if (coordinateSuccessRate < 30) {
      console.log('   Run: node fix_hospital_locations.js');
    } else if (coordinateSuccessRate < 70) {
      console.log('   Run: node update_existing_locations.js');
    } else {
      console.log('   Data looks good! Consider running advanced geocoding for better accuracy.');
    }
  }
}

// Main execution
async function main() {
  const checker = new HospitalLocationStatusChecker();
  
  try {
    await checker.checkStatus();
    process.exit(0);
  } catch (error) {
    console.error('❌ Status check failed:', error);
    process.exit(1);
  }
}

if (require.main === module) {
  main();
}

module.exports = { HospitalLocationStatusChecker };
