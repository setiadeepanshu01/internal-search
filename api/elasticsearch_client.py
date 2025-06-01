from elasticsearch import Elasticsearch
from langchain_elasticsearch import ElasticsearchChatMessageHistory

import os

ELASTIC_CLOUD_ID = os.getenv("ELASTIC_CLOUD_ID")
ELASTICSEARCH_URL = os.getenv("ELASTICSEARCH_URL")
ELASTIC_API_KEY = os.getenv("ELASTIC_API_KEY")

if ELASTICSEARCH_URL:
    elasticsearch_client = Elasticsearch(
        hosts=[ELASTICSEARCH_URL],
        timeout=30,  # 30 second timeout
        max_retries=3,
        retry_on_timeout=True
    )
elif ELASTIC_CLOUD_ID:
    elasticsearch_client = Elasticsearch(
        cloud_id=ELASTIC_CLOUD_ID, 
        api_key=ELASTIC_API_KEY,
        timeout=30,  # 30 second timeout
        max_retries=3,
        retry_on_timeout=True
    )
else:
    raise ValueError(
        "Please provide either ELASTICSEARCH_URL or ELASTIC_CLOUD_ID and ELASTIC_API_KEY"
    )


def get_elasticsearch_chat_message_history(index, session_id):
    # Check if the index exists
    if not elasticsearch_client.indices.exists(index=index):
        # Create the index with proper mapping for chat history
        # Including the 'created_at' field that's causing the error
        mapping = {
            "mappings": {
                "properties": {
                    "session_id": {"type": "keyword"},
                    "history": {"type": "text"},
                    "created_at": {"type": "date"}
                }
            }
        }
        try:
            elasticsearch_client.indices.create(index=index, body=mapping)
        except Exception as e:
            raise RuntimeError(f"Failed to create index: {e}")
    
    # Return the chat history object
    return ElasticsearchChatMessageHistory(
        es_connection=elasticsearch_client, index=index, session_id=session_id
    )


def update_document_summary(index: str, doc_id: str, summary: str) -> bool:
    """
    Update a document with its generated summary, or remove summary if None.
    
    Args:
        index: Elasticsearch index name
        doc_id: Document ID to update
        summary: Generated summary to save, or None to remove summary field
    
    Returns:
        True if update was successful, False otherwise
    """
    try:
        if summary is None:
            # Remove the summary field
            response = elasticsearch_client.update(
                index=index,
                id=doc_id,
                body={
                    "script": {
                        "source": "ctx._source.remove('summary')",
                        "lang": "painless"
                    }
                }
            )
        else:
            # Update with new summary
            response = elasticsearch_client.update(
                index=index,
                id=doc_id,
                body={
                    "doc": {
                        "summary": summary
                    }
                }
            )
        return response.get("result") in ["updated", "noop"]
    except Exception as e:
        print(f"Error updating document {doc_id} with summary: {str(e)}")
        return False


def get_document_summary(index: str, doc_id: str) -> str:
    """
    Get the existing summary for a document if it exists.
    
    Args:
        index: Elasticsearch index name
        doc_id: Document ID to check
    
    Returns:
        Existing summary or None if not found
    """
    try:
        response = elasticsearch_client.get(
            index=index,
            id=doc_id,
            _source=["summary"]
        )
        return response["_source"].get("summary")
    except Exception:
        return None


def add_summary_field_to_mapping(index: str) -> bool:
    """
    Add the summary field to the existing index mapping.
    
    Args:
        index: Elasticsearch index name
    
    Returns:
        True if mapping was updated successfully, False otherwise
    """
    try:
        # Define the summary field mapping that matches your existing pattern
        summary_mapping = {
            "properties": {
                "summary": {
                    "type": "text",
                    "analyzer": "iq_text_base",
                    "fields": {
                        "delimiter": {
                            "type": "text",
                            "index_options": "freqs",
                            "analyzer": "iq_text_delimiter"
                        },
                        "enum": {
                            "type": "keyword",
                            "ignore_above": 2048
                        },
                        "joined": {
                            "type": "text",
                            "index_options": "freqs",
                            "analyzer": "i_text_bigram",
                            "search_analyzer": "q_text_bigram"
                        },
                        "prefix": {
                            "type": "text",
                            "index_options": "docs",
                            "analyzer": "i_prefix",
                            "search_analyzer": "q_prefix"
                        },
                        "stem": {
                            "type": "text",
                            "analyzer": "iq_text_stem"
                        }
                    }
                }
            }
        }
        
        # Update the mapping
        response = elasticsearch_client.indices.put_mapping(
            index=index,
            body=summary_mapping
        )
        
        print(f"Successfully added summary field to index {index}")
        return True
        
    except Exception as e:
        print(f"Error adding summary field to mapping: {str(e)}")
        return False


def ensure_summary_field_exists(index: str) -> bool:
    """
    Check if summary field exists in mapping, add it if it doesn't.
    
    Args:
        index: Elasticsearch index name
    
    Returns:
        True if summary field exists or was added successfully
    """
    try:
        # Get current mapping
        mapping = elasticsearch_client.indices.get_mapping(index=index)
        
        # Check if summary field exists
        properties = mapping[index]['mappings'].get('properties', {})
        
        if 'summary' not in properties:
            print(f"Summary field not found in {index}, adding it...")
            return add_summary_field_to_mapping(index)
        else:
            print(f"Summary field already exists in {index}")
            return True
            
    except Exception as e:
        print(f"Error checking summary field existence: {str(e)}")
        return False
