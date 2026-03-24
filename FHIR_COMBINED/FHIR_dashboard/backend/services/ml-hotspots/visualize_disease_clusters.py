"""
Visualize Disease Clusters with Specific Disease Names
Creates comprehensive visualizations showing clusters with actual disease names
"""

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from sklearn.cluster import DBSCAN, KMeans
from sklearn.preprocessing import StandardScaler
import glob

def load_disease_data():
    """Load all individual disease datasets with names"""
    disease_files = glob.glob('hotspot_*_data.csv')
    
    disease_data = {}
    disease_names = {}
    
    # Create better disease name mappings
    disease_name_mapping = {
        'J18_9': 'Pneumonia, unspecified',
        'J44_9': 'COPD, unspecified', 
        'J44_1': 'COPD with exacerbation',
        'A41_9': 'Sepsis, unspecified organism',
        'J96_01': 'Acute respiratory failure with hypoxia',
        'J02_9': 'Acute pharyngitis, unspecified',
        'J69_0': 'Pneumonitis due to inhalation',
        'B95_2': 'Enterococcus as cause of diseases',
        'J01_00': 'Acute maxillary sinusitis',
        'J45_909': 'Asthma, unspecified'
    }
    
    for file in disease_files:
        disease_code = file.replace('hotspot_', '').replace('_data.csv', '')
        df = pd.read_csv(file)
        if len(df) > 0:
            disease_data[disease_code] = df
            disease_names[disease_code] = disease_name_mapping.get(disease_code, df.iloc[0]['disease_name'])
    
    return disease_data, disease_names

