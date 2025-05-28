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
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

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

    # Send basic source information immediately after retrieval
    for doc in docs:
        basic_source = {
            "name": doc.metadata.get("_source", {}).get("name", "Unknown"),
            "summary": doc.page_content[:100] + "...",  # Quick preview
            "page_content": "Loading summary...",  # Placeholder
            "url": doc.metadata.get("_source", {}).get("webUrl", ""),
            "category": doc.metadata.get("_source", {}).get("category", "sharepoint"),
            "confidence": doc.metadata.get("_score", 0),
            "updated_at": doc.metadata.get("_source", {}).get("lastModifiedDateTime", None),
            "loading": True  # Indicate that summary is being generated
        }
        current_app.logger.debug(f'Retrieved document passage from: {basic_source["name"]}')
        yield f"data: {SOURCE_TAG} {json.dumps(basic_source)}\n\n"

    # Start summary generation in background using threading
    def generate_single_summary(page_content):
        """Wrapper function to run async summary generation in a thread"""
        import asyncio
        import time
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            # Run the async function
            result = loop.run_until_complete(generate_doc_summary(page_content))
            
            # Wait a bit for any pending tasks to complete
            pending_tasks = asyncio.all_tasks(loop)
            if pending_tasks:
                loop.run_until_complete(asyncio.gather(*pending_tasks, return_exceptions=True))
            
            return result
        except Exception as e:
            current_app.logger.error(f"Summary generation error: {e}")
            return "Summary generation failed"
        finally:
            # Give the loop a moment to clean up
            try:
                # Cancel any remaining tasks
                pending_tasks = asyncio.all_tasks(loop)
                for task in pending_tasks:
                    task.cancel()
                
                # Run one more time to let cancellations process
                if pending_tasks:
                    loop.run_until_complete(asyncio.gather(*pending_tasks, return_exceptions=True))
                    
            except Exception:
                pass  # Ignore cleanup errors
            finally:
                loop.close()

    # Start summary generation in parallel threads
    executor = ThreadPoolExecutor(max_workers=min(len(docs), 5))
    summary_futures = {
        executor.submit(generate_single_summary, doc.page_content): i 
        for i, doc in enumerate(docs)
    }

    qa_prompt = rags_prompt_template.render(
        question=question,
        docs=docs,
        chat_history=chat_history.messages,
    )

    # Stream the answer while summaries are being generated
    answer = ""
    for chunk in get_llm().stream(qa_prompt):
        content = chunk.content.replace(
            "\n", "  "
        )
        yield f"data: {content}\n\n"
        answer += chunk.content

    yield f"data: {DONE_TAG}\n\n"

    # Wait for summaries to complete and send enhanced source information
    try:
        # Initialize summaries array to maintain order
        summaries = [None] * len(docs)
        
        # Collect results as they complete
        for future in as_completed(summary_futures.keys(), timeout=30):
            try:
                doc_index = summary_futures[future]
                summary = future.result()
                summaries[doc_index] = summary
            except Exception as e:
                current_app.logger.error(f"Summary generation failed for doc {summary_futures[future]}: {e}")
                summaries[summary_futures[future]] = "Summary generation failed"
        
        # Send enhanced source information with summaries
        for i, (doc, summary) in enumerate(zip(docs, summaries)):
            enhanced_source = {
                "name": doc.metadata.get("_source", {}).get("name", "Unknown"),
                "summary": doc.page_content[:100] + "...",
                "page_content": summary if summary else "Summary generation failed",
                "url": doc.metadata.get("_source", {}).get("webUrl", ""),
                "category": doc.metadata.get("_source", {}).get("category", "sharepoint"),
                "confidence": doc.metadata.get("_score", 0),
                "updated_at": doc.metadata.get("_source", {}).get("lastModifiedDateTime", None),
                "loading": False,  # Summary is ready
                "enhanced": True,   # Indicate this is an enhanced version
                "error": summary == "Summary generation failed" if summary else True
            }
            yield f"data: {SOURCE_TAG} {json.dumps(enhanced_source)}\n\n"
            
    except Exception as e:
        current_app.logger.error(f"Summary processing failed: {e}")
        # Send error state for sources
        for doc in docs:
            error_source = {
                "name": doc.metadata.get("_source", {}).get("name", "Unknown"),
                "summary": doc.page_content[:100] + "...",
                "page_content": "Summary generation failed",
                "url": doc.metadata.get("_source", {}).get("webUrl", ""),
                "category": doc.metadata.get("_source", {}).get("category", "sharepoint"),
                "confidence": doc.metadata.get("_score", 0),
                "updated_at": doc.metadata.get("_source", {}).get("lastModifiedDateTime", None),
                "loading": False,
                "error": True
            }
            yield f"data: {SOURCE_TAG} {json.dumps(error_source)}\n\n"
    finally:
        executor.shutdown(wait=False)

    current_app.logger.debug("Answer: %s", answer)

    chat_history.add_user_message(question)
    chat_history.add_ai_message(answer)
