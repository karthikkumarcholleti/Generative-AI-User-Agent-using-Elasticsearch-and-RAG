// backend/api/scripts/advanced_hospital_geocoder.js
// Comprehensive hospital location detection using multiple strategies

const fs = require('fs');
const path = require('path');
const axios = require('axios');
const db = require('../../db');
const dotenv = require('dotenv');
dotenv.config();

// Configuration
const CONFIG = {
  NPI_API_DELAY: 300, // ms between NPI API calls
  GOOGLE_API_DELAY: 250, // ms between Google API calls
  MAX_RETRIES: 3,
  MIN_CONFIDENCE_SCORE: 0.6,
  GEOGRAPHIC_BOUNDS: {
    // Michigan bounds (adjust based on your data)
    north: 48.2,
    south: 41.7,
    east: -82.1,
    west: -90.4
  }
};

// Hospital name normalization and matching
class HospitalNameMatcher {
  static normalize(name) {
    return (name || '')
      .toLowerCase()
      .replace(/[^\w\s]/g, ' ')
      .replace(/\s+/g, ' ')
      .trim();
  }

  static generateVariants(original) {
    const variants = new Set([original]);
    const base = original.trim();
    
    // Common hospital name variations
    const patterns = [
      { from: /\bSt\.\b/g, to: 'Saint' },
      { from: /\bSt\b/g, to: 'Saint' },
      { from: /-/, to: ' ' },
      { from: /\bHosp\b/g, to: 'Hospital' },
      { from: /\bMed\b/g, to: 'Medical' },
      { from: /\bCtr\b/g, to: 'Center' },
      { from: /\bCtr\.\b/g, to: 'Center' },
      { from: /\bSys\b/g, to: 'System' },
      { from: /\bSys\.\b/g, to: 'System' }
    ];

    patterns.forEach(pattern => {
      variants.add(base.replace(pattern.from, pattern.to));
    });

    // Add/remove common suffixes
    const suffixes = ['Hospital', 'Medical Center', 'Health System', 'Clinic', 'Healthcare'];
    suffixes.forEach(suffix => {
      if (!base.toLowerCase().includes(suffix.toLowerCase())) {
        variants.add(`${base} ${suffix}`);
      }
    });

    return Array.from(variants).filter(Boolean);
  }

  static calculateSimilarity(str1, str2) {
    const s1 = this.normalize(str1);
    const s2 = this.normalize(str2);
    
    if (s1 === s2) return 1.0;
    
    // Jaccard similarity
    const words1 = new Set(s1.split(' '));
    const words2 = new Set(s2.split(' '));
    const intersection = new Set([...words1].filter(x => words2.has(x)));
    const union = new Set([...words1, ...words2]);
    
    return intersection.size / union.size;
  }
}

// NPI API integration with advanced search strategies
class NPILocationFinder {
  static async searchByOrganizationName(orgName, state = null) {
    const params = new URLSearchParams({
      version: '2.1',
      enumeration_type: 'NPI-2',
      organization_name: orgName,
      limit: '50'
    });
    
    if (state) params.append('state', state);
    
    const url = `https://npiregistry.cms.hhs.gov/api/?${params.toString()}`;
    
    try {
      const response = await axios.get(url, { timeout: 10000 });
      return response.data.results || [];
    } catch (error) {
      console.warn(`⚠️ NPI API error for "${orgName}":`, error.message);
      return [];
    }
  }

  static async searchByGeographicArea(city, state, radius = 50) {
    const params = new URLSearchParams({
      version: '2.1',
      enumeration_type: 'NPI-2',
      city: city,
      state: state,
      limit: '100'
    });
    
    const url = `https://npiregistry.cms.hhs.gov/api/?${params.toString()}`;
    
    try {
      const response = await axios.get(url, { timeout: 10000 });
      return response.data.results || [];
    } catch (error) {
      console.warn(`⚠️ NPI geographic search error for ${city}, ${state}:`, error.message);
      return [];
    }
  }

  static findBestMatch(hospitalName, results) {
    let bestMatch = null;
    let bestScore = 0;

    for (const result of results) {
      const orgName = result?.basic?.organization_name || 
                     result?.basic?.name || 
                     result?.basic?.authorized_official_organization_name || '';
      
      const score = HospitalNameMatcher.calculateSimilarity(hospitalName, orgName);
      
      if (score > bestScore && score >= CONFIG.MIN_CONFIDENCE_SCORE) {
        bestMatch = result;
        bestScore = score;
      }
    }

    return { match: bestMatch, score: bestScore };
  }

  static extractLocationData(npiResult) {
    if (!npiResult) return null;

    const addresses = npiResult.addresses || [];
    const locationAddress = addresses.find(addr => addr.address_purpose === 'LOCATION') ||
                           addresses.find(addr => addr.address_purpose === 'PRIMARY') ||
                           addresses[0];

    if (!locationAddress) return null;

    return {
      npi: npiResult.number,
      organization_name: npiResult.basic?.organization_name || npiResult.basic?.name,
      address: locationAddress.address_1,
      city: locationAddress.city,
      state: locationAddress.state,
      postal_code: locationAddress.postal_code,
      latitude: locationAddress.latitude ? parseFloat(locationAddress.latitude) : null,
      longitude: locationAddress.longitude ? parseFloat(locationAddress.longitude) : null,
      phone: locationAddress.telephone_number,
      taxonomy: npiResult.taxonomies?.[0]?.desc || null
    };
  }
}

