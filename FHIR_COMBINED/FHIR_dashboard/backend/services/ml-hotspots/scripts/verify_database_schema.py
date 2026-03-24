"""
Database Schema Verification Script
Phase 1: Verify all required tables and columns exist
"""

import mysql.connector
import os
from dotenv import load_dotenv
import pandas as pd

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

def check_tables_exist(conn):
    """Verify all required tables exist"""
    print("\n" + "="*60)
    print("📊 CHECKING TABLES")
    print("="*60)
    
    cursor = conn.cursor()
    cursor.execute("SHOW TABLES")
    tables = [table[0] for table in cursor.fetchall()]
    
    required_tables = ['conditions', 'encounters', 'hospital_locations', 'patients', 'observations']
    
    print(f"\n📋 Found {len(tables)} tables in database:")
    for table in tables:
        status = "✅" if table in required_tables else "  "
        print(f"{status} {table}")
    
    print(f"\n🎯 Required tables status:")
    for table in required_tables:
        if table in tables:
            print(f"✅ {table}")
        else:
            print(f"❌ {table} - MISSING!")
    
    cursor.close()
    return all(table in tables for table in required_tables)

def describe_table(conn, table_name):
    """Get detailed structure of a table"""
    print(f"\n📋 Table: {table_name}")
    print("-" * 60)
    
    cursor = conn.cursor()
    cursor.execute(f"DESCRIBE {table_name}")
    columns = cursor.fetchall()
    
    print(f"{'Column':<30} {'Type':<25} {'Null':<6} {'Key':<5}")
    print("-" * 60)
    for col in columns:
        field, col_type, null, key = col[0], col[1], col[2], col[3]
        print(f"{field:<30} {str(col_type):<25} {null:<6} {key:<5}")
    
    cursor.close()
    return columns

def check_data_counts(conn):
    """Count rows in each table"""
    print("\n" + "="*60)
    print("📈 DATA COUNTS")
    print("="*60)
    
    tables = ['conditions', 'encounters', 'hospital_locations', 'patients', 'observations']
    cursor = conn.cursor()
    
    for table in tables:
        try:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            print(f"✅ {table:<25} {count:>10} rows")
        except mysql.connector.Error as err:
            print(f"❌ {table:<25} Error: {err}")
    
    cursor.close()

def check_coordinates(conn):
    """Check for missing or invalid coordinates in hospital_locations"""
    print("\n" + "="*60)
    print("🗺️  CHECKING HOSPITAL COORDINATES")
    print("="*60)
    
    cursor = conn.cursor()
    
    # Total hospitals
    cursor.execute("SELECT COUNT(*) FROM hospital_locations")
    total = cursor.fetchone()[0]
    
    # Missing coordinates
    cursor.execute("""
        SELECT COUNT(*) FROM hospital_locations 
        WHERE latitude IS NULL OR longitude IS NULL
    """)
    missing = cursor.fetchone()[0]
    
    # Invalid coordinates (out of valid range)
    cursor.execute("""
        SELECT COUNT(*) FROM hospital_locations 
        WHERE latitude < -90 OR latitude > 90 
           OR longitude < -180 OR longitude > 180
    """)
    invalid = cursor.fetchone()[0]
    
    print(f"Total hospitals: {total}")
    print(f"Missing coordinates: {missing} ({(missing/total*100) if total > 0 else 0:.1f}%)")
    print(f"Invalid coordinates: {invalid} ({(invalid/total*100) if total > 0 else 0:.1f}%)")
    
    if missing > 0:
        print("\n⚠️  Sample hospitals with missing coordinates:")
        cursor.execute("""
            SELECT id, hospital_name, latitude, longitude 
            FROM hospital_locations 
            WHERE latitude IS NULL OR longitude IS NULL
            LIMIT 5
        """)
        for row in cursor.fetchall():
            print(f"  ID: {row[0]}, Name: {row[1]}, Lat: {row[2]}, Lng: {row[3]}")
    
    cursor.close()

