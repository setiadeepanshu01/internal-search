import os
from elasticsearch import Elasticsearch
from openai import OpenAI
from dotenv import load_dotenv
load_dotenv()

# Initialize Elasticsearch client
es_client = Elasticsearch(
    cloud_id=os.environ["ELASTIC_CLOUD_ID"],
    api_key=os.environ["ELASTIC_API_KEY"]
)

# Initialize OpenAI client
openai_client = OpenAI(
    api_key=os.environ["OPENAI_API_KEY"],
)

def get_elasticsearch_results(query):
    # Define the Elasticsearch query with fields based on available schema
    es_query = {
        "query": {
            "multi_match": {
                "query": query,
                "fields": [
                    "body",
                    "displayName",
                    "description"
                ]
            }
        },
        "size": 1
    }
    
    # Execute the search query
    result = es_client.search(index="ccc-db", body=es_query)
    return result["hits"]["hits"]

def create_openai_prompt(results):
    context = ""
    for hit in results:
        source_fields = ["body", "displayName", "description"]
        for field in source_fields:
            if field in hit["_source"]:
                context += f"{hit['_source'][field]}\n"
    
    prompt = f"""
  Instructions:
  
  - You are an assistant for question-answering tasks.
  - Answer questions truthfully and factually using only the context presented.
  - If you don't know the answer, just say that you don't know, don't make up an answer.
  - Use markdown format for code examples.
  - You are correct, factual, precise, and reliable.
  
  Context:
  {context}
  
  """
    return prompt

def generate_openai_completion(user_prompt, question):
    # Generate response using OpenAI's GPT model
    response = openai_client.chat.completions.create(
        model="gpt-4.1",
        messages=[
            {"role": "system", "content": user_prompt},
            {"role": "user", "content": question},
        ]
    )
    return response.choices[0].message.content

if __name__ == "__main__":
    # question = "What is in CV OF SHAUN MARIE SEVER PO Like?"
    # question = "What Courtney Future Cost Projections look like?"
    question = "Work at Home Troubleshooting"
    elasticsearch_results = get_elasticsearch_results(question)
    # Print Elasticsearch results for debugging
    # print("Elasticsearch Results:")
    # for result in elasticsearch_results:
    #     print(result)
    
    context_prompt = create_openai_prompt(elasticsearch_results)
    openai_completion = generate_openai_completion(context_prompt, question)
    print(openai_completion)