// Google Maps Geocoding with fallback strategies
class GoogleGeocoder {
  static async geocodeAddress(addressComponents) {
    const { address, city, state, postal_code } = addressComponents;
    
    // Try different address formats
    const addressFormats = [
      `${address}, ${city}, ${state} ${postal_code}`,
      `${city}, ${state} ${postal_code}`,
      `${city}, ${state}`,
      `${address}, ${city}, ${state}`
    ];

    for (const addressFormat of addressFormats) {
      try {
        const coords = await this.geocodeSingleAddress(addressFormat);
        if (coords && this.isValidCoordinate(coords)) {
          return coords;
        }
      } catch (error) {
        console.warn(`⚠️ Geocoding failed for "${addressFormat}":`, error.message);
      }
    }

    return null;
  }

  static async geocodeSingleAddress(address) {
    const url = `https://maps.googleapis.com/maps/api/geocode/json?address=${encodeURIComponent(address)}&key=${process.env.GOOGLE_MAPS_API_KEY}`;
    
    const response = await axios.get(url, { timeout: 10000 });
    const data = response.data;

    if (data.status === 'OK' && data.results.length > 0) {
      const location = data.results[0].geometry.location;
      return {
        latitude: location.lat,
        longitude: location.lng,
        formatted_address: data.results[0].formatted_address,
        confidence: this.calculateConfidence(data.results[0])
      };
    }

    return null;
  }

  static calculateConfidence(geocodeResult) {
    const types = geocodeResult.types || [];
    const addressComponents = geocodeResult.address_components || [];
    
    let confidence = 0.5; // base confidence
    
    // Increase confidence based on result type
    if (types.includes('hospital')) confidence += 0.3;
    if (types.includes('health')) confidence += 0.2;
    if (types.includes('establishment')) confidence += 0.1;
    
    // Increase confidence based on address components
    const hasStreetNumber = addressComponents.some(comp => comp.types.includes('street_number'));
    const hasRoute = addressComponents.some(comp => comp.types.includes('route'));
    
    if (hasStreetNumber && hasRoute) confidence += 0.2;
    else if (hasRoute) confidence += 0.1;
    
    return Math.min(confidence, 1.0);
  }

  static isValidCoordinate(coords) {
    if (!coords || !coords.latitude || !coords.longitude) return false;
    
    const { latitude, longitude } = coords;
    const bounds = CONFIG.GEOGRAPHIC_BOUNDS;
    
    return latitude >= bounds.south && latitude <= bounds.north &&
           longitude >= bounds.west && longitude <= bounds.east;
  }
}

// Main geocoding orchestrator
class AdvancedHospitalGeocoder {
  constructor() {
    this.results = [];
    this.stats = {
      total: 0,
      npiFound: 0,
      geocoded: 0,
      failed: 0,
      skipped: 0
    };
  }

  async processHospital(hospital) {
    console.log(`🔍 Processing: ${hospital.hospital}`);
    this.stats.total++;

    let result = {
      hospital: hospital.hospital,
      npi: null,
      organization_name: null,
      address: null,
      city: null,
      state: null,
      postal_code: null,
      latitude: null,
      longitude: null,
      phone: null,
      taxonomy: null,
      confidence: 0,
      source: 'none',
      error: null
    };

    try {
      // Strategy 1: Try NPI API with name variants
      const npiResult = await this.tryNPISearch(hospital.hospital);
      if (npiResult) {
        Object.assign(result, npiResult);
        result.source = 'npi';
        this.stats.npiFound++;
      }

      // Strategy 2: If no coordinates from NPI, try Google Geocoding
      if (!result.latitude || !result.longitude) {
        const geocodeResult = await this.tryGoogleGeocoding(result);
        if (geocodeResult) {
          result.latitude = geocodeResult.latitude;
          result.longitude = geocodeResult.longitude;
          result.confidence = geocodeResult.confidence;
          if (result.source === 'none') result.source = 'google';
        }
      }

      // Strategy 3: If still no coordinates, try geographic search
      if (!result.latitude || !result.longitude) {
        const geoResult = await this.tryGeographicSearch(hospital.hospital);
        if (geoResult) {
          Object.assign(result, geoResult);
          result.source = 'geographic';
        }
      }

      if (result.latitude && result.longitude) {
        this.stats.geocoded++;
        console.log(`✅ Found: ${result.hospital} → (${result.latitude.toFixed(4)}, ${result.longitude.toFixed(4)}) [${result.source}]`);
      } else {
        this.stats.failed++;
        console.log(`❌ Failed: ${result.hospital}`);
      }

    } catch (error) {
      result.error = error.message;
      this.stats.failed++;
      console.error(`❌ Error processing ${hospital.hospital}:`, error.message);
    }

    this.results.push(result);
    await this.delay(CONFIG.NPI_API_DELAY);
  }