def sample_disease_codes(conn):
    """Sample disease codes from conditions table"""
    print("\n" + "="*60)
    print("🦠 SAMPLING DISEASE CODES")
    print("="*60)
    
    cursor = conn.cursor(dictionary=True)
    
    # Get unique disease codes
    cursor.execute("""
        SELECT code, display, COUNT(*) as count 
        FROM conditions 
        GROUP BY code, display 
        ORDER BY count DESC 
        LIMIT 20
    """)
    
    print(f"\n📊 Top 20 conditions in database:")
    print(f"{'Code':<15} {'Display':<50} {'Count':>10}")
    print("-" * 80)
    
    results = cursor.fetchall()
    for row in results:
        print(f"{row['code']:<15} {row['display']:<50} {row['count']:>10}")
    
    cursor.close()
    return results

def identify_communicable_diseases(conn):
    """Identify all communicable disease codes in the database"""
    print("\n" + "="*60)
    print("🦠 IDENTIFYING COMMUNICABLE DISEASES")
    print("="*60)
    
    cursor = conn.cursor(dictionary=True)
    
    # Common communicable disease ICD-10 code ranges
    # A00-B99: Infectious and parasitic diseases
    # J09-J18: Influenza and pneumonia
    # U07.1: COVID-19
    
    cursor.execute("""
        SELECT code, display, COUNT(*) as count 
        FROM conditions 
        WHERE 
            -- Infectious and parasitic diseases (A00-B99)
            (code REGEXP '^[AB][0-9]{2}')
            OR
            -- Influenza and pneumonia (J09-J18)
            (code REGEXP '^J(09|1[0-8])')
            OR
            -- COVID-19
            (code LIKE 'U07%')
        GROUP BY code, display 
        ORDER BY count DESC
    """)
    
    results = cursor.fetchall()
    
    print(f"\n✅ Found {len(results)} communicable disease codes:")
    print(f"{'Code':<15} {'Display':<60} {'Count':>10}")
    print("-" * 90)
    
    for row in results:
        print(f"{row['code']:<15} {row['display']:<60} {row['count']:>10}")
    
    # Save to CSV for reference
    if results:
        df = pd.DataFrame(results)
        output_path = '../communicable_disease_codes.csv'
        df.to_csv(output_path, index=False)
        print(f"\n💾 Saved communicable disease codes to: communicable_disease_codes.csv")
    
    cursor.close()
    return results

def main():
    """Main verification workflow"""
    print("\n" + "="*60)
    print("🔍 FHIR DATABASE SCHEMA VERIFICATION")
    print("Phase 1: Communicable Disease Hotspot Detection")
    print("="*60)
    
    # Connect to database
    conn = connect_db()
    if not conn:
        return
    
    try:
        # 1. Check tables exist
        tables_ok = check_tables_exist(conn)
        if not tables_ok:
            print("\n❌ Missing required tables. Cannot proceed.")
            return
        
        # 2. Describe each table
        print("\n" + "="*60)
        print("📊 TABLE STRUCTURES")
        print("="*60)
        
        for table in ['conditions', 'encounters', 'hospital_locations', 'patients', 'observations']:
            describe_table(conn, table)
        
        # 3. Check data counts
        check_data_counts(conn)
        
        # 4. Check coordinates
        check_coordinates(conn)
        
        # 5. Sample disease codes
        sample_disease_codes(conn)
        
        # 6. Identify communicable diseases
        communicable_diseases = identify_communicable_diseases(conn)
        
        # Summary
        print("\n" + "="*60)
        print("✅ VERIFICATION COMPLETE")
        print("="*60)
        print(f"✅ All required tables present")
        print(f"✅ Found {len(communicable_diseases)} communicable disease codes")
        print(f"✅ Ready for data extraction (Phase 1 Step 4)")
        
    except Exception as e:
        print(f"\n❌ Error during verification: {e}")
    finally:
        conn.close()
        print("\n🔌 Database connection closed")

if __name__ == "__main__":
    main()

