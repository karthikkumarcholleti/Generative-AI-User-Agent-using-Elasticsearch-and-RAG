const db = require('../../db');

class ConditionDisplayImprover {
  constructor() {
    this.updatedCount = 0;
    this.skippedCount = 0;
    this.errorCount = 0;
  }

  /**
   * Enhanced manual mapping for common conditions
   */
  getEnhancedMappings() {
    return {
      // SNOMED CT codes
      '38341003': 'Essential Hypertension',
      '44054006': 'Type 2 Diabetes Mellitus',
      '195967001': 'Bronchial Asthma',
      '13645005': 'Chronic Obstructive Pulmonary Disease',
      '55822004': 'Major Depressive Disorder',
      '197480006': 'Anxiety Disorder',
      '56265001': 'Heart Disease',
      '363346000': 'Malignant Neoplasm',
      '709044004': 'Chronic Kidney Disease',
      '64859006': 'Osteoporosis',
      '26929004': 'Alzheimer Disease',
      '49049000': 'Parkinson Disease',
      '24700007': 'Multiple Sclerosis',
      '203082005': 'Fibromyalgia',
      '414916001': 'Obesity',
      '35489007': 'Depression',
      '3723001': 'Arthritis',
      '230690007': 'Cerebrovascular Accident',
      '230265000': 'Epilepsy',
      '439401001': 'Osteoarthritis',
      '396332003': 'Rheumatoid Arthritis',
      '235595009': 'Crohn Disease',
      '236423003': 'Chronic Kidney Disease',
      '237599002': 'Hypothyroidism',
      
      // ICD-10 codes
      'E11.9': 'Type 2 Diabetes Mellitus',
      'I10': 'Essential Hypertension',
      'J44.1': 'Chronic Obstructive Pulmonary Disease',
      'F32.9': 'Major Depressive Disorder',
      'F41.9': 'Anxiety Disorder',
      'I25.9': 'Chronic Ischemic Heart Disease',
      'N18.6': 'End Stage Renal Disease',
      'M81.0': 'Osteoporosis',
      'G30.9': 'Alzheimer Disease',
      'G20': 'Parkinson Disease',
      'G35': 'Multiple Sclerosis',
      'M79.3': 'Fibromyalgia',
      'E66.9': 'Obesity',
      'M19.9': 'Osteoarthritis',
      'M06.9': 'Rheumatoid Arthritis',
      'K50.9': 'Crohn Disease',
      'E03.9': 'Hypothyroidism'
    };
  }

  /**
   * Clean up text descriptions
   */
  cleanTextDescription(text) {
    if (!text) return text;
    
    let cleaned = text
      .replace(/^\^+/, '') // Remove leading ^ symbols
      .replace(/\^ICD10$/, '') // Remove ICD10 suffix
      .replace(/\^+$/, '') // Remove trailing ^ symbols
      .replace(/^[A-Z]\d{2}\.?\d*\s*-\s*/, '') // Remove ICD-10 code prefixes
      .replace(/\([^)]*\)/g, '') // Remove parenthetical content
      .replace(/\s+/g, ' ') // Normalize whitespace
      .trim();
    
    // Capitalize first letter
    if (cleaned.length > 0) {
      cleaned = cleaned.charAt(0).toUpperCase() + cleaned.slice(1);
    }
    
    return cleaned;
  }

  /**
   * Get better display name for a condition
   */
  getBetterDisplayName(code, currentDisplay) {
    const mappings = this.getEnhancedMappings();
    
    // First try exact code match
    if (mappings[code]) {
      return mappings[code];
    }
    
    // Clean up text descriptions
    if (code && !/^\d+$/.test(code)) {
      const cleaned = this.cleanTextDescription(code);
      if (cleaned && cleaned !== code && cleaned.length > 2) {
        return cleaned;
      }
    }
    
    // Clean up current display
    if (currentDisplay && currentDisplay !== code) {
      const cleaned = this.cleanTextDescription(currentDisplay);
      if (cleaned && cleaned !== currentDisplay && cleaned.length > 2) {
        return cleaned;
      }
    }
    
    return null; // No improvement found
  }

  /**
   * Update a single condition
   */
  async updateCondition(code, newDisplay, newStatus) {
    try {
      const [result] = await db.query(`
        UPDATE conditions 
        SET display = ?, clinical_status = ?
        WHERE code = ?
      `, [newDisplay, newStatus, code]);
      
      return result.affectedRows > 0;
    } catch (error) {
      console.error(`❌ Database error updating ${code}:`, error.message);
      return false;
    }
  }

  /**
   * Process all conditions
   */
  async improveAllConditions() {
    try {
      console.log('🚀 Starting condition display improvement...\n');
      
      // Get all conditions
      const [conditions] = await db.query(`
        SELECT DISTINCT code, display, clinical_status
        FROM conditions 
        WHERE code IS NOT NULL 
        AND code != ''
        ORDER BY code
      `);
      
      console.log(`📊 Processing ${conditions.length} conditions...\n`);
      
      for (let i = 0; i < conditions.length; i++) {
        const condition = conditions[i];
        const progress = Math.floor((i / conditions.length) * 100);
        
        if (i % 100 === 0) {
          console.log(`📈 Progress: ${i}/${conditions.length} (${progress}%)`);
        }
        
        try {
          const betterDisplay = this.getBetterDisplayName(condition.code, condition.display);
          
          if (betterDisplay) {
            const success = await this.updateCondition(
              condition.code, 
              betterDisplay, 
              condition.clinical_status || 'unknown'
            );
            
            if (success) {
              this.updatedCount++;
              if (this.updatedCount % 50 === 0) {
                console.log(`✅ Updated ${this.updatedCount} conditions so far...`);
              }
            }
          } else {
            this.skippedCount++;
          }
        } catch (error) {
          console.error(`❌ Error processing ${condition.code}:`, error.message);
          this.errorCount++;
        }
      }
      
      // Final statistics
      console.log('\n📊 IMPROVEMENT COMPLETE!');
      console.log(`✅ Successfully updated: ${this.updatedCount} conditions`);
      console.log(`⚠️ Skipped (no improvement): ${this.skippedCount} conditions`);
      console.log(`❌ Errors encountered: ${this.errorCount} conditions`);
      
      // Show some examples
      await this.showUpdatedExamples();
      
    } catch (error) {
      console.error('❌ Fatal error during improvement:', error);
    } finally {
      process.exit(0);
    }
  }

  /**
   * Show examples of updated conditions
   */
  async showUpdatedExamples() {
    console.log('\n📋 SAMPLE IMPROVED CONDITIONS:');
    
    const [examples] = await db.query(`
      SELECT code, display, clinical_status
      FROM conditions 
      WHERE display IS NOT NULL 
      AND display != code
      AND display != ''
      ORDER BY RAND()
      LIMIT 15
    `);
    
    examples.forEach((condition, index) => {
      console.log(`${index + 1}. Code: ${condition.code}`);
      console.log(`   Display: "${condition.display}"`);
      console.log(`   Status: ${condition.clinical_status}`);
      console.log('');
    });
  }
}

// Main execution
async function main() {
  const improver = new ConditionDisplayImprover();
  await improver.improveAllConditions();
}

// Run if called directly
if (require.main === module) {
  main().catch(console.error);
}

module.exports = ConditionDisplayImprover;
