// backend/api/scripts/filename_hospital_extractor.js
// Extract hospital names from ADT/CCDA/ORU filenames and create comprehensive hospital list

const fs = require('fs');
const path = require('path');

class FilenameHospitalExtractor {
  constructor() {
    this.hospitals = new Set();
    this.patterns = {
      adt: /TEST_([A-Z_]+)_A\d+_\d+_fhir\.json$/i,
      ccda: /fhir_output_TEST_ccd_([a-z]+)_\d+\.json$/i,
      oru: /TEST_([A-Za-z_]+)_LAB_\d{4}-\d{2}-\d{2}-\d{2}-\d{2}-\d{2}-\d{3}_fhir\.json$/i
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

  extractFromADT(filename) {
    const match = filename.match(this.patterns.adt);
    if (match) {
      const code = match[1];
      return this.hospitalMappings[code] || this.expandHospitalCode(code);
    }
    return null;
  }

  extractFromCCDA(filename) {
    const match = filename.match(this.patterns.ccda);
    if (match) {
      const code = match[1];
      return this.hospitalMappings[code] || this.expandHospitalCode(code);
    }
    return null;
  }

  extractFromORU(filename) {
    const match = filename.match(this.patterns.oru);
    if (match) {
      const code = match[1];
      return this.hospitalMappings[code] || this.expandHospitalCode(code);
    }
    return null;
  }

  expandHospitalCode(code) {
    // Convert codes to readable names
    return code
      .replace(/_/g, ' ')
      .replace(/\b([A-Z])([A-Z]+)\b/g, (match, first, rest) => 
        first + rest.toLowerCase())
      .replace(/\b\w/g, l => l.toUpperCase());
  }

  determineSourceType(filename) {
    if (this.patterns.adt.test(filename)) return 'adt';
    if (this.patterns.ccda.test(filename)) return 'ccda';
    if (this.patterns.oru.test(filename)) return 'oru';
    return 'unknown';
  }

  processFile(filename) {
    const sourceType = this.determineSourceType(filename);
    let hospitalName = null;

    switch (sourceType) {
      case 'adt':
        hospitalName = this.extractFromADT(filename);
        break;
      case 'ccda':
        hospitalName = this.extractFromCCDA(filename);
        break;
      case 'oru':
        hospitalName = this.extractFromORU(filename);
        break;
    }

    if (hospitalName) {
      this.hospitals.add(hospitalName);
      return {
        filename,
        sourceType,
        hospitalName,
        extracted: true
      };
    }

    return {
      filename,
      sourceType,
      hospitalName: null,
      extracted: false
    };
  }

  scanDirectory(directoryPath) {
    console.log(`🔍 Scanning directory: ${directoryPath}`);
    
    if (!fs.existsSync(directoryPath)) {
      console.error(`❌ Directory not found: ${directoryPath}`);
      return [];
    }

    const results = [];
    const files = this.getAllJsonFiles(directoryPath);
    
    console.log(`📁 Found ${files.length} JSON files to process`);

    for (const filePath of files) {
      const filename = path.basename(filePath);
      const result = this.processFile(filename);
      results.push(result);
      
      if (result.extracted) {
        console.log(`✅ ${filename} → ${result.hospitalName} (${result.sourceType})`);
      } else {
        console.log(`⚠️ ${filename} → No hospital extracted (${result.sourceType})`);
      }
    }

    return results;
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

  generateHospitalList() {
    const hospitalArray = Array.from(this.hospitals).map(name => ({
      hospital: name,
      address: null,
      lat: null,
      lon: null,
      source_types: [],
      file_count: 0
    }));

    return hospitalArray.sort((a, b) => a.hospital.localeCompare(b.hospital));
  }

  generateStatistics(results) {
    const stats = {
      total_files: results.length,
      extracted_hospitals: this.hospitals.size,
      by_source_type: {
        adt: results.filter(r => r.sourceType === 'adt').length,
        ccda: results.filter(r => r.sourceType === 'ccda').length,
        oru: results.filter(r => r.sourceType === 'oru').length,
        unknown: results.filter(r => r.sourceType === 'unknown').length
      },
      extraction_success_rate: (results.filter(r => r.extracted).length / results.length * 100).toFixed(1)
    };

    return stats;
  }

  saveResults(outputPath, results, hospitalList, stats) {
    const output = {
      metadata: {
        generated_at: new Date().toISOString(),
        total_files_processed: results.length,
        unique_hospitals_found: this.hospitals.size,
        statistics: stats
      },
      hospitals: hospitalList,
      file_analysis: results
    };

    fs.writeFileSync(outputPath, JSON.stringify(output, null, 2));
    console.log(`📄 Results saved to: ${outputPath}`);
  }
}

// Main execution function
async function main() {
  const extractor = new FilenameHospitalExtractor();
  
  // Define data directories
  const dataDirectories = [
    'C:/Users/kasar/CoCM_Platform/UI Updates FHIR/backend/data/Converted_data/ADT',
    'C:/Users/kasar/CoCM_Platform/UI Updates FHIR/backend/data/Converted_data/CCDA',
    'C:/Users/kasar/CoCM_Platform/UI Updates FHIR/backend/data/Converted_data/ORU'
  ];

  let allResults = [];

  // Process each directory
  for (const directory of dataDirectories) {
    if (fs.existsSync(directory)) {
      const results = extractor.scanDirectory(directory);
      allResults = allResults.concat(results);
    } else {
      console.warn(`⚠️ Directory not found: ${directory}`);
    }
  }

  // Generate final results
  const hospitalList = extractor.generateHospitalList();
  const stats = extractor.generateStatistics(allResults);

  // Save results
  const outputPath = path.join(__dirname, 'extracted_hospitals_comprehensive.json');
  extractor.saveResults(outputPath, allResults, hospitalList, stats);

  // Print summary
  console.log('\n📊 Extraction Summary:');
  console.log(`Total files processed: ${stats.total_files}`);
  console.log(`Unique hospitals found: ${stats.extracted_hospitals}`);
  console.log(`Extraction success rate: ${stats.extraction_success_rate}%`);
  console.log('\nBy source type:');
  Object.entries(stats.by_source_type).forEach(([type, count]) => {
    console.log(`  ${type.toUpperCase()}: ${count} files`);
  });

  console.log('\n🏥 Extracted Hospitals:');
  hospitalList.forEach((hospital, index) => {
    console.log(`  ${index + 1}. ${hospital.hospital}`);
  });

  return { hospitalList, stats, allResults };
}

if (require.main === module) {
  main().catch(console.error);
}

module.exports = { FilenameHospitalExtractor };
