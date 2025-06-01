#!/usr/bin/env python3
"""
Test script for Elasticsearch summary storage functionality
"""
import os
import sys
# Add parent directory to path to access api folder
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'api'))

from elasticsearch_client import (
    elasticsearch_client, 
    update_document_summary, 
    get_document_summary,
    ensure_summary_field_exists
)

INDEX = os.getenv("ES_INDEX", "ccc-db")

def test_summary_storage():
    """Test summary storage and retrieval functionality"""
    print("🧪 Testing Summary Storage Functionality...")
    
    # Ensure summary field exists
    print("\n1. Checking summary field mapping...")
    mapping_success = ensure_summary_field_exists(INDEX)
    if mapping_success:
        print("✅ Summary field mapping verified/added")
    else:
        print("❌ Failed to setup summary field mapping")
        return False
    
    # Test document ID (using a known document from your index)
    try:
        # Get a real document from the index
        search_response = elasticsearch_client.search(
            index=INDEX,
            body={
                "query": {"match_all": {}},
                "size": 1
            }
        )
        
        if not search_response['hits']['hits']:
            print("❌ No documents found in index for testing")
            return False
            
        doc = search_response['hits']['hits'][0]
        test_doc_id = doc['_id']
        doc_name = doc['_source'].get('name', 'Unknown')
        print(f"📄 Using test document: {doc_name} (ID: {test_doc_id})")
        
    except Exception as e:
        print(f"❌ Error finding test document: {e}")
        return False
    
    # Test summary storage
    print("\n2. Testing summary storage...")
    test_summary = "This is a test AI-generated summary for document validation."
    
    storage_success = update_document_summary(INDEX, test_doc_id, test_summary)
    if storage_success:
        print("✅ Summary stored successfully")
    else:
        print("❌ Failed to store summary")
        return False
    
    # Test summary retrieval
    print("\n3. Testing summary retrieval...")
    retrieved_summary = get_document_summary(INDEX, test_doc_id)
    
    if retrieved_summary == test_summary:
        print("✅ Summary retrieved successfully and matches stored version")
        print(f"📝 Retrieved: {retrieved_summary}")
    else:
        print(f"❌ Summary mismatch!")
        print(f"   Stored: {test_summary}")
        print(f"   Retrieved: {retrieved_summary}")
        return False
    
    # Clean up test data
    print("\n4. Cleaning up test data...")
    cleanup_success = update_document_summary(INDEX, test_doc_id, None)
    if cleanup_success:
        print("✅ Test data cleaned up successfully")
    else:
        print("⚠️  Warning: Could not clean up test data")
    
    print("\n🎉 All summary storage tests passed!")
    return True

if __name__ == "__main__":
    success = test_summary_storage()
    if not success:
        sys.exit(1)
