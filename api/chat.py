from langchain_elasticsearch import ElasticsearchStore, BM25Strategy
from langchain_elasticsearch import ElasticsearchRetriever
from llm_integrations import get_llm, get_llm_with_trace_id, init_openai_config_chat
from elasticsearch_client import (
    elasticsearch_client,
    get_elasticsearch_chat_message_history,
    update_document_summary,
    get_document_summary,
    ensure_summary_field_exists,
)
from langchain_core.documents import Document
from typing import Dict, Any, AsyncGenerator
from flask import stream_with_context, current_app
from jinja2.nativetypes import NativeEnvironment
from templates import prompt
import json
import logging
import os
import asyncio
import threading
import math
from concurrent.futures import ThreadPoolExecutor, as_completed

INDEX = os.getenv("ES_INDEX", "ccc-db")
INDEX_CHAT_HISTORY = os.getenv(
    "ES_INDEX_CHAT_HISTORY", "ccc-db-chat-history"
)
ELSER_MODEL = os.getenv("ELSER_MODEL", ".elser_model_2_linux-x86_64")
SESSION_ID_TAG = "[SESSION_ID]"
SOURCE_TAG = "[SOURCE]"
DONE_TAG = "[DONE]"
TRACE_ID_TAG = "[TRACE_ID]"

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
                    "bool": {
                        "should": [
                            {"exists": {"field": "body"}},
                            {"exists": {"field": "Description"}},
                            {"exists": {"field": "CanvasContent1"}}
                        ],
                        "minimum_should_match": 1
                    }
                }],
                "should": [
                    # Title exact match (highest priority for SharePoint pages)
                    {
                        "match": {
                            "Title": {
                                "query": search_query,
                                "boost": 3.0
                            }
                        }
                    },
                    # Phrase search for better relevance
                    {
                        "match_phrase": {
                            "body": {
                                "query": search_query,
                                "boost": 3.0,
                                "slop": 1
                            }
                        }
                    },
                    # Regular text search for individual words
                    {
                        "match": {
                            "body": {
                                "query": search_query,
                                "boost": 1.0,
                                "minimum_should_match": "2<75%"
                            }
                        }
                    },
                    # Stem search for better matching
                    {
                        "match": {
                            "body.stem": {
                                "query": search_query,
                                "boost": 1.5,
                                "minimum_should_match": "2<75%"
                            }
                        }
                    },
                    # Summary field (AI-generated summaries when available)
                    {
                        "match": {
                            "summary": {
                                "query": search_query,
                                "boost": 3.0
                            }
                        }
                    },
                    # Document name search (file names are very relevant)
                    {
                        "match": {
                            "name": {
                                "query": search_query,
                                "boost": 2.5,
                                "fuzziness": "AUTO"
                            }
                        }
                    },
                    # Name stem search for better matching
                    {
                        "match": {
                            "name.stem": {
                                "query": search_query,
                                "boost": 2.0
                            }
                        }
                    },
                    # Path search
                    {
                        "match": {
                            "parentReference.path": {
                                "query": search_query,
                                "boost": 1.5
                            }
                        }
                    },
                    # Description field search
                    {
                        "match": {
                            "Description": {
                                "query": search_query,
                                "boost": 2.0,
                                "minimum_should_match": "2<75%"
                            }
                        }
                    },
                    # Description phrase search for better relevance
                    {
                        "match_phrase": {
                            "Description": {
                                "query": search_query,
                                "boost": 2.5,
                                "slop": 1
                            }
                        }
                    },
                    # CanvasContent1 field search
                    {
                        "match": {
                            "CanvasContent1": {
                                "query": search_query,
                                "boost": 1.0,
                                "minimum_should_match": "2<75%"
                            }
                        }
                    },
                    # CanvasContent1 phrase search
                    {
                        "match_phrase": {
                            "CanvasContent1": {
                                "query": search_query,
                                "boost": 2.0,
                                "slop": 1
                            }
                        }
                    }
                ],
                "minimum_should_match": 1
            }
        },
        "size": 5,

        "rescore": {
            "window_size": 20,
            "query": {
                "rescore_query": {
                    "bool": {
                        "should": [
                            # Exact phrase matching - critical for legal terms
                            {
                                "match_phrase": {
                                    "body": {
                                        "query": search_query,
                                        "boost": 3.0,
                                        "slop": 2
                                    }
                                }
                            },
                            # Phrase match in summary
                            {
                                "match_phrase": {
                                    "summary": {
                                        "query": search_query,
                                        "boost": 2.5
                                    }
                                }
                            },
                            # Phrase match in Description
                            {
                                "match_phrase": {
                                    "Description": {
                                        "query": search_query,
                                        "boost": 2.5
                                    }
                                }
                            },
                            # Phrase match in CanvasContent1
                            {
                                "match_phrase": {
                                    "CanvasContent1": {
                                        "query": search_query,
                                        "boost": 2.0
                                    }
                                }
                            },
                            # Multi-match with cross_fields (including new fields)
                            {
                                "multi_match": {
                                    "query": search_query,
                                    "type": "cross_fields",
                                    "fields": [
                                        "name^3",
                                        "name.stem^2.5",
                                        "summary^3",
                                        "summary.stem^2.5",
                                        "body^1",
                                        "body.stem^1.5",
                                        "parentReference.path^1.5",
                                        "Description^2",
                                        "CanvasContent1^1"
                                    ],
                                    "operator": "or",
                                    "minimum_should_match": "75%"
                                }
                            },
                            # Boost recent documents
                            {
                                "range": {
                                    "lastModifiedDateTime": {
                                        "gte": "now-6M",
                                        "boost": 1.2
                                    }
                                }
                            }
                        ]
                    }
                },
                "query_weight": 0.3,
                "rescore_query_weight": 0.7
            }
        }
    }

