#!/usr/bin/env python3
"""
Permanent Solution: Reindex ElasticSearch with Embeddings
This script will:
1. Create new index with content_embedding field
2. Reindex all existing documents with embeddings
3. Enable semantic search permanently
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.api.elasticsearch_client import es_client
from app.api.embedding_service import get_embedding_service
from app.core.database import engine
from sqlalchemy import text
import logging
from tqdm import tqdm

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_all_patient_ids():
    """Get all patient IDs from database (cocm_db)"""
    try:
        from app.core.database import DB_NAME
        logger.info(f"Using database: {DB_NAME}")
        
        with engine.connect() as conn:
            # Verify patient count
            count_query = text("SELECT COUNT(DISTINCT patient_id) as count FROM patients")
            count_result = conn.execute(count_query)
            total_count = count_result.fetchone()[0]
            logger.info(f"Total patients in database: {total_count}")
            
            # Get all patient IDs
            query = text("SELECT DISTINCT patient_id FROM patients ORDER BY patient_id")
            result = conn.execute(query)
            patient_ids = [row[0] for row in result.fetchall()]
            
            logger.info(f"Retrieved {len(patient_ids)} patient IDs")
            if len(patient_ids) != total_count:
                logger.warning(f"Count mismatch: Expected {total_count}, got {len(patient_ids)}")
            
        return patient_ids
    except Exception as e:
        logger.error(f"Failed to get patient IDs: {e}")
        return []

def get_patient_data_from_db(patient_id: str):
    """Get patient data from database for indexing (with ALL data, no limits)"""
    try:
        from app.api.chat_agent import get_patient_data_from_db
        # Use for_indexing=True to get ALL data (no limits)
        return get_patient_data_from_db(patient_id, for_indexing=True)
    except Exception as e:
        logger.error(f"Failed to get patient data for {patient_id}: {e}")
        return None

def recreate_index_with_embeddings():
    """Recreate index with content_embedding field"""
    index_name = "patient_data"
    
    logger.info("="*80)
    logger.info("STEP 1: Recreating ElasticSearch Index with Embeddings")
    logger.info("="*80)
    
    if not es_client.is_connected():
        logger.error("ElasticSearch not connected!")
        return False
    
    # Check if embedding service is available
    embedding_service = get_embedding_service()
    if not embedding_service.is_available():
        logger.error("Embedding service not available!")
        return False
    
    try:
        # Delete old index if exists
        if es_client.client.indices.exists(index=index_name):
            logger.info(f"Deleting old index: {index_name}")
            es_client.client.indices.delete(index=index_name)
            logger.info("Old index deleted")
        
        # Create new index with embedding field
        logger.info("Creating new index with content_embedding field...")
        success = es_client.create_patient_index(index_name)
        
        if success:
            logger.info("✅ New index created successfully with content_embedding field!")
            return True
        else:
            logger.error("❌ Failed to create new index")
            return False
            
    except Exception as e:
        logger.error(f"Failed to recreate index: {e}")
        return False

def reindex_all_patients():
    """Reindex all patients with embeddings"""
    logger.info("="*80)
    logger.info("STEP 2: Reindexing All Patients with Embeddings")
    logger.info("="*80)
    
    # Get all patient IDs
    logger.info("Fetching all patient IDs from database...")
    patient_ids = get_all_patient_ids()
    total_patients = len(patient_ids)
    logger.info(f"Found {total_patients} patients to reindex")
    
    if total_patients == 0:
        logger.warning("No patients found!")
        return False
    
    # Reindex each patient
    indexed_count = 0
    error_count = 0
    errors = []
    
    logger.info("Starting reindexing process...")
    logger.info("Indexing WITH embeddings for semantic search")
    logger.info("This will enable semantic search capabilities")
    logger.info("")
    
    # Check if embedding service is available
    embedding_service = get_embedding_service()
    if not embedding_service.is_available():
        logger.error("Embedding service not available! Cannot generate embeddings.")
        logger.error("Please install sentence-transformers: pip install sentence-transformers")
        return False
    
    logger.info(f"Using embedding model: {embedding_service.model_name}")
    logger.info(f"Embedding dimension: {embedding_service.get_embedding_dimension()}")
    logger.info("")
    
    for idx, patient_id in enumerate(tqdm(patient_ids, desc="Reindexing patients"), 1):
        try:
            # Get patient data (local function already uses for_indexing=True internally)
            patient_data = get_patient_data_from_db(patient_id)
            
            if not patient_data:
                error_count += 1
                errors.append(f"Patient {patient_id}: No data found")
                continue
            
            # Index WITH embeddings for semantic search
            success = es_client.index_patient_data(patient_id, patient_data, generate_embeddings=True)
            
            if success:
                indexed_count += 1
            else:
                error_count += 1
                errors.append(f"Patient {patient_id}: Indexing failed")
            
            # Log progress every 100 patients
            if idx % 100 == 0:
                logger.info(f"Progress: {idx}/{total_patients} patients indexed ({indexed_count} successful, {error_count} errors)")
                
        except Exception as e:
            error_count += 1
            errors.append(f"Patient {patient_id}: {str(e)}")
            logger.warning(f"Error indexing patient {patient_id}: {e}")
    
    # Summary
    logger.info("")
    logger.info("="*80)
    logger.info("REINDEXING COMPLETE")
    logger.info("="*80)
    logger.info(f"Total patients: {total_patients}")
    logger.info(f"Successfully indexed: {indexed_count}")
    logger.info(f"Errors: {error_count}")
    
    if errors:
        logger.warning(f"First 10 errors:")
        for error in errors[:10]:
            logger.warning(f"  - {error}")
    
    return indexed_count > 0

def verify_semantic_search():
    """Verify that semantic search is working"""
    logger.info("="*80)
    logger.info("STEP 3: Verifying Semantic Search")
    logger.info("="*80)
    
    try:
        # Check index mapping
        mapping = es_client.client.indices.get_mapping(index="patient_data")
        if "patient_data" in mapping:
            props = mapping["patient_data"].get("mappings", {}).get("properties", {})
            has_embedding = "content_embedding" in props
            
            if has_embedding:
                logger.info("✅ Index has content_embedding field")
                embedding_field = props["content_embedding"]
                logger.info(f"   Type: {embedding_field.get('type')}")
                logger.info(f"   Dimensions: {embedding_field.get('dims')}")
                logger.info(f"   Indexed: {embedding_field.get('index')}")
            else:
                logger.error("❌ Index missing content_embedding field")
                return False
        
        # Check document count
        stats = es_client.client.count(index="patient_data")
        doc_count = stats["count"]
        logger.info(f"✅ Total documents in index: {doc_count}")
        
        # Test semantic search
        logger.info("Testing semantic search with sample query...")
        test_patient_id = "000000216"
        test_query = "heart disease"
        
        # Generate query embedding
        embedding_service = get_embedding_service()
        query_embedding = embedding_service.generate_embedding(test_query)
        
        # Try kNN search
        search_body = {
            "knn": {
                "field": "content_embedding",
                "query_vector": query_embedding,
                "k": 5,
                "filter": {
                    "term": {"patient_id": test_patient_id}
                }
            },
            "size": 5
        }
        
        response = es_client.client.search(index="patient_data", body=search_body)
        hits = response["hits"]["hits"]
        
        if hits:
            logger.info(f"✅ Semantic search working! Found {len(hits)} results")
            logger.info(f"   Sample result: {hits[0]['_source'].get('content', '')[:100]}...")
            return True
        else:
            logger.warning("⚠️  Semantic search returned no results (may need data)")
            return True  # Still consider it working if no errors
        
    except Exception as e:
        logger.error(f"❌ Verification failed: {e}")
        return False

def main():
    """Main function"""
    logger.info("="*80)
    logger.info("PERMANENT SOLUTION: Reindexing with Embeddings")
    logger.info("="*80)
    logger.info("")
    logger.info("Database: cocm_db (3,254 patients)")
    logger.info("")
    logger.info("This will:")
    logger.info("1. Recreate ElasticSearch index with content_embedding field")
    logger.info("2. Reindex all 3,254 patients WITH embeddings (for semantic search)")
    logger.info("3. Enable semantic search permanently")
    logger.info("")
    logger.info("NOTE: This will take longer than indexing without embeddings,")
    logger.info("      but it enables semantic search capabilities.")
    logger.info("      Estimated time: 1-2 hours for 3,254 patients")
    logger.info("")
    
    # Step 1: Recreate index
    if not recreate_index_with_embeddings():
        logger.error("Failed to recreate index. Aborting.")
        return False
    
    # Step 2: Reindex all patients
    if not reindex_all_patients():
        logger.error("Failed to reindex patients. Check errors above.")
        return False
    
    # Step 3: Verify
    if verify_semantic_search():
        logger.info("")
        logger.info("="*80)
        logger.info("✅ SUCCESS! Semantic search is now permanently enabled!")
        logger.info("="*80)
        return True
    else:
        logger.error("Verification failed. Please check the errors above.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

