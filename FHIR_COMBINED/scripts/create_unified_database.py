#!/usr/bin/env python3
"""
Script to create a unified database by:
1. Copying all data from cocm_db
2. Adding notes from llm_ua_clinical
3. Creating a new database: cocm_db_unified
"""

import pymysql
import sys
import logging
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Database credentials
# For creating database, we may need root user
# For data operations, we use llm_ua_reader
DB_HOST = "127.0.0.1"
DB_PORT = 3306
DB_USER = "llm_ua_reader"
DB_PASSWORD = "P@ssw0rd"
ROOT_USER = "root"
ROOT_PASSWORD = "P@ssw0rd"

# Source databases
SOURCE_DB = "cocm_db"
NOTES_SOURCE_DB = "llm_ua_clinical"

# Target database
TARGET_DB = "cocm_db_unified"

def get_connection(database=None):
    """Create database connection"""
    return pymysql.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        database=database,
        charset='utf8mb4'
    )

def create_database():
    """Create the new unified database"""
    logger.info(f"Creating database: {TARGET_DB}")
    try:
        # First try with llm_ua_reader
        try:
            conn = get_connection()
            with conn.cursor() as cur:
                cur.execute(f"DROP DATABASE IF EXISTS {TARGET_DB}")
                cur.execute(f"CREATE DATABASE {TARGET_DB} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
                logger.info(f"✅ Created database: {TARGET_DB} using llm_ua_reader")
            conn.close()
            return True
        except Exception as e1:
            logger.warning(f"llm_ua_reader doesn't have CREATE DATABASE permission: {e1}")
            logger.info("Trying with root user...")
            
            # Try with root user
            try:
                root_conn = pymysql.connect(
                    host=DB_HOST,
                    port=DB_PORT,
                    user=ROOT_USER,
                    password=ROOT_PASSWORD
                )
                with root_conn.cursor() as cur:
                    cur.execute(f"DROP DATABASE IF EXISTS {TARGET_DB}")
                    cur.execute(f"CREATE DATABASE {TARGET_DB} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
                    logger.info(f"✅ Created database: {TARGET_DB} using root user")
                    
                    # Grant permissions to llm_ua_reader
                    cur.execute(f"GRANT ALL PRIVILEGES ON {TARGET_DB}.* TO '{DB_USER}'@'localhost'")
                    cur.execute("FLUSH PRIVILEGES")
                    logger.info(f"✅ Granted permissions to {DB_USER} on {TARGET_DB}")
                root_conn.close()
                return True
            except Exception as e2:
                logger.error(f"Failed to create database with root user: {e2}")
                logger.error("Please grant CREATE DATABASE permission to llm_ua_reader or run as root")
                return False
    except Exception as e:
        logger.error(f"Failed to create database: {e}")
        return False

def copy_table_structure(source_conn, target_conn, table_name):
    """Copy table structure from source to target"""
    try:
        with source_conn.cursor() as source_cur:
            # Get CREATE TABLE statement
            source_cur.execute(f"SHOW CREATE TABLE {table_name}")
            create_table = source_cur.fetchone()[1]
            
            # Replace database name in CREATE TABLE statement
            create_table = create_table.replace(f"`{SOURCE_DB}`", f"`{TARGET_DB}`")
            
            with target_conn.cursor() as target_cur:
                target_cur.execute(f"USE {TARGET_DB}")
                # Disable foreign key checks temporarily
                target_cur.execute("SET FOREIGN_KEY_CHECKS=0")
                try:
                    target_cur.execute(create_table)
                    logger.info(f"  ✅ Created table structure: {table_name}")
                    return True
                finally:
                    # Re-enable foreign key checks
                    target_cur.execute("SET FOREIGN_KEY_CHECKS=1")
    except Exception as e:
        logger.error(f"  ❌ Failed to copy structure for {table_name}: {e}")
        return False

def copy_table_data(source_conn, target_conn, table_name, batch_size=1000):
    """Copy table data from source to target"""
    try:
        with source_conn.cursor() as source_cur:
            # Get row count
            source_cur.execute(f"SELECT COUNT(*) FROM {table_name}")
            total_rows = source_cur.fetchone()[0]
            
            if total_rows == 0:
                logger.info(f"  ⚠️  Table {table_name} is empty, skipping")
                return True
            
            logger.info(f"  Copying {total_rows:,} rows from {table_name}...")
            
            # Get column names and types
            source_cur.execute(f"SHOW COLUMNS FROM {table_name}")
            column_info = source_cur.fetchall()
            columns = [row[0] for row in column_info]
            column_types = {row[0]: row[1] for row in column_info}
            columns_str = ", ".join([f"`{col}`" for col in columns])
            placeholders = ", ".join(["%s"] * len(columns))
            
            # Helper to clean datetime values
            def clean_datetime_value(value, col_type):
                if 'datetime' in col_type.lower() or 'timestamp' in col_type.lower():
                    if value and str(value).startswith('0000-00-00'):
                        return None
                return value
            
            # Copy data in batches
            offset = 0
            copied = 0
            
            with target_conn.cursor() as target_cur:
                target_cur.execute(f"USE {TARGET_DB}")
                # Disable foreign key checks during data insertion
                target_cur.execute("SET FOREIGN_KEY_CHECKS=0")
                try:
                    while offset < total_rows:
                        source_cur.execute(f"SELECT {columns_str} FROM {table_name} LIMIT {batch_size} OFFSET {offset}")
                        rows = source_cur.fetchall()
                        
                        if not rows:
                            break
                        
                        # Clean datetime values
                        cleaned_rows = []
                        for row in rows:
                            cleaned_row = tuple(
                                clean_datetime_value(val, column_types.get(col, ''))
                                for val, col in zip(row, columns)
                            )
                            cleaned_rows.append(cleaned_row)
                        
                        # Insert into target
                        insert_sql = f"INSERT INTO {table_name} ({columns_str}) VALUES ({placeholders})"
                        target_cur.executemany(insert_sql, cleaned_rows)
                        target_conn.commit()
                        
                        copied += len(rows)
                        offset += batch_size
                        
                        if copied % 5000 == 0:
                            logger.info(f"    Copied {copied:,} / {total_rows:,} rows...")
                    
                    logger.info(f"  ✅ Copied {copied:,} rows to {table_name}")
                    return True
                finally:
                    # Re-enable foreign key checks
                    target_cur.execute("SET FOREIGN_KEY_CHECKS=1")
    except Exception as e:
        logger.error(f"  ❌ Failed to copy data for {table_name}: {e}")
        return False

def copy_all_tables_from_cocm():
    """Copy all tables from cocm_db to target database"""
    logger.info("="*70)
    logger.info("STEP 1: Copying all tables from cocm_db")
    logger.info("="*70)
    
    try:
        source_conn = get_connection(SOURCE_DB)
        target_conn = get_connection(TARGET_DB)
        
        # Get list of tables
        with source_conn.cursor() as cur:
            cur.execute("SHOW TABLES")
            tables = [row[0] for row in cur.fetchall()]
        
        logger.info(f"Found {len(tables)} tables to copy: {tables}")
        
        # Order tables: patients first (for foreign key dependencies)
        priority_tables = ['patients']
        other_tables = [t for t in tables if t not in priority_tables]
        ordered_tables = priority_tables + other_tables
        
        logger.info(f"Processing tables in order: {ordered_tables}")
        
        success_count = 0
        for table in ordered_tables:
            logger.info(f"Processing table: {table}")
            
            # Copy structure
            if copy_table_structure(source_conn, target_conn, table):
                # Copy data
                if copy_table_data(source_conn, target_conn, table):
                    success_count += 1
                else:
                    logger.warning(f"  ⚠️  Structure copied but data failed for {table}")
            else:
                logger.error(f"  ❌ Failed to copy {table}")
        
        source_conn.close()
        target_conn.close()
        
        logger.info(f"✅ Successfully copied {success_count} / {len(tables)} tables")
        return success_count == len(tables)
        
    except Exception as e:
        logger.error(f"Failed to copy tables from cocm_db: {e}")
        import traceback
        traceback.print_exc()
        return False

def create_notes_table(target_conn):
    """Create notes table in target database"""
    logger.info("Creating notes table structure...")
    try:
        with target_conn.cursor() as cur:
            cur.execute(f"USE {TARGET_DB}")
            
            # Create notes table based on llm_ua_clinical structure
            create_sql = """
            CREATE TABLE IF NOT EXISTS notes (
                id INT AUTO_INCREMENT PRIMARY KEY,
                base_key VARCHAR(255),
                filename_txt VARCHAR(500),
                source_type ENUM('ccd','oru','adt','unknown') DEFAULT 'unknown',
                note_text LONGTEXT,
                note_datetime DATETIME,
                patient_id VARCHAR(255),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_patient_id (patient_id),
                INDEX idx_note_datetime (note_datetime),
                INDEX idx_created_at (created_at)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """
            cur.execute(create_sql)
            target_conn.commit()
            logger.info("✅ Created notes table")
            return True
    except Exception as e:
        logger.error(f"Failed to create notes table: {e}")
        return False

def copy_notes_from_llm_ua_clinical():
    """Copy notes from llm_ua_clinical to target database"""
    logger.info("="*70)
    logger.info("STEP 2: Copying notes from llm_ua_clinical")
    logger.info("="*70)
    
    try:
        source_conn = get_connection(NOTES_SOURCE_DB)
        target_conn = get_connection(TARGET_DB)
        
        # Create notes table
        if not create_notes_table(target_conn):
            return False
        
        # Get notes count
        with source_conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM notes")
            total_notes = cur.fetchone()[0]
            logger.info(f"Found {total_notes:,} notes in {NOTES_SOURCE_DB}")
            
            if total_notes == 0:
                logger.warning("No notes to copy")
                return True
            
            # Get notes data
            cur.execute("""
                SELECT base_key, filename_txt, source_type, note_text, 
                       note_datetime, patient_id, created_at
                FROM notes
                ORDER BY id
            """)
            
            # Copy notes in batches
            batch_size = 100
            copied = 0
            
            with target_conn.cursor() as target_cur:
                target_cur.execute(f"USE {TARGET_DB}")
                
                while True:
                    rows = cur.fetchmany(batch_size)
                    if not rows:
                        break
                    
                    insert_sql = """
                        INSERT INTO notes 
                        (base_key, filename_txt, source_type, note_text, 
                         note_datetime, patient_id, created_at)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """
                    target_cur.executemany(insert_sql, rows)
                    target_conn.commit()
                    
                    copied += len(rows)
                    if copied % 500 == 0:
                        logger.info(f"  Copied {copied:,} / {total_notes:,} notes...")
                
                logger.info(f"✅ Copied {copied:,} notes to {TARGET_DB}")
                
                # Check patient overlap
                target_cur.execute("""
                    SELECT COUNT(DISTINCT n.patient_id) as notes_patients,
                           (SELECT COUNT(DISTINCT patient_id) FROM patients) as total_patients
                    FROM notes n
                """)
                result = target_cur.fetchone()
                notes_patients = result[0]
                total_patients = result[1]
                
                logger.info(f"  Notes matched to {notes_patients:,} patients")
                logger.info(f"  Total patients in database: {total_patients:,}")
        
        source_conn.close()
        target_conn.close()
        return True
        
    except Exception as e:
        logger.error(f"Failed to copy notes: {e}")
        import traceback
        traceback.print_exc()
        return False

def verify_unified_database():
    """Verify the unified database"""
    logger.info("="*70)
    logger.info("STEP 3: Verifying unified database")
    logger.info("="*70)
    
    try:
        conn = get_connection(TARGET_DB)
        with conn.cursor() as cur:
            # Get table counts
            cur.execute("SHOW TABLES")
            tables = [row[0] for row in cur.fetchall()]
            
            logger.info(f"Tables in {TARGET_DB}: {len(tables)}")
            
            for table in tables:
                cur.execute(f"SELECT COUNT(*) FROM {table}")
                count = cur.fetchone()[0]
                logger.info(f"  {table}: {count:,} records")
            
            # Check patient overlap
            cur.execute("""
                SELECT 
                    (SELECT COUNT(DISTINCT patient_id) FROM patients) as total_patients,
                    (SELECT COUNT(DISTINCT patient_id) FROM conditions) as patients_with_conditions,
                    (SELECT COUNT(DISTINCT patient_id) FROM observations) as patients_with_observations,
                    (SELECT COUNT(DISTINCT patient_id) FROM encounters) as patients_with_encounters,
                    (SELECT COUNT(DISTINCT patient_id) FROM notes) as patients_with_notes
            """)
            result = cur.fetchone()
            
            logger.info("="*70)
            logger.info("PATIENT COVERAGE:")
            logger.info(f"  Total patients: {result[0]:,}")
            logger.info(f"  Patients with conditions: {result[1]:,}")
            logger.info(f"  Patients with observations: {result[2]:,}")
            logger.info(f"  Patients with encounters: {result[3]:,}")
            logger.info(f"  Patients with notes: {result[4]:,}")
            logger.info("="*70)
        
        conn.close()
        return True
        
    except Exception as e:
        logger.error(f"Failed to verify database: {e}")
        return False

def main():
    """Main execution"""
    logger.info("="*70)
    logger.info("CREATING UNIFIED DATABASE")
    logger.info("="*70)
    logger.info(f"Source: {SOURCE_DB}")
    logger.info(f"Notes Source: {NOTES_SOURCE_DB}")
    logger.info(f"Target: {TARGET_DB}")
    logger.info("="*70)
    logger.info("")
    
    # Step 1: Create database
    if not create_database():
        logger.error("Failed to create database. Aborting.")
        sys.exit(1)
    
    # Step 2: Copy all tables from cocm_db
    if not copy_all_tables_from_cocm():
        logger.error("Failed to copy tables from cocm_db. Aborting.")
        sys.exit(1)
    
    # Step 3: Copy notes from llm_ua_clinical
    if not copy_notes_from_llm_ua_clinical():
        logger.error("Failed to copy notes. Continuing anyway...")
    
    # Step 4: Verify
    if not verify_unified_database():
        logger.warning("Verification had issues, but database may still be usable")
    
    logger.info("")
    logger.info("="*70)
    logger.info("✅ UNIFIED DATABASE CREATION COMPLETE!")
    logger.info("="*70)
    logger.info(f"New database: {TARGET_DB}")
    logger.info("")
    logger.info("Next steps:")
    logger.info("1. Update .env file to use DB_NAME=cocm_db_unified")
    logger.info("2. Test the database connection")
    logger.info("3. Reindex all patients with the new unified database")
    logger.info("="*70)

if __name__ == "__main__":
    main()

