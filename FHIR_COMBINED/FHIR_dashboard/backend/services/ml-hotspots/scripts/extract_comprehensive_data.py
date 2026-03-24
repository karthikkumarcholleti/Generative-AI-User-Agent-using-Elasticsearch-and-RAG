"""
Comprehensive Data Extraction Script
Extracts data useful for BOTH spatial and temporal analysis
- Spatial: conditions + hospital locations (current focus)
- Temporal: observations with real dates (future use)
"""

import mysql.connector
import os
from dotenv import load_dotenv
import pandas as pd
from datetime import datetime
import re

# Load environment variables
load_dotenv()

# Database connection parameters
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'user': os.getenv('DB_USER', 'root'),
    'password': os.getenv('DB_PASSWORD', 'P@ssw0rd'),
    'database': os.getenv('DB_NAME', 'cocm_db_test')
}

def connect_db():
    """Establish read-only database connection"""
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        print(f"✅ Connected to database: {DB_CONFIG['database']}")
        return conn
    except mysql.connector.Error as err:
        print(f"❌ Error connecting to database: {err}")
        return None

def extract_date_from_filename(filename):
    """Extract date from filename for spatial analysis"""
    if pd.isna(filename):
        return None
    try:
        match = re.search(r'(\d{8})\d{6}', str(filename))
        if match:
            date_str = match.group(1)
            return pd.to_datetime(date_str, format='%Y%m%d')
        return None
    except:
        return None

def extract_comprehensive_data(conn):
    """
    Extract comprehensive data for both spatial and temporal analysis
    - Primary: Conditions data (for spatial clustering)
    - Secondary: Observations data (for future temporal analysis)
    """
    print("\n" + "="*70)
    print("📥 EXTRACTING COMPREHENSIVE DATA FOR SPATIAL & TEMPORAL ANALYSIS")
    print("="*70)
    
    # Comprehensive SQL query
    query = """
    SELECT 
        -- Condition information (PRIMARY - for spatial analysis)
        c.code AS condition_code,
        c.display AS condition_display,
        c.clinical_status,
        c.filename,
        c.created_at,
        
        -- Patient information
        p.patient_id,
        p.given_name,
        p.family_name,
        p.birth_date,
        p.gender,
        p.city AS patient_city,
        p.state AS patient_state,
        p.postal_code AS patient_zip,
        
        -- Hospital/Location information
        h.id AS hospital_id,
        h.hospital_name,
        h.city AS hospital_city,
        h.state AS hospital_state,
        h.postal_code AS hospital_zip,
        h.latitude,
        h.longitude,
        
        -- Encounter information
        e.id AS encounter_id,
        e.date AS encounter_date,
        e.class_display AS encounter_class,
        e.type_display AS encounter_type,
        e.admission_reason,
        
        -- Observation information (SECONDARY - for future temporal analysis)
        o.effectiveDateTime AS observation_date,
        o.code AS observation_code,
        o.display AS observation_display,
        o.value_numeric AS observation_value_numeric,
        o.value_string AS observation_value_string,
        o.unit AS observation_unit
        
    FROM conditions c
    
    -- Join patient information
    INNER JOIN patients p 
        ON c.patient_id = p.patient_id
    
    -- Join hospital location
    LEFT JOIN hospital_locations h 
        ON p.location_id = h.id
    
    -- Join encounter information
    LEFT JOIN encounters e 
        ON c.patient_id = e.patient_id
    
    -- Join observations (for future temporal analysis)
    LEFT JOIN observations o 
        ON c.patient_id = o.patient_id
    
    WHERE 
        -- Filter for communicable diseases
        c.code REGEXP '^[JAB][0-9]'
        -- Must have valid coordinates for spatial analysis
        AND h.latitude IS NOT NULL
        AND h.longitude IS NOT NULL
        -- Must have filename for date extraction
        AND c.filename IS NOT NULL
    
    ORDER BY c.filename DESC, h.hospital_name, o.effectiveDateTime DESC
    """
    
    print(f"\n🔍 Executing comprehensive extraction query...")
    print(f"📊 Query includes:")
    print(f"   - Conditions (primary data)")
    print(f"   - Hospital locations with coordinates")
    print(f"   - Patient demographics")
    print(f"   - Encounter details")
    print(f"   - Observations with dates (for future temporal analysis)")
    print(f"   - ICD-10 codes: J00-J99, A00-B99 (communicable diseases)")
    
    try:
        df = pd.read_sql(query, conn)
        print(f"\n✅ Extraction successful!")
        print(f"   Records extracted: {len(df):,}")
        print(f"   Columns: {len(df.columns)}")
        
        return df
        
    except Exception as e:
        print(f"❌ Error during extraction: {e}")
        return None

