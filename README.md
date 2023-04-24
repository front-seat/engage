# City Council Engage-o-tron™

This repository currently contains early bits of disorganized research code to:

- Crawl the Seattle city council Legistar website, starting with the event calendar, and index its content.
- Extract text from Seattle city council PDF documents
- Generate LLM summaries for individual ordinances, appointment packets, etc.
- Generate unified summaries for legislative actions and future council meetings
- Build embeddings via [FAISS](https://faiss.ai/)
- Build static sites containing these summaries and links to go deeper

We use the ["baked data" pattern](https://simonwillison.net/2021/Jul/28/baked-data/) for this project. Namely, `data/db.sqlite3` contains our current index; when we update our index (say, by crawling the Legistar website again), we also update this file _and check it back in_.

We run new crawls, generate static site content, and update GitHub Pages (our deployment mechanism) entirely via GitHub actions.

We also generate static content and make it available to GitHub pages.

As of this writing, everything interesting happens on the command-line. Documentation for our command line exposure is forthcoming.
