import pandas as pd
from sklearn.cluster import DBSCAN
from sklearn.preprocessing import StandardScaler

# Load data and run DBSCAN to get actual results
df = pd.read_csv('ready_for_spatial_analysis.csv')
features = ['latitude', 'longitude', 'total_cases', 'mean_age', 'distance_from_center_km', 'category_Respiratory', 'category_Infectious', 'category_Parasitic', 'category_Other']
X = df[features].copy()
X = X.fillna(X.mean())
scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)

dbscan = DBSCAN(eps=0.5, min_samples=3)
dbscan_labels = dbscan.fit_predict(X_scaled)
df['dbscan_cluster'] = dbscan_labels

print('🔍 VERIFYING DBSCAN CLUSTER ANALYSIS RESULTS:')
print('='*60)

# Check actual cluster statistics
cluster_stats = df.groupby('dbscan_cluster').agg({
    'total_cases': ['sum', 'count', 'mean']
}).round(1)

cluster_stats.columns = ['Total Cases', 'Hospital Count', 'Average Cases']
print('\nACTUAL CLUSTER STATISTICS:')
print(cluster_stats)

print('\nCLUSTER BREAKDOWN:')
for cluster in sorted(df['dbscan_cluster'].unique()):
    cluster_data = df[df['dbscan_cluster'] == cluster]
    if cluster == -1:
        print(f'  Noise (Isolated): {len(cluster_data)} hospitals, {cluster_data["total_cases"].sum()} total cases')
    else:
        print(f'  Cluster {cluster}: {len(cluster_data)} hospitals, {cluster_data["total_cases"].sum()} total cases, {cluster_data["total_cases"].mean():.1f} avg cases')

# Check clustered vs isolated
clustered_count = len(df[df['dbscan_cluster'] != -1])
noise_count = len(df[df['dbscan_cluster'] == -1])
total_count = len(df)

print(f'\nCLUSTERED vs ISOLATED:')
print(f'  Clustered hospitals: {clustered_count} ({clustered_count/total_count*100:.1f}%)')
print(f'  Isolated hospitals: {noise_count} ({noise_count/total_count*100:.1f}%)')

print('\n🎯 COMPARING WITH VISUALIZATION:')
print('Visualization shows:')
print('  Cluster 0: 976 cases, 6 hospitals, 162.7 avg')
print('  Cluster 1: 996 cases, 8 hospitals, 124.5 avg') 
print('  Cluster 2: 494 cases, 5 hospitals, 98.8 avg')
print('  Cluster 3: 536 cases, 3 hospitals, 178.7 avg')
print('  Cluster 4: 86 cases, 5 hospitals, 17.2 avg')
print('  68.2% isolated, 31.8% clustered')

print('\n✅ VERIFICATION: Does the visualization match our actual data?')
