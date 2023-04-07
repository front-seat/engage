# City Council Engage-o-tron™

This repository currently contains the earliest bits of disorganized research code to:

1. Download documents related to the Seattle city council (agendas, minutes, transcripts) and grab their text
2. Embed the documents and store it in a vector database (pgvector, OpenAI)
3. Summarize document content (using LC + map-reduce)
4. Allow querying over the documents

As of this writing, everything lives on the command-line. Because I'm using the Django admin interface to poke at the database, there are the earliest trappings of a web project too. It's a ball of yarn for now; I'll tease things apart later, when/if it matters.
