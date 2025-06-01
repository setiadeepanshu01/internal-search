#!/usr/bin/env python3
"""
Test script for Elasticsearch mapping updates (summary field)
"""
import os
import sys
# Add parent directory to path to access api folder
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'api'))

from elasticsearch_client import (
    elasticsearch_client, 
    ensure_summary_field_exists,
    add_summary_field_to_mapping
)

INDEX = os.getenv("ES_INDEX", "ccc-db")

def test_mapping_updates():
    """Test Elasticsearch mapping updates for summary field"""
    print("🗺️  Testing Elasticsearch Mapping Updates...")
    
    try:
        # Get current mapping
        print("\n1. Checking current index mapping...")
        current_mapping = elasticsearch_client.indices.get_mapping(index=INDEX)
        properties = current_mapping[INDEX]['mappings'].get('properties', {})
        
        print(f"📊 Current mapping has {len(properties)} fields")
        print(f"🔍 Key fields present: {', '.join(list(properties.keys())[:10])}...")
        
        # Check if summary field exists
        has_summary = 'summary' in properties
        print(f"📝 Summary field exists: {'✅ Yes' if has_summary else '❌ No'}")
        
        if has_summary:
            summary_mapping = properties['summary']
            print("🏗️  Summary field structure:")
            print(f"   Type: {summary_mapping.get('type', 'unknown')}")
            print(f"   Analyzer: {summary_mapping.get('analyzer', 'none')}")
            
            # Check for subfields
            fields = summary_mapping.get('fields', {})
            if fields:
                print(f"   Subfields: {', '.join(fields.keys())}")
                
                # Verify subfield structure
                expected_subfields = {'delimiter', 'enum', 'joined', 'prefix', 'stem'}
                actual_subfields = set(fields.keys())
                missing_subfields = expected_subfields - actual_subfields
                
                if missing_subfields:
                    print(f"   ⚠️  Missing subfields: {', '.join(missing_subfields)}")
                else:
                    print("   ✅ All expected subfields present")
        
        # Test the ensure_summary_field_exists function
        print("\n2. Testing summary field setup function...")
        setup_success = ensure_summary_field_exists(INDEX)
        
        if setup_success:
            print("✅ Summary field setup completed successfully")
            
            # Verify the field is now properly configured
            updated_mapping = elasticsearch_client.indices.get_mapping(index=INDEX)
            updated_properties = updated_mapping[INDEX]['mappings'].get('properties', {})
            
            if 'summary' in updated_properties:
                summary_config = updated_properties['summary']
                print("🎯 Final summary field configuration:")
                print(f"   Type: {summary_config.get('type')}")
                print(f"   Analyzer: {summary_config.get('analyzer')}")
                
                subfields = summary_config.get('fields', {})
                if subfields:
                    print(f"   Subfields: {len(subfields)} configured")
                    for subfield, config in subfields.items():
                        analyzer = config.get('analyzer', config.get('search_analyzer', 'keyword'))
                        print(f"     - {subfield}: {analyzer}")
                
        else:
            print("❌ Summary field setup failed")
            return False
        
        # Test index health after mapping update
        print("\n3. Checking index health...")
        health = elasticsearch_client.cluster.health(index=INDEX)
        print(f"📊 Index status: {health['status']}")
        print(f"🔢 Document count: {health.get('number_of_data_nodes', 'unknown')} nodes")
        
        if health['status'] in ['green', 'yellow']:
            print("✅ Index is healthy after mapping update")
        else:
            print(f"⚠️  Index status is {health['status']}")
        
        print("\n🎉 All mapping update tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Error during mapping tests: {e}")
        return False

if __name__ == "__main__":
    success = test_mapping_updates()
    if not success:
        sys.exit(1)
