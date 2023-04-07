# City Council Engage-o-tron™

This repository currently contains early bits of disorganized research code to:

- Download documents related to the Seattle city council (agendas, minutes, transcripts) and grab their text
- Embed the documents and store it in a vector database (pgvector, OpenAI)
- Summarize document content (zero-shot, using LLMs with LangChain+map-reduce)
- Allow querying over the documents

FUTURE:

- _Optional_. Use spaCY, NLTK, or BERT to perform extractive summarization. Consider how extractive summaries can be fed as input to LLMs for final abstracting summarization.

As of this writing, everything interesting happens on the command-line.

Because I'm using the Django admin interface to poke at the database, there are the earliest trappings of a web project too.

Bottom line: this is a (small-ish) ball of yarn for now; I'll tease things apart later, once we have a little more clarity about what we're building, and when/if it matters.
