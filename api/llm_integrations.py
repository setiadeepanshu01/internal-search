from langchain_openai import ChatOpenAI
from portkey_ai import createHeaders, PORTKEY_GATEWAY_URL
import os
import uuid

LLM_TYPE = os.getenv("LLM_TYPE", "openai")

config = {
    "cache": {
		"mode": "semantic",
	},
    "retry" : {
		"attempts": 3
	},
}

portkey_headers = createHeaders(api_key= os.getenv("PORTKEY_API_KEY"),
                                provider="openai",
                                metadata={"_user": "mx2-ccc"},
                                config=config
                                )

def init_openai_chat(temperature):
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    return ChatOpenAI(
        openai_api_key=OPENAI_API_KEY, streaming=True, temperature=temperature, model='gpt-4.1',
        base_url=PORTKEY_GATEWAY_URL, default_headers=portkey_headers, stream_usage=True
    )

def init_openai_config_chat(temperature):
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    return ChatOpenAI(
        openai_api_key=OPENAI_API_KEY, streaming=False, temperature=temperature, model='gpt-4.1',
        base_url=PORTKEY_GATEWAY_URL, default_headers=portkey_headers
    )

MAP_LLM_TYPE_TO_CHAT_MODEL = {
    "openai": init_openai_chat,
}


def get_llm(temperature=0):
    if not LLM_TYPE in MAP_LLM_TYPE_TO_CHAT_MODEL:
        raise Exception(
            "LLM type not found. Please set LLM_TYPE to one of: "
            + ", ".join(MAP_LLM_TYPE_TO_CHAT_MODEL.keys())
            + "."
        )

    return MAP_LLM_TYPE_TO_CHAT_MODEL[LLM_TYPE](temperature=temperature)

def get_llm_with_trace_id(temperature=0):
    """Get LLM with custom trace ID for feedback tracking"""
    # Generate our own trace ID
    trace_id = str(uuid.uuid4())
    
    # Create headers with trace_id included
    headers_with_trace = createHeaders(
        api_key=os.getenv("PORTKEY_API_KEY"),
        provider="openai",
        metadata={"_user": "mx2-ccc"},
        config=config,
        trace_id=trace_id,
        span_name="LLM Generation",
    )
    
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    llm = ChatOpenAI(
        openai_api_key=OPENAI_API_KEY,
        streaming=True,
        temperature=temperature,
        model='gpt-4.1',
        base_url=PORTKEY_GATEWAY_URL,
        default_headers=headers_with_trace,
        stream_usage=True
    )
    
    return llm, trace_id
