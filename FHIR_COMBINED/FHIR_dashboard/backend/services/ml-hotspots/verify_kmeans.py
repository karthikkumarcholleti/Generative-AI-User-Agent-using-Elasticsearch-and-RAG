import pandas as pd
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

# Load data and run K-Means to verify results
df = pd.read_csv('ready_for_spatial_analysis.csv')
features = ['latitude', 'longitude', 'total_cases', 'mean_age', 'distance_from_center_km', 'category_Respiratory', 'category_Infectious', 'category_Parasitic', 'category_Other']
X = df[features].copy()
X = X.fillna(X.mean())
scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)

kmeans = KMeans(n_clusters=4, random_state=42, n_init=10)
kmeans_labels = kmeans.fit_predict(X_scaled)
df['kmeans_cluster'] = kmeans_labels

print('🔍 VERIFYING K-MEANS CLUSTER ANALYSIS RESULTS:')
print('='*60)

# Check actual K-Means cluster statistics
cluster_stats = df.groupby('kmeans_cluster').agg({
    'total_cases': ['sum', 'count', 'mean']
}).round(1)

cluster_stats.columns = ['Total Cases', 'Hospital Count', 'Average Cases']
print('\nACTUAL K-MEANS CLUSTER STATISTICS:')
print(cluster_stats)

print('\nK-MEANS GROUP BREAKDOWN:')
for cluster in sorted(df['kmeans_cluster'].unique()):
    cluster_data = df[df['kmeans_cluster'] == cluster]
    total_cases = cluster_data['total_cases'].sum()
    hospital_count = len(cluster_data)
    avg_cases = cluster_data['total_cases'].mean()
    print(f'  Group {cluster}: {hospital_count} hospitals, {total_cases} total cases, {avg_cases:.1f} avg cases')

print('\n🎯 COMPARING WITH VISUALIZATION:')
print('Visualization shows:')
print('  Group 0: 54 hospitals, 537.3 avg cases')
print('  Group 1: 9 hospitals, 646.9 avg cases') 
print('  Group 2: 16 hospitals, 637.0 avg cases')
print('  Group 3: 6 hospitals, 43.7 avg cases')

print('\n✅ VERIFICATION: Does the K-Means visualization match our actual data?')
