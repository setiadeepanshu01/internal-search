from elasticsearch import Elasticsearch
from langchain_elasticsearch import ElasticsearchChatMessageHistory

import os

ELASTIC_CLOUD_ID = os.getenv("ELASTIC_CLOUD_ID")
ELASTICSEARCH_URL = os.getenv("ELASTICSEARCH_URL")
ELASTIC_API_KEY = os.getenv("ELASTIC_API_KEY")

if ELASTICSEARCH_URL:
    elasticsearch_client = Elasticsearch(
        hosts=[ELASTICSEARCH_URL],
    )
elif ELASTIC_CLOUD_ID:
    elasticsearch_client = Elasticsearch(
        cloud_id=ELASTIC_CLOUD_ID, api_key=ELASTIC_API_KEY
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
