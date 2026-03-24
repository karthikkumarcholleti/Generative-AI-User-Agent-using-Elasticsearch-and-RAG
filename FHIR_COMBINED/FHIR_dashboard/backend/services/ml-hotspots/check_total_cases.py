import pandas as pd

# Load the spatial analysis dataset
df = pd.read_csv('ready_for_spatial_analysis.csv')

print('📊 SPATIAL HOTSPOT DATA - TOTAL CASES EXPLANATION')
print('='*70)

print(f'\n1. DATASET SIZE:')
print(f'   Total Records (rows): {len(df)}')
print(f'   Each row = One hospital with one disease category')

print(f'\n2. TOTAL CASES:')
print(f'   Sum of all cases: {df["total_cases"].sum()}')

print(f'\n3. DISEASE CATEGORY BREAKDOWN:')
print(f'   Respiratory cases: {df["category_Respiratory"].sum()}')
print(f'   Infectious cases: {df["category_Infectious"].sum()}')
print(f'   Parasitic cases: {df["category_Parasitic"].sum()}')
print(f'   Other cases: {df["category_Other"].sum()}')
print(f'   ---')
print(f'   Total (should match): {df["category_Respiratory"].sum() + df["category_Infectious"].sum() + df["category_Parasitic"].sum() + df["category_Other"].sum()}')

print(f'\n4. UNIQUE HOSPITALS:')
print(f'   Number of unique hospitals: {df["hospital_name"].nunique()}')

print(f'\n5. HOW THE DATA IS STRUCTURED:')
print(f'   Each hospital can appear multiple times (once per disease category)')
print(f'   Example: OSF St. Francis Hospital appears in multiple rows:')
osf_data = df[df['hospital_name'] == 'OSF St. Francis Hospital']
if len(osf_data) > 0:
    print(f'   - OSF St. Francis appears {len(osf_data)} times')
    for idx, row in osf_data.iterrows():
        print(f'     • Category: {row["disease_category"]}, Cases: {row["total_cases"]}')

print(f'\n6. TOP 5 HOSPITAL-CATEGORY COMBINATIONS:')
top5 = df.nlargest(5, 'total_cases')[['hospital_name', 'disease_category', 'total_cases']]
for idx, row in top5.iterrows():
    print(f'   {row["hospital_name"]} ({row["disease_category"]}): {row["total_cases"]} cases')

print(f'\n7. WHAT "TOTAL CASES" MEANS:')
print(f'   - {df["total_cases"].sum()} = Sum of ALL disease cases in the dataset')
print(f'   - This is the total number of communicable disease cases we are analyzing')
print(f'   - Each case represents one patient with one disease diagnosis')

print(f'\n8. INDIVIDUAL DISEASE BREAKDOWN (from separate files):')
import glob
disease_files = glob.glob('hotspot_*_data.csv')
disease_totals = []
for file in disease_files:
    disease_code = file.replace('hotspot_', '').replace('_data.csv', '')
    disease_df = pd.read_csv(file)
    total = disease_df['total_cases'].sum()
    disease_totals.append((disease_code, total))

disease_totals.sort(key=lambda x: x[1], reverse=True)
print(f'   Found {len(disease_totals)} specific diseases:')
for code, total in disease_totals:
    print(f'   - {code}: {total} cases')

print(f'   ---')
print(f'   Sum of individual diseases: {sum([t[1] for t in disease_totals])}')

print(f'\n🎯 SUMMARY:')
print(f'   We are analyzing {df["total_cases"].sum()} total communicable disease cases')
print(f'   across {df["hospital_name"].nunique()} hospitals')
print(f'   covering {len(disease_totals)} specific diseases')

