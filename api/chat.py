from langchain_elasticsearch import ElasticsearchStore, BM25Strategy
from langchain_elasticsearch import ElasticsearchRetriever
from llm_integrations import get_llm, init_openai_config_chat
from elasticsearch_client import (
    elasticsearch_client,
    get_elasticsearch_chat_message_history,
)
from langchain_core.documents import Document
from typing import Dict, Any, AsyncGenerator
from flask import stream_with_context, current_app
from jinja2.nativetypes import NativeEnvironment
from templates import prompt
import json
import os
import asyncio

INDEX = os.getenv("ES_INDEX", "ccc-db")
INDEX_CHAT_HISTORY = os.getenv(
    "ES_INDEX_CHAT_HISTORY", "ccc-db-chat-history"
)
ELSER_MODEL = os.getenv("ELSER_MODEL", ".elser_model_2_linux-x86_64")
SESSION_ID_TAG = "[SESSION_ID]"
SOURCE_TAG = "[SOURCE]"
DONE_TAG = "[DONE]"

text_field = "body"

env = NativeEnvironment()

rags_prompt_template = env.from_string(prompt.rag_template)
condense_question_template = env.from_string(prompt.condense_question_template)
summary_template = env.from_string(prompt.summary_template)

store = ElasticsearchStore(
    es_connection=elasticsearch_client,
    index_name=INDEX,
    strategy=BM25Strategy(),
)

def bm25_query(search_query: str) -> Dict:
    return {
        "query": {
            "bool": {
                "must": [{
                    "exists": {
                        "field": text_field
                    }
                }],
                "should": [
                    {
                        "match": {
                            text_field: {
                                "query": search_query,
                                "boost": 1.0
                            }
                        }
                    },
                    {
                        "match": {
                            "parentReference.path": {
                                "query": search_query,
                                "boost": 2.0
                            }
                        }
                    },
                    {
                        "match": {
                            "name": {
                                "query": search_query,
                                "boost": 2.0
                            }
                        }
                    },
                    {
                        "match": {
                            "webUrl": {
                                "query": search_query,
                                "boost": 1.5
                            }
                        }
                    },
                ],
                "minimum_should_match": 1,
            }
        },
        "size": 5,
    }

async def generate_doc_summary(page_content: str) -> str:
    from langchain_openai import ChatOpenAI
    from portkey_ai import createHeaders, PORTKEY_GATEWAY_URL
    
    # Create a specific ChatOpenAI instance for summarization using gpt-4o-mini
    portkey_headers = createHeaders(
        api_key=os.getenv("PORTKEY_API_KEY"),
        provider="openai",
        metadata={"_user": "mx2-ccc"},
        config={
            "cache": {"mode": "semantic"},
            "retry": {"attempts": 3}
        }
    )
    
    summary_llm = ChatOpenAI(
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        streaming=False,
        temperature=0,
        model='gpt-4.1-mini',
        base_url=PORTKEY_GATEWAY_URL,
        default_headers=portkey_headers
    )
    
    summary_prompt = summary_template.render(page_content=page_content)
    response = await summary_llm.ainvoke(summary_prompt)
    return response.content

@stream_with_context
def ask_question(question, session_id):
    yield f"data: {SESSION_ID_TAG} {session_id}\n\n"
    current_app.logger.debug("Chat session ID: %s", session_id)

    chat_history = get_elasticsearch_chat_message_history(
        INDEX_CHAT_HISTORY, session_id
    )

    if len(chat_history.messages) > 0:
        # create a condensed question
        condense_question_prompt = condense_question_template.render(
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
        )

    docs = bm25_retriever.invoke(condensed_question)
    current_app.logger.debug("Retrieved %s documents", len(docs))

    qa_prompt = rags_prompt_template.render(
        question=question,
        docs=docs,
        chat_history=chat_history.messages,
    )

    answer = ""
    for chunk in get_llm().stream(qa_prompt):
        content = chunk.content.replace(
            "\n", "  "
        )
        yield f"data: {content}\n\n"
        answer += chunk.content

    yield f"data: {DONE_TAG}\n\n"

    # Generate document summaries concurrently
    async def generate_summaries():
        summary_tasks = [generate_doc_summary(doc.page_content) for doc in docs]
        return await asyncio.gather(*summary_tasks)

    # Run the async summary generation
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        summaries = loop.run_until_complete(generate_summaries())
    finally:
        loop.close()

    # Process results and yield source information
    for doc, summary in zip(docs, summaries):
        doc_source = {
            "name": doc.metadata.get("_source", {}).get("name", "Unknown"),
            "summary": doc.page_content[:50] + "...",
            "page_content": summary,
            "url": doc.metadata.get("_source", {}).get("webUrl", ""),
            "category": doc.metadata.get("_source", {}).get("category", "sharepoint"),
            "confidence": doc.metadata.get("_score", 0),
            "updated_at": doc.metadata.get("_source", {}).get("lastModifiedDateTime", None),
        }
        current_app.logger.debug(f'Retrieved document passage from: {doc_source["name"]}')
        yield f"data: {SOURCE_TAG} {json.dumps(doc_source)}\n\n"

    current_app.logger.debug("Answer: %s", answer)

    chat_history.add_user_message(question)
    chat_history.add_ai_message(answer)
