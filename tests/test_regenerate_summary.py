#!/usr/bin/env python3
"""
Script to force regeneration of AI summaries for specific documents
"""
import os
import sys
# Add parent directory to path to access api folder
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'api'))

from elasticsearch_client import (
    elasticsearch_client, 
    update_document_summary,
    get_document_summary
)

INDEX = os.getenv("ES_INDEX", "ccc-db")

def find_document_by_name(document_name):
    """Find a document by its name"""
    try:
        response = elasticsearch_client.search(
            index=INDEX,
            body={
                "query": {
                    "match": {
                        "name": {
                            "query": document_name,
                            "operator": "and"
                        }
                    }
                },
                "size": 10,
                "_source": ["name"]
            }
        )
        
        hits = response['hits']['hits']
        if not hits:
            print(f"❌ No documents found matching '{document_name}'")
            return None
        
        # Show options if multiple matches
        if len(hits) > 1:
            print(f"📄 Found {len(hits)} documents matching '{document_name}':")
            for i, hit in enumerate(hits):
                print(f"  {i+1}. {hit['_source']['name']} (ID: {hit['_id']})")
            
            choice = input(f"\nSelect document (1-{len(hits)}): ")
            try:
                index = int(choice) - 1
                if 0 <= index < len(hits):
                    return hits[index]
                else:
                    print("❌ Invalid selection")
                    return None
            except ValueError:
                print("❌ Invalid selection")
                return None
        else:
            return hits[0]
            
    except Exception as e:
        print(f"❌ Error searching for document: {e}")
        return None

def regenerate_summary_for_document(doc_id, doc_name):
    """Remove the summary for a document, forcing regeneration on next search"""
    try:
        # Check if document has a summary
        existing_summary = get_document_summary(INDEX, doc_id)
        if not existing_summary:
            print(f"ℹ️  Document '{doc_name}' doesn't have a summary yet")
            return True
        
        print(f"📝 Current summary: {existing_summary[:100]}...")
        
        # Remove the summary
        success = update_document_summary(INDEX, doc_id, None)
        if success:
            print(f"✅ Summary removed for '{doc_name}'")
            print("💡 The summary will be regenerated on the next search that includes this document")
            return True
        else:
            print(f"❌ Failed to remove summary for '{doc_name}'")
            return False
            
    except Exception as e:
        print(f"❌ Error removing summary: {e}")
        return False

def list_documents_with_summaries():
    """List all documents that have AI-generated summaries"""
    try:
        response = elasticsearch_client.search(
            index=INDEX,
            body={
                "query": {
                    "exists": {
                        "field": "summary"
                    }
                },
                "size": 100,
                "_source": ["name", "summary"]
            }
        )
        
        hits = response['hits']['hits']
        if not hits:
            print("📄 No documents found with AI summaries")
            return
        
        print(f"📄 Found {len(hits)} documents with AI summaries:\n")
        for i, hit in enumerate(hits, 1):
            doc_name = hit['_source'].get('name', 'Unknown')
            summary = hit['_source'].get('summary', '')
            summary_preview = summary[:80] + "..." if len(summary) > 80 else summary
            print(f"{i:2d}. {doc_name}")
            print(f"    Summary: {summary_preview}")
            print()
        
    except Exception as e:
        print(f"❌ Error listing documents: {e}")

def remove_all_summaries():
    """Remove summaries from all documents"""
    try:
        # Get all documents with summaries
        response = elasticsearch_client.search(
            index=INDEX,
            body={
                "query": {
                    "exists": {
                        "field": "summary"
                    }
                },
                "size": 1000,  # Increased size to handle more documents
                "_source": ["name"]
            }
        )
        
        hits = response['hits']['hits']
        if not hits:
            print("📄 No documents found with AI summaries")
            return
        
        print(f"📄 Found {len(hits)} documents with summaries")
        print("\n⚠️  WARNING: This will remove ALL AI-generated summaries!")
        print("They will be regenerated on the next search that includes each document.")
        
        confirm = input(f"\nRemove summaries from all {len(hits)} documents? Type 'DELETE ALL' to confirm: ").strip()
        
        if confirm != "DELETE ALL":
            print("❌ Operation cancelled")
            return
        
        print("\n🗑️  Removing summaries...")
        success_count = 0
        error_count = 0
        
        for i, hit in enumerate(hits, 1):
            doc_id = hit['_id']
            doc_name = hit['_source'].get('name', 'Unknown')
            
            print(f"  {i:3d}/{len(hits)} - {doc_name[:50]}...", end=" ")
            
            success = update_document_summary(INDEX, doc_id, None)
            if success:
                print("✅")
                success_count += 1
            else:
                print("❌")
                error_count += 1
        
        print(f"\n📊 Results:")
        print(f"   ✅ Successfully removed: {success_count}")
        print(f"   ❌ Failed to remove: {error_count}")
        print(f"   📈 Total processed: {len(hits)}")
        
        if success_count > 0:
            print("\n💡 Summaries will be regenerated automatically on next search!")
        
    except Exception as e:
        print(f"❌ Error during bulk removal: {e}")

def main():
    print("🔄 AI Summary Regeneration Tool")
    print("=" * 40)
    
    while True:
        print("\nOptions:")
        print("1. Regenerate summary for specific document")
        print("2. List all documents with summaries")
        print("3. Remove ALL summaries (bulk regeneration)")
        print("4. Exit")
        
        choice = input("\nSelect option (1-4): ").strip()
        
        if choice == "1":
            document_name = input("\nEnter document name (or part of it): ").strip()
            if not document_name:
                print("❌ Please enter a document name")
                continue
            
            doc = find_document_by_name(document_name)
            if doc:
                doc_id = doc['_id']
                doc_name = doc['_source']['name']
                print(f"\n🎯 Selected: {doc_name}")
                
                confirm = input(f"Remove summary for '{doc_name}'? (y/N): ").strip().lower()
                if confirm in ['y', 'yes']:
                    regenerate_summary_for_document(doc_id, doc_name)
                else:
                    print("❌ Cancelled")
        
        elif choice == "2":
            print("\n📋 Documents with AI summaries:")
            print("-" * 40)
            list_documents_with_summaries()
        
        elif choice == "3":
            print("\n🗑️  Bulk Summary Removal:")
            print("-" * 40)
            remove_all_summaries()
        
        elif choice == "4":
            print("👋 Goodbye!")
            break
        
        else:
            print("❌ Invalid option. Please select 1, 2, 3, or 4.")

if __name__ == "__main__":
    main()