  async tryNPISearch(hospitalName) {
    const variants = HospitalNameMatcher.generateVariants(hospitalName);
    
    for (const variant of variants) {
      const results = await NPILocationFinder.searchByOrganizationName(variant);
      if (results.length > 0) {
        const { match, score } = NPILocationFinder.findBestMatch(hospitalName, results);
        if (match) {
          const locationData = NPILocationFinder.extractLocationData(match);
          if (locationData) {
            locationData.confidence = score;
            return locationData;
          }
        }
      }
      await this.delay(CONFIG.NPI_API_DELAY);
    }
    
    return null;
  }

  async tryGoogleGeocoding(hospitalData) {
    if (!hospitalData.address || !hospitalData.city || !hospitalData.state) {
      return null;
    }

    return await GoogleGeocoder.geocodeAddress(hospitalData);
  }

  async tryGeographicSearch(hospitalName) {
    // Extract potential city/state from hospital name
    const cityStateMatch = hospitalName.match(/(\w+)\s+(Hospital|Medical|Health|Clinic)/i);
    if (!cityStateMatch) return null;

    const potentialCity = cityStateMatch[1];
    const results = await NPILocationFinder.searchByGeographicArea(potentialCity, 'MI');
    
    if (results.length > 0) {
      const { match, score } = NPILocationFinder.findBestMatch(hospitalName, results);
      if (match && score >= 0.4) {
        const locationData = NPILocationFinder.extractLocationData(match);
        if (locationData) {
          locationData.confidence = score * 0.8; // Lower confidence for geographic search
          return locationData;
        }
      }
    }

    return null;
  }

  async delay(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  async saveToDatabase() {
    console.log('\n💾 Saving results to database...');
    
    await db.execute(`
      CREATE TABLE IF NOT EXISTS hospital_locations_advanced (
        id INT AUTO_INCREMENT PRIMARY KEY,
        hospital_name VARCHAR(255) NOT NULL,
        npi VARCHAR(20),
        organization_name VARCHAR(255),
        address VARCHAR(255),
        city VARCHAR(100),
        state VARCHAR(50),
        postal_code VARCHAR(20),
        latitude DECIMAL(10,8),
        longitude DECIMAL(11,8),
        phone VARCHAR(20),
        taxonomy VARCHAR(255),
        confidence DECIMAL(3,2),
        source VARCHAR(20),
        error TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
      )
    `);

    await db.execute('TRUNCATE TABLE hospital_locations_advanced');

    for (const result of this.results) {
      if (result.latitude && result.longitude) {
        await db.execute(`
          INSERT INTO hospital_locations_advanced 
          (hospital_name, npi, organization_name, address, city, state, postal_code, 
           latitude, longitude, phone, taxonomy, confidence, source, error)
          VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        `, [
          result.hospital, result.npi, result.organization_name, result.address,
          result.city, result.state, result.postal_code, result.latitude,
          result.longitude, result.phone, result.taxonomy, result.confidence,
          result.source, result.error
        ]);
      }
    }

    console.log(`✅ Saved ${this.results.filter(r => r.latitude && r.longitude).length} locations to database`);
  }

  printStats() {
    console.log('\n📊 Processing Statistics:');
    console.log(`Total hospitals processed: ${this.stats.total}`);
    console.log(`NPI API matches found: ${this.stats.npiFound}`);
    console.log(`Successfully geocoded: ${this.stats.geocoded}`);
    console.log(`Failed to geocode: ${this.stats.failed}`);
    console.log(`Success rate: ${((this.stats.geocoded / this.stats.total) * 100).toFixed(1)}%`);
  }
}

// Main execution
async function main() {
  if (!process.env.GOOGLE_MAPS_API_KEY) {
    console.error('❌ Missing GOOGLE_MAPS_API_KEY in .env');
    process.exit(1);
  }

  const inputFile = path.join(__dirname, 'hospital_locations.json');
  
  if (!fs.existsSync(inputFile)) {
    console.error(`❌ Input file not found: ${inputFile}`);
    process.exit(1);
  }

  const hospitals = JSON.parse(fs.readFileSync(inputFile, 'utf8'));
  const geocoder = new AdvancedHospitalGeocoder();

  console.log(`🚀 Starting advanced geocoding for ${hospitals.length} hospitals...\n`);

  for (const hospital of hospitals) {
    await geocoder.processHospital(hospital);
  }

  await geocoder.saveToDatabase();
  geocoder.printStats();

  // Save detailed results to JSON
  const outputFile = path.join(__dirname, 'hospital_locations_advanced.json');
  fs.writeFileSync(outputFile, JSON.stringify(geocoder.results, null, 2));
  console.log(`📄 Detailed results saved to: ${outputFile}`);

  process.exit(0);
}

if (require.main === module) {
  main().catch(console.error);
}

module.exports = { AdvancedHospitalGeocoder, NPILocationFinder, GoogleGeocoder };
