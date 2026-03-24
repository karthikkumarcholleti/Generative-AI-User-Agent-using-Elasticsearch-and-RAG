// backend/api/scripts/run_comprehensive_geocoding.js
// Master script to run the complete hospital location detection pipeline

const { FilenameHospitalExtractor } = require('./filename_hospital_extractor');
const { AdvancedHospitalGeocoder } = require('./advanced_hospital_geocoder');
const fs = require('fs');
const path = require('path');

class ComprehensiveGeocodingPipeline {
  constructor() {
    this.extractor = new FilenameHospitalExtractor();
    this.geocoder = new AdvancedHospitalGeocoder();
  }

  async runCompletePipeline() {
    console.log('🚀 Starting Comprehensive Hospital Location Detection Pipeline\n');
    
    try {
      // Step 1: Extract hospital names from filenames
      console.log('📁 Step 1: Extracting hospital names from filenames...');
      const extractionResults = await this.extractHospitalsFromFilenames();
      
      // Step 2: Run advanced geocoding
      console.log('\n🌍 Step 2: Running advanced geocoding...');
      const geocodingResults = await this.runAdvancedGeocoding(extractionResults.hospitalList);
      
      // Step 3: Generate comprehensive report
      console.log('\n📊 Step 3: Generating comprehensive report...');
      await this.generateComprehensiveReport(extractionResults, geocodingResults);
      
      console.log('\n✅ Pipeline completed successfully!');
      
    } catch (error) {
      console.error('❌ Pipeline failed:', error.message);
      throw error;
    }
  }

  async extractHospitalsFromFilenames() {
    const dataDirectories = [
      'C:/Users/kasar/CoCM_Platform/UI Updates FHIR/backend/data/Converted_data/ADT',
      'C:/Users/kasar/CoCM_Platform/UI Updates FHIR/backend/data/Converted_data/CCDA',
      'C:/Users/kasar/CoCM_Platform/UI Updates FHIR/backend/data/Converted_data/ORU'
    ];

    let allResults = [];

    for (const directory of dataDirectories) {
      if (fs.existsSync(directory)) {
        console.log(`  📂 Processing: ${path.basename(directory)}`);
        const results = this.extractor.scanDirectory(directory);
        allResults = allResults.concat(results);
      } else {
        console.warn(`  ⚠️ Directory not found: ${directory}`);
      }
    }

    const hospitalList = this.extractor.generateHospitalList();
    const stats = this.extractor.generateStatistics(allResults);

    // Save extraction results
    const extractionOutput = path.join(__dirname, 'extraction_results.json');
    this.extractor.saveResults(extractionOutput, allResults, hospitalList, stats);

    console.log(`  ✅ Extracted ${hospitalList.length} unique hospitals from ${allResults.length} files`);
    
    return { hospitalList, stats, allResults };
  }

  async runAdvancedGeocoding(hospitalList) {
    // Convert hospital list to format expected by geocoder
    const hospitalsForGeocoding = hospitalList.map(h => ({
      hospital: h.hospital,
      address: h.address,
      lat: h.lat,
      lon: h.lon
    }));

    // Run geocoding
    for (const hospital of hospitalsForGeocoding) {
      await this.geocoder.processHospital(hospital);
    }

    // Save to database
    await this.geocoder.saveToDatabase();
    
    // Print statistics
    this.geocoder.printStats();

    return this.geocoder.results;
  }

  async generateComprehensiveReport(extractionResults, geocodingResults) {
    const report = {
      pipeline_info: {
        executed_at: new Date().toISOString(),
        version: '1.0.0',
        description: 'Comprehensive Hospital Location Detection Pipeline'
      },
      extraction_summary: {
        total_files_processed: extractionResults.allResults.length,
        unique_hospitals_found: extractionResults.hospitalList.length,
        extraction_success_rate: extractionResults.stats.extraction_success_rate,
        by_source_type: extractionResults.stats.by_source_type
      },
      geocoding_summary: {
        total_hospitals_processed: this.geocoder.stats.total,
        npi_matches_found: this.geocoder.stats.npiFound,
        successfully_geocoded: this.geocoder.stats.geocoded,
        failed_to_geocode: this.geocoder.stats.failed,
        success_rate: ((this.geocoder.stats.geocoded / this.geocoder.stats.total) * 100).toFixed(1) + '%'
      },
      data_quality: {
        high_confidence_locations: geocodingResults.filter(r => r.confidence >= 0.8).length,
        npi_sourced_locations: geocodingResults.filter(r => r.source === 'npi').length,
        google_sourced_locations: geocodingResults.filter(r => r.source === 'google').length,
        geographic_sourced_locations: geocodingResults.filter(r => r.source === 'geographic').length
      },
      recommendations: this.generateRecommendations(geocodingResults)
    };

    // Save comprehensive report
    const reportPath = path.join(__dirname, 'comprehensive_geocoding_report.json');
    fs.writeFileSync(reportPath, JSON.stringify(report, null, 2));
    
    console.log(`📄 Comprehensive report saved to: ${reportPath}`);
    
    // Print summary
    console.log('\n📋 Pipeline Summary:');
    console.log(`  Files processed: ${extractionResults.allResults.length}`);
    console.log(`  Unique hospitals: ${extractionResults.hospitalList.length}`);
    console.log(`  Successfully geocoded: ${this.geocoder.stats.geocoded}`);
    console.log(`  Success rate: ${((this.geocoder.stats.geocoded / this.geocoder.stats.total) * 100).toFixed(1)}%`);
    console.log(`  High confidence locations: ${report.data_quality.high_confidence_locations}`);
  }

  generateRecommendations(geocodingResults) {
    const recommendations = [];
    
    const failedHospitals = geocodingResults.filter(r => !r.latitude || !r.longitude);
    if (failedHospitals.length > 0) {
      recommendations.push({
        type: 'manual_review',
        priority: 'high',
        description: `${failedHospitals.length} hospitals could not be geocoded automatically`,
        hospitals: failedHospitals.map(h => h.hospital)
      });
    }

    const lowConfidenceHospitals = geocodingResults.filter(r => r.confidence < 0.6 && r.latitude && r.longitude);
    if (lowConfidenceHospitals.length > 0) {
      recommendations.push({
        type: 'verification',
        priority: 'medium',
        description: `${lowConfidenceHospitals.length} hospitals have low confidence scores and should be verified`,
        hospitals: lowConfidenceHospitals.map(h => h.hospital)
      });
    }

    const npiHospitals = geocodingResults.filter(r => r.source === 'npi');
    if (npiHospitals.length > 0) {
      recommendations.push({
        type: 'data_enrichment',
        priority: 'low',
        description: `${npiHospitals.length} hospitals have NPI data that could be used for additional enrichment`,
        suggestion: 'Consider using NPI data for additional hospital metadata like services, bed count, etc.'
      });
    }

    return recommendations;
  }
}

// Main execution
async function main() {
  const pipeline = new ComprehensiveGeocodingPipeline();
  
  try {
    await pipeline.runCompletePipeline();
    process.exit(0);
  } catch (error) {
    console.error('❌ Pipeline execution failed:', error);
    process.exit(1);
  }
}

if (require.main === module) {
  main();
}

module.exports = { ComprehensiveGeocodingPipeline };