def create_disease_cluster_map(disease_data, disease_names):
    """Create a comprehensive map showing all diseases with clusters"""
    
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    fig.suptitle('Communicable Disease Hotspots - Specific Disease Analysis', 
                 fontsize=16, fontweight='bold')
    
    # 1. All diseases on one map with different colors
    ax1 = axes[0, 0]
    colors = plt.cm.Set3(np.linspace(0, 1, len(disease_data)))
    
    for i, (disease_code, df) in enumerate(disease_data.items()):
        if len(df) > 0:
            disease_name = disease_names[disease_code]
            # Size based on total cases
            sizes = df['total_cases'] * 20
            ax1.scatter(df['longitude'], df['latitude'], 
                       c=[colors[i]], s=sizes, alpha=0.7, 
                       label=f'{disease_code}: {disease_name[:30]}...',
                       edgecolors='black', linewidths=1)
    
    ax1.set_title('All Disease Hotspots\n(Size = Case Count)', fontweight='bold')
    ax1.set_xlabel('Longitude')
    ax1.set_ylabel('Latitude')
    ax1.legend(bbox_to_anchor=(1.05, 1), loc='upper left', fontsize=8)
    ax1.grid(True, alpha=0.3)
    
    # 2. Top 5 diseases by total cases
    ax2 = axes[0, 1]
    disease_totals = [(code, df['total_cases'].sum(), disease_names[code]) 
                      for code, df in disease_data.items() if len(df) > 0]
    disease_totals.sort(key=lambda x: x[1], reverse=True)
    top_5 = disease_totals[:5]
    
    codes, totals, names = zip(*top_5)
    bars = ax2.bar(range(len(codes)), totals, color='skyblue', alpha=0.7, edgecolor='navy')
    ax2.set_title('Top 5 Diseases by Total Cases', fontweight='bold')
    ax2.set_xlabel('Disease Code')
    ax2.set_ylabel('Total Cases')
    ax2.set_xticks(range(len(codes)))
    ax2.set_xticklabels(codes, rotation=45)
    
    # Add value labels and disease names
    for i, (bar, total, name) in enumerate(zip(bars, totals, names)):
        height = bar.get_height()
        ax2.text(bar.get_x() + bar.get_width()/2., height + 1,
                f'{int(total)}', ha='center', va='bottom', fontweight='bold')
        # Add disease name below
        ax2.text(bar.get_x() + bar.get_width()/2., -5,
                f'{name[:15]}...', ha='center', va='top', fontsize=8, rotation=45)
    
    # 3. Hospital analysis - which hospitals have multiple diseases
    ax3 = axes[1, 0]
    
    # Count diseases per hospital
    all_hospitals = {}
    for disease_code, df in disease_data.items():
        for _, row in df.iterrows():
            hospital = row['hospital_name']
            if hospital not in all_hospitals:
                all_hospitals[hospital] = {'diseases': [], 'total_cases': 0, 'latitude': row['latitude'], 'longitude': row['longitude']}
            all_hospitals[hospital]['diseases'].append(disease_code)
            all_hospitals[hospital]['total_cases'] += row['total_cases']
    
    # Create hospital disease count data
    hospital_data = []
    for hospital, info in all_hospitals.items():
        hospital_data.append({
            'hospital': hospital,
            'disease_count': len(info['diseases']),
            'total_cases': info['total_cases'],
            'latitude': info['latitude'],
            'longitude': info['longitude']
        })
    
    hospital_df = pd.DataFrame(hospital_data)
    
    # Color hospitals by number of diseases
    scatter = ax3.scatter(hospital_df['longitude'], hospital_df['latitude'], 
                         c=hospital_df['disease_count'], s=hospital_df['total_cases']*5,
                         cmap='RdYlBu_r', alpha=0.7, edgecolors='black')
    
    ax3.set_title('Hospital Disease Burden\n(Color = # Diseases, Size = Total Cases)', fontweight='bold')
    ax3.set_xlabel('Longitude')
    ax3.set_ylabel('Latitude')
    
    # Add colorbar
    cbar = plt.colorbar(scatter, ax=ax3)
    cbar.set_label('Number of Different Diseases')
    
    ax3.grid(True, alpha=0.3)
    
    # 4. Disease severity analysis
    ax4 = axes[1, 1]
    
    # Calculate average cases per hospital for each disease
    disease_metrics = []
    for disease_code, df in disease_data.items():
        if len(df) > 0:
            avg_cases = df['total_cases'].mean()
            max_cases = df['total_cases'].max()
            hospitals = len(df)
            disease_metrics.append({
                'code': disease_code,
                'name': disease_names[disease_code],
                'avg_cases': avg_cases,
                'max_cases': max_cases,
                'hospitals': hospitals
            })
    
    disease_metrics.sort(key=lambda x: x['avg_cases'], reverse=True)
    
    codes = [d['code'] for d in disease_metrics]
    avg_cases = [d['avg_cases'] for d in disease_metrics]
    max_cases = [d['max_cases'] for d in disease_metrics]
    
    x = np.arange(len(codes))
    width = 0.35
    
    bars1 = ax4.bar(x - width/2, avg_cases, width, label='Average Cases', color='lightblue', alpha=0.7)
    bars2 = ax4.bar(x + width/2, max_cases, width, label='Max Cases', color='lightcoral', alpha=0.7)
    
    ax4.set_title('Disease Severity Analysis', fontweight='bold')
    ax4.set_xlabel('Disease Code')
    ax4.set_ylabel('Number of Cases')
    ax4.set_xticks(x)
    ax4.set_xticklabels(codes, rotation=45)
    ax4.legend()
    
    # Add value labels
    for bars in [bars1, bars2]:
        for bar in bars:
            height = bar.get_height()
            ax4.text(bar.get_x() + bar.get_width()/2., height + 0.1,
                    f'{height:.1f}', ha='center', va='bottom', fontsize=8)
    
    plt.tight_layout()
    plt.show()
    
    return all_hospitals

