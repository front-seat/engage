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

### URL hierarchy for static site.

_notes to myself_

Available summary style slugs:

- `educated-layperson`
- `high-school`
- `catchy-clickbait`

I'm trying to avoid doing too much work here, so the hierarchy is:

/ --> meta-equiv redirect to /calendar/educated-layperson/

/calendar/<summary-style-slug>/
Shows all upcoming non-canceled meetings in the appropriate style.

/meeting/<id>/<summary-style-slug>/
Shows a full summary of the meeting and headlines for each legislative action
Links to the SCC legistar meeting page

/legislation/<id>/<summary-style-slug>/
Shows a full summary of the legislation + headlines for each affiliated document
Links to the SCC legistar legislation page

/document/<id>/<summary-style-slug>/
Shows a full summary of the document
Links to the original document
hello friend 4
