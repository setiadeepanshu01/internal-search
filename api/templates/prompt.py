rag_template = """Use the following context and chat history to answer the user's question.
Each passage has a NAME which is the title of the document. After your answer, leave a blank line and then give the source name of the context you answered from. Put them in a comma separated list, prefixed with SOURCES:.

User question: {{ question }}

Example:

Question: What is the meaning of life?
Response:
The meaning of life is 42.

SOURCES: Hitchhiker's Guide to the Galaxy

----

{% for doc in docs -%}
---
NAME: {{ doc.metadata.name }}
PASSAGE:
{{ doc.page_content }}
---

{% endfor -%}
----
Chat history:
{% for dialogue_turn in chat_history -%}
{% if dialogue_turn.type == 'human' %}Question: {{ dialogue_turn.content }}{% elif dialogue_turn.type == 'ai' %}Response: {{ dialogue_turn.content }}{% endif %}
{% endfor -%}

Question: {{ question }}
Response:
"""

condense_question_template = """
Given the following conversation and a follow up question, rephrase the follow up question to be a standalone question, in its original language.

Chat history:
{% for dialogue_turn in chat_history -%}
{% if dialogue_turn.type == 'human' %}Question: {{ dialogue_turn.content }}{% elif dialogue_turn.type == 'ai' %}Response: {{ dialogue_turn.content }}{% endif %}
{% endfor -%}
Follow Up Question: {{ question }}
Standalone question:

"""

summary_template = """Create a concise and dense summary of the following document text in 150 words:

{{ page_content }}

Summary:
"""