def enrich_dataset(df):
    """Enrich dataset with calculated fields"""
    print(f"\n🔧 Enriching dataset...")
    
    # Calculate age
    df['birth_date'] = pd.to_datetime(df['birth_date'], errors='coerce')
    current_date = pd.Timestamp.now()
    df['age'] = ((current_date - df['birth_date']).dt.days / 365.25).round(1)
    
    # Extract date from filename for spatial analysis
    df['event_date'] = df['filename'].apply(extract_date_from_filename)
    
    # Add temporal fields (for future use)
    df['year'] = df['event_date'].dt.year
    df['week'] = df['event_date'].dt.isocalendar().week
    df['month'] = df['event_date'].dt.month
    df['day_of_week'] = df['event_date'].dt.dayofweek
    
    # Clean disease codes
    df['condition_code_clean'] = df['condition_code'].str.split('^').str[0].str.strip()
    df['condition_display_clean'] = df['condition_display'].str.split('^').str[0].str.strip()
    
    # Categorize diseases
    def categorize_disease(code):
        if pd.isna(code):
            return 'Unknown'
        code = str(code).upper()
        if code.startswith('J'):
            return 'Respiratory'
        elif code.startswith('A'):
            return 'Infectious'
        elif code.startswith('B'):
            return 'Parasitic'
        else:
            return 'Other'
    
    df['disease_category'] = df['condition_code_clean'].apply(categorize_disease)
    
    print(f"✅ Dataset enriched with:")
    print(f"   - Age calculations")
    print(f"   - Date extraction from filenames")
    print(f"   - Disease categorization")
    print(f"   - Temporal fields for future analysis")
    
    return df

def save_results(df, filename='comprehensive_disease_data.csv'):
    """Save comprehensive dataset"""
    print(f"\n💾 Saving comprehensive dataset...")
    
    # Save full dataset
    df.to_csv(filename, index=False)
    print(f"✅ Saved: {filename}")
    print(f"   Records: {len(df):,}")
    print(f"   File size: {os.path.getsize(filename) / 1024:.1f} KB")
    
    # Create summary
    summary = {
        'total_records': len(df),
        'unique_patients': df['patient_id'].nunique(),
        'unique_hospitals': df['hospital_name'].nunique(),
        'disease_categories': df['disease_category'].value_counts().to_dict(),
        'date_range': f"{df['event_date'].min()} to {df['event_date'].max()}" if not df['event_date'].isna().all() else "No valid dates",
        'observations_with_dates': df['observation_date'].notna().sum(),
        'extraction_timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    
    print(f"\n📊 Dataset Summary:")
    print(f"   Total records: {summary['total_records']:,}")
    print(f"   Unique patients: {summary['unique_patients']:,}")
    print(f"   Unique hospitals: {summary['unique_hospitals']:,}")
    print(f"   Disease categories: {summary['disease_categories']}")
    print(f"   Observations with dates: {summary['observations_with_dates']:,}")
    print(f"   Date range: {summary['date_range']}")
    
    return summary

def main():
    """Main execution function"""
    print("🚀 Starting Comprehensive Data Extraction")
    print("="*50)
    
    # Connect to database
    conn = connect_db()
    if not conn:
        return
    
    try:
        # Extract comprehensive data
        df = extract_comprehensive_data(conn)
        if df is None or df.empty:
            print("❌ No data extracted")
            return
        
        # Enrich dataset
        df = enrich_dataset(df)
        
        # Save results
        summary = save_results(df)
        
        print(f"\n🎯 EXTRACTION COMPLETE!")
        print(f"✅ Ready for spatial analysis (current focus)")
        print(f"✅ Ready for temporal analysis (when dates fixed)")
        print(f"✅ Comprehensive dataset saved")
        
    except Exception as e:
        print(f"❌ Error in main execution: {e}")
    
    finally:
        conn.close()
        print(f"\n🔌 Database connection closed")

if __name__ == "__main__":
    main()
