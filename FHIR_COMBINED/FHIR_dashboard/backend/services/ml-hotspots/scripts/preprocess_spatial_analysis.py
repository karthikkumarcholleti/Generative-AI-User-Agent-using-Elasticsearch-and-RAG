"""
Spatial Analysis Preprocessing Script
Processes comprehensive data for spatial hotspot detection
Focuses on geographic clustering without temporal aggregation
"""

import pandas as pd
import numpy as np
import os
from datetime import datetime

def load_data(filename='comprehensive_disease_data.csv'):
    """Load comprehensive dataset"""
    print(f"📂 Loading data from {filename}...")
    
    if not os.path.exists(filename):
        print(f"❌ File not found: {filename}")
        return None
    
    df = pd.read_csv(filename)
    print(f"✅ Loaded {len(df):,} records with {len(df.columns)} columns")
    return df

def clean_spatial_data(df):
    """Clean data for spatial analysis"""
    print(f"\n🧹 Cleaning data for spatial analysis...")
    
    # Remove records without coordinates
    before = len(df)
    df = df.dropna(subset=['latitude', 'longitude'])
    after = len(df)
    print(f"   Removed {before - after} records without coordinates")
    
    # Remove records without hospital names
    before = len(df)
    df = df.dropna(subset=['hospital_name'])
    after = len(df)
    print(f"   Removed {before - after} records without hospital names")
    
    # Clean hospital names
    df['hospital_name'] = df['hospital_name'].str.strip()
    
    # Clean disease codes
    df['condition_code_clean'] = df['condition_code_clean'].fillna('Unknown')
    df['disease_category'] = df['disease_category'].fillna('Unknown')
    
    print(f"✅ Data cleaning complete: {len(df):,} records remaining")
    return df

def aggregate_by_hospital_disease(df):
    """Aggregate data by hospital and disease category"""
    print(f"\n📊 Aggregating data by hospital and disease category...")
    
    # Group by hospital and disease category
    aggregation = df.groupby(['hospital_name', 'hospital_id', 'hospital_city', 'hospital_state', 
                             'latitude', 'longitude', 'disease_category']).agg({
        'patient_id': 'count',  # Total cases
        'age': ['mean', 'median', 'std', 'min', 'max'],  # Age statistics
        'gender': lambda x: (x == 'male').sum(),  # Male count
        'condition_code_clean': 'nunique',  # Unique diseases
        'observation_date': lambda x: x.notna().sum()  # Observations with dates
    }).reset_index()
    
    # Flatten column names
    aggregation.columns = [
        'hospital_name', 'hospital_id', 'hospital_city', 'hospital_state',
        'latitude', 'longitude', 'disease_category',
        'total_cases', 'mean_age', 'median_age', 'std_age', 'min_age', 'max_age',
        'male_count', 'unique_diseases', 'observations_with_dates'
    ]
    
    # Calculate additional metrics
    aggregation['male_percentage'] = (aggregation['male_count'] / aggregation['total_cases'] * 100).round(1)
    aggregation['age_range'] = aggregation['max_age'] - aggregation['min_age']
    aggregation['cases_per_disease'] = (aggregation['total_cases'] / aggregation['unique_diseases']).round(1)
    
    print(f"✅ Aggregation complete: {len(aggregation):,} hospital-disease combinations")
    return aggregation

def add_hospital_features(df):
    """Add hospital-level features"""
    print(f"\n🏥 Adding hospital-level features...")
    
    # Calculate hospital totals
    hospital_totals = df.groupby('hospital_name').agg({
        'total_cases': 'sum',
        'unique_diseases': 'sum',
        'observations_with_dates': 'sum'
    }).reset_index()
    hospital_totals.columns = ['hospital_name', 'hospital_grand_total', 'hospital_total_unique_diseases', 'hospital_total_observations']
    
    # Merge hospital totals
    df = df.merge(hospital_totals, on='hospital_name', how='left')
    
    # Calculate percentages
    df['category_percentage'] = (df['total_cases'] / df['hospital_grand_total'] * 100).round(1)
    
    # Calculate distance from geographic center
    center_lat = df['latitude'].mean()
    center_lon = df['longitude'].mean()
    
    # Simple distance calculation (approximate)
    df['distance_from_center_km'] = np.sqrt(
        (df['latitude'] - center_lat)**2 + (df['longitude'] - center_lon)**2
    ) * 111  # Rough conversion to km
    
    print(f"✅ Hospital features added")
    print(f"   Geographic center: ({center_lat:.4f}, {center_lon:.4f})")
    return df

