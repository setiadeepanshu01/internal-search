import os
import logging
from elasticsearch import Elasticsearch, NotFoundError, ApiError
from dotenv import load_dotenv
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_elasticsearch_connection():
    """Test the basic Elasticsearch connection and diagnose issues"""
    try:
        ELASTIC_CLOUD_ID = os.getenv("ELASTIC_CLOUD_ID")
        ELASTIC_API_KEY = os.getenv("ELASTIC_API_KEY")
        ES_INDEX = os.getenv("ES_INDEX", "ccc-db")
        ES_INDEX_CHAT_HISTORY = os.getenv("ES_INDEX_CHAT_HISTORY", "ccc-db-chat-history")
        
        logger.info(f"Using Elasticsearch Cloud ID: {ELASTIC_CLOUD_ID[:10]}...")
        logger.info(f"Configured index: {ES_INDEX}")
        logger.info(f"Configured chat history index: {ES_INDEX_CHAT_HISTORY}")
        
        # Create Elasticsearch client
        es_client = Elasticsearch(cloud_id=ELASTIC_CLOUD_ID, api_key=ELASTIC_API_KEY)
        
        # Test basic connection
        info = es_client.info()
        logger.info(f"Successfully connected to Elasticsearch version: {info.get('version', {}).get('number', 'unknown')}")
        
        # List available indices
        indices = es_client.indices.get_alias(index="*")
        logger.info(f"Available indices: {list(indices.keys())}")
        
        # Check if our indices exist
        if ES_INDEX in indices:
            logger.info(f"Main index '{ES_INDEX}' exists.")
        else:
            logger.warning(f"Main index '{ES_INDEX}' does not exist. Available indices: {list(indices.keys())}")
        
        if ES_INDEX_CHAT_HISTORY in indices:
            logger.info(f"Chat history index '{ES_INDEX_CHAT_HISTORY}' exists.")
        else:
            logger.warning(f"Chat history index '{ES_INDEX_CHAT_HISTORY}' does not exist. Will be created on first use.")
        
        # Try to create chat history index
        if not es_client.indices.exists(index=ES_INDEX_CHAT_HISTORY):
            logger.info(f"Creating chat history index '{ES_INDEX_CHAT_HISTORY}'...")
            
            es_client.indices.create(
                index=ES_INDEX_CHAT_HISTORY,
                body={
                    "mappings": {
                        "properties": {
                            "type": {"type": "keyword"},
                            "data": {"type": "text"},
                            "session_id": {"type": "keyword"}
                        }
                    }
                }
            )
            logger.info(f"Successfully created chat history index")
        
        return True
    
    except NotFoundError as e:
        logger.error(f"Index not found error: {e}")
        if hasattr(e, 'info') and e.info:
            logger.error(f"Detailed error info: {e.info}")
        return False
        
    except ApiError as e:
        logger.error(f"Elasticsearch API error: {e}")
        if hasattr(e, 'info') and e.info:
            logger.error(f"Detailed error info: {e.info}")
        return False
        
    except Exception as e:
        logger.error(f"Error connecting to Elasticsearch: {e}")
        return False

def test_chat_history_operations():
    """Test the specific operations that are failing in the application"""
    try:
        ELASTIC_CLOUD_ID = os.getenv("ELASTIC_CLOUD_ID")
        ELASTIC_API_KEY = os.getenv("ELASTIC_API_KEY")
        ES_INDEX_CHAT_HISTORY = os.getenv("ES_INDEX_CHAT_HISTORY", "ccc-db-chat-history")
        
        # Create Elasticsearch client
        es_client = Elasticsearch(cloud_id=ELASTIC_CLOUD_ID, api_key=ELASTIC_API_KEY)
        
        # Generate a test session ID
        session_id = "test-session-id"
        
        # Try to add a message (this is what's failing in the application)
        doc = {
            "type": "human",
            "data": "This is a test message",
            "session_id": session_id
        }
        
        # First, make sure index exists
        if not es_client.indices.exists(index=ES_INDEX_CHAT_HISTORY):
            logger.info(f"Creating chat history index '{ES_INDEX_CHAT_HISTORY}'...")
            
            es_client.indices.create(
                index=ES_INDEX_CHAT_HISTORY,
                body={
                    "mappings": {
                        "properties": {
                            "type": {"type": "keyword"},
                            "data": {"type": "text"},
                            "session_id": {"type": "keyword"}
                        }
                    }
                }
            )
        
        # Try to insert a document
        logger.info(f"Attempting to insert a test document into {ES_INDEX_CHAT_HISTORY}")
        result = es_client.index(index=ES_INDEX_CHAT_HISTORY, document=doc)
        logger.info(f"Document insertion result: {result}")
        
        # Try to retrieve the document
        logger.info(f"Attempting to retrieve documents from {ES_INDEX_CHAT_HISTORY}")
        query = {
            "query": {
                "term": {
                    "session_id": session_id
                }
            }
        }
        
        search_result = es_client.search(index=ES_INDEX_CHAT_HISTORY, body=query)
        logger.info(f"Search result: {search_result}")
        
        return True
        
    except NotFoundError as e:
        logger.error(f"Index not found error: {e}")
        if hasattr(e, 'info') and e.info:
            logger.error(f"Detailed error info: {e.info}")
        return False
        
    except ApiError as e:
        logger.error(f"Elasticsearch API error: {e}")
        if hasattr(e, 'info') and e.info:
            logger.error(f"Detailed error info: {e.info}")
        return False
        
    except Exception as e:
        logger.error(f"Error in chat history operations: {e}")
        return False

if __name__ == "__main__":
    print("Testing Elasticsearch connection...")
    success = test_elasticsearch_connection()
    if success:
        print("Elasticsearch connection test passed!")
    else:
        print("Elasticsearch connection test failed. Check the logs for details.")
        
    print("\nTesting chat history operations...")
    success = test_chat_history_operations()
    if success:
        print("Chat history operations test passed!")
    else:
        print("Chat history operations test failed. Check the logs for details.")