def create_individual_disease_analysis(disease_data, disease_names):
    """Create detailed analysis for top diseases"""
    
    # Get top 3 diseases by total cases
    disease_totals = [(code, df['total_cases'].sum()) for code, df in disease_data.items() if len(df) > 0]
    disease_totals.sort(key=lambda x: x[1], reverse=True)
    top_3 = disease_totals[:3]
    
    fig, axes = plt.subplots(1, 3, figsize=(18, 6))
    fig.suptitle('Individual Disease Hotspot Analysis - Top 3 Diseases', 
                 fontsize=16, fontweight='bold')
    
    for i, (disease_code, total_cases) in enumerate(top_3):
        df = disease_data[disease_code]
        disease_name = disease_names[disease_code]
        
        ax = axes[i]
        
        # Run clustering for this disease
        if len(df) >= 3:
            features = ['latitude', 'longitude', 'total_cases', 'mean_age']
            X = df[features].copy()
            # Handle missing values
            X = X.fillna(X.mean())
            scaler = StandardScaler()
            X_scaled = scaler.fit_transform(X)
            
            # DBSCAN clustering
            dbscan = DBSCAN(eps=0.8, min_samples=2)
            dbscan_labels = dbscan.fit_predict(X_scaled)
            
            # Plot clusters
            colors = ['red', 'blue', 'green', 'orange', 'purple']
            for cluster in set(dbscan_labels):
                if cluster == -1:  # Noise
                    cluster_data = df[dbscan_labels == cluster]
                    ax.scatter(cluster_data['longitude'], cluster_data['latitude'], 
                               c='black', marker='x', s=100, alpha=0.6, label='Isolated')
                else:
                    cluster_data = df[dbscan_labels == cluster]
                    sizes = cluster_data['total_cases'] * 30
                    ax.scatter(cluster_data['longitude'], cluster_data['latitude'], 
                               c=colors[cluster % len(colors)], s=sizes, alpha=0.7, 
                               label=f'Cluster {cluster}', edgecolors='black', linewidths=1)
        
        ax.set_title(f'{disease_code}\n{disease_name}\n({total_cases} total cases)', 
                    fontweight='bold', fontsize=12)
        ax.set_xlabel('Longitude')
        ax.set_ylabel('Latitude')
        ax.legend()
        ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.show()

def print_disease_summary(disease_data, disease_names, all_hospitals):
    """Print comprehensive disease summary"""
    
    print("\n" + "="*80)
    print("🏥 COMMUNICABLE DISEASE HOTSPOT SUMMARY - WITH DISEASE NAMES")
    print("="*80)
    
    print("\n📊 DISEASE BREAKDOWN:")
    disease_totals = [(code, df['total_cases'].sum(), len(df)) for code, df in disease_data.items() if len(df) > 0]
    disease_totals.sort(key=lambda x: x[1], reverse=True)
    
    for i, (code, total_cases, hospitals) in enumerate(disease_totals, 1):
        disease_name = disease_names[code]
        print(f"   {i:2d}. {code}: {disease_name}")
        print(f"       Total Cases: {total_cases}, Hospitals: {hospitals}")
    
    print(f"\n🏥 HOSPITAL DISEASE BURDEN:")
    hospital_data = []
    for hospital, info in all_hospitals.items():
        hospital_data.append({
            'hospital': hospital,
            'diseases': info['diseases'],
            'total_cases': info['total_cases']
        })
    
    hospital_data.sort(key=lambda x: x['total_cases'], reverse=True)
    
    for i, hospital_info in enumerate(hospital_data[:5], 1):
        hospital = hospital_info['hospital']
        diseases = hospital_info['diseases']
        total_cases = hospital_info['total_cases']
        
        disease_names_list = [disease_names.get(code, code) for code in diseases]
        print(f"   {i}. {hospital}: {total_cases} total cases")
        print(f"      Diseases: {', '.join(diseases)}")
        print(f"      Names: {', '.join([name[:20] + '...' if len(name) > 20 else name for name in disease_names_list])}")
    
    print(f"\n🎯 CLINICAL INSIGHTS:")
    print(f"   • Most widespread disease: {disease_names[disease_totals[0][0]]} ({disease_totals[0][1]} cases)")
    print(f"   • Most concentrated disease: {disease_names[min(disease_totals, key=lambda x: x[2])[0]]} (fewest hospitals)")
    print(f"   • Highest case volume hospital: {hospital_data[0]['hospital']} ({hospital_data[0]['total_cases']} cases)")

def main():
    """Main visualization function"""
    print("🎨 Creating Disease Cluster Visualizations with Specific Names...")
    
    # Load data
    disease_data, disease_names = load_disease_data()
    
    if not disease_data:
        print("❌ No disease data found!")
        return
    
    print(f"✅ Loaded {len(disease_data)} diseases with names")
    
    # Create visualizations
    all_hospitals = create_disease_cluster_map(disease_data, disease_names)
    create_individual_disease_analysis(disease_data, disease_names)
    
    # Print summary
    print_disease_summary(disease_data, disease_names, all_hospitals)
    
    print(f"\n🎯 Visualizations complete! Check the plots above for disease-specific clusters.")

if __name__ == "__main__":
    main()
