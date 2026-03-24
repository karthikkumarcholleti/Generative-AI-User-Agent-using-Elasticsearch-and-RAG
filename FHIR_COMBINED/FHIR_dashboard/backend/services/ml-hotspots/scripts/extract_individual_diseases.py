"""
Individual Disease Hotspot Extraction Script
Extracts data for specific communicable diseases for individual hotspot detection
Focuses on actual diseases present in the database
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

def get_top_communicable_diseases(conn, limit=15):
    """Get the most common communicable diseases in the database"""
    print(f"\n🔍 Finding top {limit} communicable diseases...")
    
    query = """
    SELECT 
        SUBSTRING_INDEX(code, '^', 1) as clean_code,
        SUBSTRING_INDEX(display, '^', 1) as clean_display,
        COUNT(*) as case_count
    FROM conditions 
    WHERE code REGEXP '^[JAB][0-9]'
    GROUP BY clean_code, clean_display
    ORDER BY case_count DESC
    LIMIT %s
    """
    
    cursor = conn.cursor()
    cursor.execute(query, (limit,))
    diseases = cursor.fetchall()
    
    print(f"✅ Found {len(diseases)} diseases:")
    for i, (code, display, count) in enumerate(diseases, 1):
        print(f"   {i:2d}. {code}: {display} ({count} cases)")
    
    return diseases

def extract_individual_disease_data(conn, diseases):
    """
    Extract data for individual diseases
    Each disease gets its own analysis
    """
    print(f"\n" + "="*70)
    print(f"📥 EXTRACTING INDIVIDUAL DISEASE DATA")
    print(f"="*70)
    
    all_disease_data = {}
    
    for i, (code, display, expected_count) in enumerate(diseases, 1):
        print(f"\n🔬 Processing Disease {i}/{len(diseases)}: {code} - {display}")
        
        # SQL query for specific disease
        query = f"""
        SELECT 
            -- Condition information
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
            e.admission_reason
            
        FROM conditions c
        
        INNER JOIN patients p ON c.patient_id = p.patient_id
        LEFT JOIN hospital_locations h ON p.location_id = h.id
        LEFT JOIN encounters e ON c.patient_id = e.patient_id
        
        WHERE 
            c.code LIKE %s
            AND h.latitude IS NOT NULL
            AND h.longitude IS NOT NULL
            AND c.filename IS NOT NULL
        
        ORDER BY c.filename DESC, h.hospital_name
        """
        
        try:
            df = pd.read_sql(query, conn, params=[f'{code}%'])
            
            if len(df) > 0:
                # Enrich the dataset
                df = enrich_disease_dataset(df, code, display)
                all_disease_data[code] = df
                print(f"   ✅ Extracted {len(df)} records for {code}")
            else:
                print(f"   ⚠️  No records found for {code}")
                
        except Exception as e:
            print(f"   ❌ Error extracting {code}: {e}")
    
    return all_disease_data

def enrich_disease_dataset(df, disease_code, disease_name):
    """Enrich dataset with disease-specific fields"""
    
    # Calculate age
    df['birth_date'] = pd.to_datetime(df['birth_date'], errors='coerce')
    current_date = pd.Timestamp.now()
    df['age'] = ((current_date - df['birth_date']).dt.days / 365.25).round(1)
    
    # Extract date from filename
    df['event_date'] = df['filename'].apply(extract_date_from_filename)
    
    # Add disease information
    df['disease_code'] = disease_code
    df['disease_name'] = disease_name
    
    # Clean hospital names
    df['hospital_name'] = df['hospital_name'].str.strip()
    
    return df

def extract_date_from_filename(filename):
    """Extract date from filename"""
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

def create_individual_hotspot_datasets(all_disease_data):
    """Create individual hotspot datasets for each disease"""
    print(f"\n🏥 Creating individual hotspot datasets...")
    
    individual_datasets = {}
    
    for disease_code, df in all_disease_data.items():
        if len(df) == 0:
            continue
            
        print(f"\n📊 Processing {disease_code} ({df.iloc[0]['disease_name']})...")
        
        # Aggregate by hospital for this specific disease
        hospital_aggregation = df.groupby([
            'hospital_name', 'hospital_id', 'hospital_city', 'hospital_state',
            'latitude', 'longitude', 'disease_code', 'disease_name'
        ]).agg({
            'patient_id': 'count',  # Total cases
            'age': ['mean', 'median', 'std', 'min', 'max'],
            'gender': lambda x: (x == 'male').sum(),
            'event_date': 'count'  # Total encounters
        }).reset_index()
        
        # Flatten column names
        hospital_aggregation.columns = [
            'hospital_name', 'hospital_id', 'hospital_city', 'hospital_state',
            'latitude', 'longitude', 'disease_code', 'disease_name',
            'total_cases', 'mean_age', 'median_age', 'std_age', 'min_age', 'max_age',
            'male_count', 'total_encounters'
        ]
        
        # Add additional features
        hospital_aggregation['male_percentage'] = (hospital_aggregation['male_count'] / hospital_aggregation['total_cases'] * 100).round(1)
        hospital_aggregation['age_range'] = hospital_aggregation['max_age'] - hospital_aggregation['min_age']
        hospital_aggregation['cases_per_encounter'] = (hospital_aggregation['total_cases'] / hospital_aggregation['total_encounters']).round(2)
        
        # Calculate distance from geographic center
        center_lat = hospital_aggregation['latitude'].mean()
        center_lon = hospital_aggregation['longitude'].mean()
        hospital_aggregation['distance_from_center_km'] = np.sqrt(
            (hospital_aggregation['latitude'] - center_lat)**2 + 
            (hospital_aggregation['longitude'] - center_lon)**2
        ) * 111
        
        individual_datasets[disease_code] = hospital_aggregation
        print(f"   ✅ Created dataset: {len(hospital_aggregation)} hospitals")
        
        # Show top hospitals for this disease
        top_hospitals = hospital_aggregation.nlargest(3, 'total_cases')
        print(f"   🏆 Top hospitals:")
        for _, row in top_hospitals.iterrows():
            print(f"      - {row['hospital_name']}: {row['total_cases']} cases")
    
    return individual_datasets

def save_individual_datasets(individual_datasets):
    """Save individual disease datasets"""
    print(f"\n💾 Saving individual disease datasets...")
    
    saved_files = []
    
    for disease_code, df in individual_datasets.items():
        if len(df) == 0:
            continue
            
        filename = f'hotspot_{disease_code.replace(".", "_")}_data.csv'
        df.to_csv(filename, index=False)
        saved_files.append(filename)
        
        print(f"   ✅ Saved {filename}: {len(df)} hospitals, {df['total_cases'].sum()} total cases")
    
    # Create a combined summary
    summary_data = []
    for disease_code, df in individual_datasets.items():
        if len(df) > 0:
            summary_data.append({
                'disease_code': disease_code,
                'disease_name': df.iloc[0]['disease_name'],
                'hospitals_affected': len(df),
                'total_cases': df['total_cases'].sum(),
                'avg_cases_per_hospital': df['total_cases'].mean(),
                'max_cases_single_hospital': df['total_cases'].max()
            })
    
    summary_df = pd.DataFrame(summary_data)
    summary_df.to_csv('individual_diseases_summary.csv', index=False)
    print(f"   ✅ Saved summary: individual_diseases_summary.csv")
    
    return saved_files

def main():
    """Main execution function"""
    print("🚀 Starting Individual Disease Hotspot Extraction")
    print("="*60)
    
    # Connect to database
    conn = connect_db()
    if not conn:
        return
    
    try:
        # Get top communicable diseases
        diseases = get_top_communicable_diseases(conn, limit=10)
        
        # Extract data for each disease
        all_disease_data = extract_individual_disease_data(conn, diseases)
        
        # Create individual hotspot datasets
        individual_datasets = create_individual_hotspot_datasets(all_disease_data)
        
        # Save datasets
        saved_files = save_individual_datasets(individual_datasets)
        
        print(f"\n🎯 INDIVIDUAL DISEASE EXTRACTION COMPLETE!")
        print(f"✅ Created {len(saved_files)} individual disease datasets")
        print(f"✅ Each disease can now have its own hotspot analysis")
        print(f"✅ Ready for individual disease clustering")
        
        # Show summary
        print(f"\n📊 Summary of Diseases:")
        for disease_code, df in individual_datasets.items():
            if len(df) > 0:
                print(f"   {disease_code}: {len(df)} hospitals, {df['total_cases'].sum()} cases")
        
    except Exception as e:
        print(f"❌ Error in main execution: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        conn.close()
        print(f"\n🔌 Database connection closed")

if __name__ == "__main__":
    import numpy as np
    main()