async def generate_doc_summary(page_content: str, trace_id: str) -> str:
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
        },
        trace_id=trace_id,
        span_name="Document Summary"
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
    # Ensure summary field exists in the index mapping
    ensure_summary_field_exists(INDEX)
    
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

    # Custom search function to handle multiple content fields
    def custom_search(query: str):
        search_body = bm25_query(query)
        search_body["_source"] = True
        
        try:
            response = elasticsearch_client.search(
                index=INDEX,
                body=search_body
            )
            
            docs = []
            seen_ids = set()
            for hit in response["hits"]["hits"]:
                doc_id = hit["_id"]
                
                # Skip if we've already processed this document
                if doc_id in seen_ids:
                    continue
                seen_ids.add(doc_id)
                
                source = hit["_source"]
                
                # Extract content from the first available field (simplified approach)
                page_content = (
                    source.get("body") or 
                    source.get("CanvasContent1") or 
                    source.get("Description") or 
                    source.get("name", "No content available")
                )
                
                doc = Document(
                    page_content=page_content,
                    metadata={
                        "_score": hit["_score"],
                        "_id": hit["_id"],
                        "_source": source,
                        "name": source.get("name", "Unknown Document")
                    }
                )
                docs.append(doc)
            
            return docs
        except Exception as e:
            current_app.logger.error(f"Custom search failed: {e}")
            raise e

    try:
        docs = custom_search(condensed_question)
        current_app.logger.debug("Retrieved %s documents", len(docs))
    except Exception as e:
        current_app.logger.error(f"Elasticsearch search failed: {e}")
        # Send error message to frontend
        yield f"data: I'm sorry, there was an issue searching the documents. Please try again in a moment.\n\n"
        yield f"data: {DONE_TAG}\n\n"
        return

    # Calculate improved confidence scores based on absolute relevance
    def calculate_confidence_scores(docs):
        if not docs:
            return []
        
        # Define relevance thresholds based on typical Elasticsearch scores
        HIGH_RELEVANCE_THRESHOLD = 10.0   # Very relevant
        MED_RELEVANCE_THRESHOLD = 5.0     # Somewhat relevant  
        LOW_RELEVANCE_THRESHOLD = 2.0     # Minimally relevant
        
        scores = [doc.metadata.get("_score", 0) for doc in docs]
        max_score = scores[0] if scores else 1
        
        confidences = []
        for i, doc in enumerate(docs):
            raw_score = doc.metadata.get("_score", 0)
            
            # Base confidence on absolute score first
            if raw_score >= HIGH_RELEVANCE_THRESHOLD:
                base_confidence = 0.8  # 80-100% range for highly relevant
                confidence_range = 20
            elif raw_score >= MED_RELEVANCE_THRESHOLD:
                base_confidence = 0.5  # 50-80% range for moderately relevant
                confidence_range = 30
            elif raw_score >= LOW_RELEVANCE_THRESHOLD:
                base_confidence = 0.3  # 30-50% range for minimally relevant
                confidence_range = 20
            else:
                base_confidence = 0.1  # 10-30% range for very low relevance
                confidence_range = 20
            
            # Apply relative scoring within the determined range
            if max_score > 0 and raw_score > 0:
                relative_score = (raw_score / max_score) ** 0.5
            else:
                relative_score = 0
            
            # Position decay (less aggressive for already lower confidence)
            position_factor = 1.0 - (i * 0.08)  # Reduced from 0.1 to 0.08
            
            # Final confidence combines absolute relevance with relative positioning
            confidence = int(base_confidence * 100 + 
                           relative_score * position_factor * confidence_range)
            
            # Ensure confidence stays within reasonable bounds
            confidences.append(min(100, max(10, confidence)))
        
        return confidences
    
    confidence_scores = calculate_confidence_scores(docs)
    
    # Log retrieved documents for debugging
    for i, doc in enumerate(docs):
        doc_name = doc.metadata.get("_source", {}).get("name", "Unknown")
        current_app.logger.debug(f'Retrieved document passage from: {doc_name}')

    # Get LLM with trace ID for feedback tracking
    llm_with_trace, trace_id = get_llm_with_trace_id()
    current_app.logger.debug(f"Generated trace ID: {trace_id}")
    
    # Check for existing summaries and prepare summary generation
    def generate_single_summary(doc, doc_index, trace_id):
        """Wrapper function to check for existing summary or generate new one"""
        import asyncio
        import logging
        
        # Set up logging for the thread (can't use current_app.logger in threads)
        logger = logging.getLogger(__name__)
        
        # First check if summary already exists
        doc_id = doc.metadata.get("_id")
        if doc_id:
            existing_summary = get_document_summary(INDEX, doc_id)
            if existing_summary:
                logger.debug(f"Using existing summary for document {doc_id}")
                return existing_summary
        
        # Generate new summary if none exists
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            # Run the async function
            result = loop.run_until_complete(generate_doc_summary(doc.page_content, trace_id))
            
            # Save the summary back to Elasticsearch if we have a doc_id
            if doc_id and result and result != "Summary generation failed":
                success = update_document_summary(INDEX, doc_id, result)
                if success:
                    logger.debug(f"Saved summary for document {doc_id}")
                else:
                    logger.warning(f"Failed to save summary for document {doc_id}")
            
            return result
        except Exception as e:
            logger.error(f"Summary generation error: {e}")
            return "Summary generation failed"
        finally:
            # Proper async cleanup to prevent "Event loop is closed" errors
            try:
                # Get all remaining tasks
                pending_tasks = asyncio.all_tasks(loop)
                
                if pending_tasks:
                    # Cancel all pending tasks
                    for task in pending_tasks:
                        if not task.done():
                            task.cancel()
                    
                    # Wait for cancellations to complete with timeout
                    try:
                        loop.run_until_complete(
                            asyncio.wait_for(
                                asyncio.gather(*pending_tasks, return_exceptions=True),
                                timeout=2.0
                            )
                        )
                    except asyncio.TimeoutError:
                        logger.debug("Timeout waiting for task cancellation")
                    except Exception:
                        pass  # Ignore cleanup errors
                
                # Additional cleanup for httpx connections
                try:
                    # Give the loop one more chance to process any final cleanup
                    loop.run_until_complete(asyncio.sleep(0.1))
                except Exception:
                    pass
                    
            except Exception as cleanup_error:
                logger.debug(f"Loop cleanup warning (non-critical): {cleanup_error}")
            finally:
                # Close the loop
                if not loop.is_closed():
                    loop.close()

    # Start summary generation in parallel threads
    executor = ThreadPoolExecutor(max_workers=min(len(docs), 5))
    summary_futures = {
        executor.submit(generate_single_summary, doc, i, trace_id): i 
        for i, doc in enumerate(docs)
    }

    qa_prompt = rags_prompt_template.render(
        question=question,
        docs=docs,
        chat_history=chat_history.messages,
    )
    
    # Send trace ID for feedback tracking
    yield f"data: {TRACE_ID_TAG} {trace_id}\n\n"

    # Stream the answer while summaries are being generated
    answer = ""
    for chunk in llm_with_trace.stream(qa_prompt):
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
        current_app.logger.debug(f"Sending {len(docs)} enhanced source results")
        for i, (doc, summary) in enumerate(zip(docs, summaries)):
            # Get proper document name (prefer Title for SharePoint pages, then name)
            source_data = doc.metadata.get("_source", {})
            doc_name = (
                source_data.get("Title") or 
                source_data.get("name") or 
                "Unknown Document"
            )
            doc_id = doc.metadata.get("_id")
            doc_url = source_data.get("webUrl", "")
            

            
            enhanced_source = {
                "name": doc_name,
                "summary": summary if summary else "Summary generation failed",  # AI summary
                "page_content": summary if summary else "Summary generation failed",
                "url": doc_url,
                "category": source_data.get("category", "sharepoint"),
                "confidence": confidence_scores[i] if i < len(confidence_scores) else 30,
                "updated_at": source_data.get("lastModifiedDateTime", None),
                "loading": False,  # Summary is ready
                "enhanced": True,   # Indicate this is an enhanced version
                "error": summary == "Summary generation failed" if summary else True
            }

            yield f"data: {SOURCE_TAG} {json.dumps(enhanced_source)}\n\n"
            
    except Exception as e:
        current_app.logger.error(f"Summary processing failed: {e}")
        # Send error state for sources
        for i, doc in enumerate(docs):
            error_source = {
                "name": doc.metadata.get("_source", {}).get("name", "Unknown"),
                "summary": doc.page_content[:100] + "...",
                "page_content": "Summary generation failed",
                "url": doc.metadata.get("_source", {}).get("webUrl", ""),
                "category": doc.metadata.get("_source", {}).get("category", "sharepoint"),
                "confidence": confidence_scores[i] if i < len(confidence_scores) else 30,
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
