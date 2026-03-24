#!/usr/bin/env python3
"""
Database Source Verification Script
Verifies if LLM Backend and Full-Stack Dashboard are using the same database
"""

import os
import sys
from pathlib import Path

# Add paths for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "FHIR_LLM_UA" / "backend"))
sys.path.insert(0, str(Path(__file__).parent.parent / "FHIR_dashboard" / "backend"))

try:
    from sqlalchemy import create_engine, text
    from sqlalchemy.engine import URL
    import mysql.connector
    import mysql2
except ImportError:
    print("❌ Missing dependencies. Installing...")
    os.system("pip install sqlalchemy pymysql mysql-connector-python mysql2-python 2>/dev/null || pip install sqlalchemy pymysql mysql-connector-python")
    from sqlalchemy import create_engine, text
    from sqlalchemy.engine import URL
    import mysql.connector

def get_llm_db_config():
    """Get LLM Backend database configuration"""
    llm_env_path = Path(__file__).parent.parent / "FHIR_LLM_UA" / "backend" / ".env"
    
    config = {
        "host": "127.0.0.1",
        "port": 3306,
        "database": "llm_ua_clinical",
        "user": None,
        "password": None
    }
    
    if llm_env_path.exists():
        print(f"📄 Found LLM .env file: {llm_env_path}")
        with open(llm_env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    if '=' in line:
                        key, value = line.split('=', 1)
                        key = key.strip()
                        value = value.strip().strip('"').strip("'")
                        if key == "DB_HOST":
                            config["host"] = value
                        elif key == "DB_PORT":
                            config["port"] = int(value) if value.isdigit() else 3306
                        elif key == "DB_NAME":
                            config["database"] = value
                        elif key == "DB_USER":
                            config["user"] = value
                        elif key == "DB_PASSWORD":
                            config["password"] = value
    else:
        print(f"⚠️  LLM .env file not found: {llm_env_path}")
        print("   Using defaults from database.py")
    
    return config

def get_fullstack_db_config():
    """Get Full-Stack Dashboard database configuration"""
    fs_env_path = Path(__file__).parent.parent / "FHIR_dashboard" / "backend" / ".env"
    
    config = {
        "host": "localhost",
        "port": 3306,
        "database": "cocm_db",
        "user": "root",
        "password": ""
    }
    
    if fs_env_path.exists():
        print(f"📄 Found Full-Stack .env file: {fs_env_path}")
        with open(fs_env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    if '=' in line:
                        key, value = line.split('=', 1)
                        key = key.strip()
                        value = value.strip().strip('"').strip("'")
                        if key == "DB_HOST":
                            config["host"] = value
                        elif key == "DB_PORT":
                            config["port"] = int(value) if value.isdigit() else 3306
                        elif key == "DB_NAME":
                            config["database"] = value
                        elif key == "DB_USER":
                            config["user"] = value
                        elif key == "DB_PASSWORD":
                            config["password"] = value
    else:
        print(f"⚠️  Full-Stack .env file not found: {fs_env_path}")
        print("   Using defaults from db.js")
    
    return config

def test_connection(config, name):
    """Test database connection"""
    try:
        conn = mysql.connector.connect(
            host=config["host"],
            port=config["port"],
            user=config["user"] or "root",
            password=config["password"] or "",
            database=config["database"]
        )
        cursor = conn.cursor()
        cursor.execute("SELECT DATABASE()")
        db_name = cursor.fetchone()[0]
        cursor.close()
        conn.close()
        return True, db_name
    except Exception as e:
        return False, str(e)

def query_database(config, query, name):
    """Execute a query on the database"""
    try:
        conn = mysql.connector.connect(
            host=config["host"],
            port=config["port"],
            user=config["user"] or "root",
            password=config["password"] or "",
            database=config["database"]
        )
        cursor = conn.cursor(dictionary=True)
        cursor.execute(query)
        results = cursor.fetchall()
        cursor.close()
        conn.close()
        return True, results
    except Exception as e:
        return False, str(e)

def main():
    print("=" * 70)
    print("🔍 DATABASE SOURCE VERIFICATION")
    print("=" * 70)
    print()
    
    # Get configurations
    print("📋 Reading configurations...")
    llm_config = get_llm_db_config()
    fs_config = get_fullstack_db_config()
    print()
    
    # Display configurations
    print("🔧 LLM Backend Configuration:")
    print(f"   Host: {llm_config['host']}")
    print(f"   Port: {llm_config['port']}")
    print(f"   Database: {llm_config['database']}")
    print(f"   User: {llm_config['user'] or '(default: root)'}")
    print()
    
    print("🔧 Full-Stack Dashboard Configuration:")
    print(f"   Host: {fs_config['host']}")
    print(f"   Port: {fs_config['port']}")
    print(f"   Database: {fs_config['database']}")
    print(f"   User: {fs_config['user'] or '(default: root)'}")
    print()
    
    # Test connections
    print("🔌 Testing connections...")
    llm_ok, llm_result = test_connection(llm_config, "LLM")
    fs_ok, fs_result = test_connection(fs_config, "Full-Stack")
    
    if not llm_ok:
        print(f"❌ LLM Backend connection failed: {llm_result}")
        return
    else:
        print(f"✅ LLM Backend connected to: {llm_result}")
    
    if not fs_ok:
        print(f"❌ Full-Stack Dashboard connection failed: {fs_result}")
        return
    else:
        print(f"✅ Full-Stack Dashboard connected to: {fs_result}")
    
    print()
    
    # Compare database names
    if llm_config["database"] == fs_config["database"]:
        print("✅ Database names match!")
    else:
        print(f"⚠️  Database names differ:")
        print(f"   LLM: {llm_config['database']}")
        print(f"   Full-Stack: {fs_config['database']}")
        print()
        print("   However, they might still be the same database if:")
        print("   - Environment variables override the defaults")
        print("   - Both connect to the same host/port")
    
    print()
    
    # Query same data from both
    print("📊 Querying data for comparison...")
    
    # Test 1: Patient count
    print("\n1️⃣  Patient Count:")
    llm_ok, llm_patients = query_database(llm_config, "SELECT COUNT(*) as count FROM patients", "LLM")
    fs_ok, fs_patients = query_database(fs_config, "SELECT COUNT(*) as count FROM patients", "Full-Stack")
    
    if llm_ok and fs_ok:
        llm_count = llm_patients[0]["count"] if llm_patients else 0
        fs_count = fs_patients[0]["count"] if fs_patients else 0
        print(f"   LLM Backend: {llm_count} patients")
        print(f"   Full-Stack: {fs_count} patients")
        if llm_count == fs_count:
            print("   ✅ Counts match!")
        else:
            print("   ❌ Counts differ - Different databases!")
    
    # Test 2: Get a sample patient ID
    print("\n2️⃣  Sample Patient ID:")
    llm_ok, llm_sample = query_database(llm_config, "SELECT patient_id FROM patients LIMIT 1", "LLM")
    fs_ok, fs_sample = query_database(fs_config, "SELECT patient_id FROM patients LIMIT 1", "Full-Stack")
    
    if llm_ok and fs_ok and llm_sample and fs_sample:
        llm_pid = llm_sample[0]["patient_id"]
        fs_pid = fs_sample[0]["patient_id"]
        print(f"   LLM Backend sample: {llm_pid}")
        print(f"   Full-Stack sample: {fs_pid}")
    
    # Test 3: Query same patient from both
    if llm_ok and fs_ok and llm_sample:
        test_pid = llm_sample[0]["patient_id"]
        print(f"\n3️⃣  Querying Patient '{test_pid}' from both databases:")
        
        llm_ok, llm_patient = query_database(
            llm_config, 
            f"SELECT patient_id, CONCAT(given_name, ' ', family_name) as name FROM patients WHERE patient_id = '{test_pid}'",
            "LLM"
        )
        fs_ok, fs_patient = query_database(
            fs_config,
            f"SELECT patient_id, CONCAT(given_name, ' ', family_name) as name FROM patients WHERE patient_id = '{test_pid}'",
            "Full-Stack"
        )
        
        if llm_ok and fs_ok:
            if llm_patient and fs_patient:
                llm_name = llm_patient[0]["name"] if llm_patient else "Not found"
                fs_name = fs_patient[0]["name"] if fs_patient else "Not found"
                print(f"   LLM Backend: {llm_name}")
                print(f"   Full-Stack: {fs_name}")
                if llm_name == fs_name:
                    print("   ✅ Same patient found in both - Likely same database!")
                else:
                    print("   ❌ Different patient data - Different databases!")
            else:
                print(f"   ⚠️  Patient not found in one or both databases")
    
    # Test 4: Conditions count
    print("\n4️⃣  Conditions Count:")
    llm_ok, llm_conditions = query_database(llm_config, "SELECT COUNT(*) as count FROM conditions", "LLM")
    fs_ok, fs_conditions = query_database(fs_config, "SELECT COUNT(*) as count FROM conditions", "Full-Stack")
    
    if llm_ok and fs_ok:
        llm_count = llm_conditions[0]["count"] if llm_conditions else 0
        fs_count = fs_conditions[0]["count"] if fs_conditions else 0
        print(f"   LLM Backend: {llm_count} conditions")
        print(f"   Full-Stack: {fs_count} conditions")
        if llm_count == fs_count:
            print("   ✅ Counts match!")
        else:
            print("   ❌ Counts differ - Different databases!")
    
    # Test 5: Observations count
    print("\n5️⃣  Observations Count:")
    llm_ok, llm_observations = query_database(llm_config, "SELECT COUNT(*) as count FROM observations", "LLM")
    fs_ok, fs_observations = query_database(fs_config, "SELECT COUNT(*) as count FROM observations", "Full-Stack")
    
    if llm_ok and fs_ok:
        llm_count = llm_observations[0]["count"] if llm_observations else 0
        fs_count = fs_observations[0]["count"] if fs_observations else 0
        print(f"   LLM Backend: {llm_count} observations")
        print(f"   Full-Stack: {fs_count} observations")
        if llm_count == fs_count:
            print("   ✅ Counts match!")
        else:
            print("   ❌ Counts differ - Different databases!")
    
    print()
    print("=" * 70)
    print("📝 SUMMARY")
    print("=" * 70)
    
    # Final verdict
    if llm_config["database"] == fs_config["database"]:
        print("✅ Database names match in configuration")
    else:
        print("⚠️  Database names differ in configuration")
        print("   Check if environment variables override defaults")
    
    print()
    print("💡 RECOMMENDATION:")
    print("   If all counts match and same patient data is found,")
    print("   both teams are using the SAME database.")
    print("   If counts differ, they are using DIFFERENT databases.")
    print()

if __name__ == "__main__":
    main()