def create_disease_category_features(df):
    """Create one-hot encoded disease category features"""
    print(f"\n🏷️ Creating disease category features...")
    
    # Create one-hot encoding for disease categories
    disease_categories = ['Respiratory', 'Infectious', 'Parasitic', 'Other']
    
    for category in disease_categories:
        df[f'category_{category}'] = (df['disease_category'] == category).astype(int)
    
    print(f"✅ Disease category features created: {disease_categories}")
    return df

def save_spatial_dataset(df, filename='ready_for_spatial_analysis.csv'):
    """Save processed dataset for spatial analysis"""
    print(f"\n💾 Saving spatial analysis dataset...")
    
    # Select relevant columns for spatial analysis
    spatial_columns = [
        'hospital_name', 'hospital_id', 'hospital_city', 'hospital_state',
        'latitude', 'longitude', 'distance_from_center_km',
        'disease_category', 'unique_diseases', 'total_cases',
        'mean_age', 'median_age', 'std_age', 'min_age', 'max_age',
        'male_count', 'male_percentage', 'age_range',
        'hospital_grand_total', 'category_percentage',
        'hospital_total_unique_diseases', 'cases_per_disease',
        'observations_with_dates'
    ] + [col for col in df.columns if col.startswith('category_')]
    
    spatial_df = df[spatial_columns].copy()
    
    # Save dataset
    spatial_df.to_csv(filename, index=False)
    
    print(f"✅ Spatial dataset saved: {filename}")
    print(f"   Records: {len(spatial_df):,}")
    print(f"   Columns: {len(spatial_df.columns)}")
    print(f"   File size: {os.path.getsize(filename) / 1024:.1f} KB")
    
    # Print summary
    print(f"\n📊 Spatial Dataset Summary:")
    print(f"   Unique hospitals: {spatial_df['hospital_name'].nunique()}")
    print(f"   Total cases: {spatial_df['total_cases'].sum()}")
    print(f"   Disease categories: {spatial_df['disease_category'].value_counts().to_dict()}")
    
    return spatial_df

def main():
    """Main preprocessing function"""
    print("🚀 Starting Spatial Analysis Preprocessing")
    print("="*50)
    
    # Load comprehensive data
    df = load_data()
    if df is None:
        return
    
    try:
        # Clean data
        df = clean_spatial_data(df)
        
        # Aggregate by hospital and disease
        df = aggregate_by_hospital_disease(df)
        
        # Add hospital features
        df = add_hospital_features(df)
        
        # Create disease category features
        df = create_disease_category_features(df)
        
        # Save spatial dataset
        spatial_df = save_spatial_dataset(df)
        
        print(f"\n🎯 PREPROCESSING COMPLETE!")
        print(f"✅ Ready for spatial analysis (DBSCAN, K-Means)")
        print(f"✅ Dataset optimized for geographic clustering")
        print(f"✅ All hospital and disease features included")
        
        # Show top hospitals by case count
        print(f"\n🏆 Top 5 Hospitals by Total Cases:")
        top_hospitals = spatial_df.groupby('hospital_name')['total_cases'].sum().nlargest(5)
        for i, (hospital, cases) in enumerate(top_hospitals.items(), 1):
            print(f"   {i}. {hospital}: {cases} cases")
        
    except Exception as e:
        print(f"❌ Error in preprocessing: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
