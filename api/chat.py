from langchain_elasticsearch import ElasticsearchStore, BM25Strategy
from langchain_elasticsearch import ElasticsearchRetriever
from llm_integrations import get_llm
from elasticsearch_client import (
    elasticsearch_client,
    get_elasticsearch_chat_message_history,
)
from langchain_core.documents import Document
from typing import Dict, Any
from flask import render_template, stream_with_context, current_app
import json
import os

INDEX = os.getenv("ES_INDEX", "search-internal")
INDEX_CHAT_HISTORY = os.getenv(
    "ES_INDEX_CHAT_HISTORY", "search-internal-chat-history"
)
ELSER_MODEL = os.getenv("ELSER_MODEL", ".elser_model_2_linux-x86_64")
SESSION_ID_TAG = "[SESSION_ID]"
SOURCE_TAG = "[SOURCE]"
DONE_TAG = "[DONE]"

text_field = "body"

store = ElasticsearchStore(
    es_connection=elasticsearch_client,
    index_name=INDEX,
    strategy=BM25Strategy(),
)

def bm25_query(search_query: str) -> Dict:
    return {
        "query": {
            "match": {
                text_field: search_query,
            },
        },
        "size": 3
    }

def custom_mapper(hit: Dict[str, Any]) -> Document:
    content = hit["_source"][text_field]
    return Document(
        metadata={"text_content": content},
    )

@stream_with_context
def ask_question(question, session_id):
    yield f"data: {SESSION_ID_TAG} {session_id}\n\n"
    current_app.logger.debug("Chat session ID: %s", session_id)

    chat_history = get_elasticsearch_chat_message_history(
        INDEX_CHAT_HISTORY, session_id
    )

    if len(chat_history.messages) > 0:
        # create a condensed question
        condense_question_prompt = render_template(
            "condense_question_prompt.txt",
            question=question,
            chat_history=chat_history.messages,
        )
        condensed_question = get_llm().invoke(condense_question_prompt).content
    else:
        condensed_question = question

    current_app.logger.debug("Condensed question: %s", condensed_question)
    current_app.logger.debug("Question: %s", question)

    bm25_retriever = ElasticsearchRetriever(
            index_name=INDEX,
            body_func=bm25_query,
            es_client=elasticsearch_client,
            content_field=text_field,
            # document_mapper=custom_mapper,
        )

    docs = bm25_retriever.invoke(condensed_question)
    # docs = store.as_retriever().invoke(condensed_question)
    current_app.logger.debug("Retrieved %s documents", len(docs))
    for doc in docs:
        doc_source = doc.metadata['_source']
        doc_source['body'] = doc.page_content
        current_app.logger.debug(
            "Retrieved document passage from: %s", doc_source.get('name', 'Unknown')
        )
        yield f"data: {SOURCE_TAG} {json.dumps(doc_source)}\n\n"

    qa_prompt = render_template(
        "rag_prompt.txt",
        question=question,
        docs=docs,
        chat_history=chat_history.messages,
    )

    answer = ""
    for chunk in get_llm().stream(qa_prompt):
        content = chunk.content.replace(
            "\n", " "
        )  # the stream can get messed up with newlines
        yield f"data: {content}\n\n"
        answer += chunk.content

    yield f"data: {DONE_TAG}\n\n"
    current_app.logger.debug("Answer: %s", answer)

    chat_history.add_user_message(question)
    chat_history.add_ai_message(answer)
