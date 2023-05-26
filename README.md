# City Council Engage-o-tron™

This the code that generates [scc.frontseat.org](https://scc.frontseat.org/), a static site that contains summaries of upcoming meetings, agenda items, and legislative documents for the Seattle City Council.

The SCC publishes documents for upcoming meetings at [seattle.legistar.com](https://seattle.legistar.com/Calendar.aspx). These documents are often long and complex, and it can be difficult to understand what's going on. The Engage-o-tron™ is an attempt to make this information more accessible.

## How it works

This repository contains code to generate a static website site that is deployed to [GitHub Pages](https://pages.github.com/).

We use [GitHub Actions](https://github.com/features/actions) to regularly re-crawl the SCC Legistar website, extract text from PDFs, generate summaries of upcoming meetings, and deploy the static site.

In order to make this all work, a record of previously crawled data, extracted text, and summarizations is stored in a SQLite database that is checked into this repository. This follows [Simon Willison's "baked data" pattern](https://simonwillison.net/2021/Jul/28/baked-data/) and keeps our devops both simple and zero cost. The only expense we have, at the moment, is invoking ChatGPT to generate summaries; we're currently _well_ under the GitHub Actions monthly minutes quota for the free tier.

### Some more details

The primary GitHub action definition is [crawl-summarize-deploy.yml](.github/workflows/crawl-summarize-deploy.yml), which runs a couple times a day. It invokes our crawler; extracts text from newly discovered PDFs and Word files; generates summaries; updates the SQLite database; and generates + deploys the static site.

The code is implemented as a [Django](https://www.djangoproject.com/) project. We use Django's ORM to interact with the SQLite database. We use Django's view and template system to generate the HTML content. We use [Django Distill](https://github.com/meeb/django-distill) to generate a _static_ site from our Django views. (It's nice to have a flexible web framework!)

We have a collection of command-line tools implemented as Django management commands:

- `manage.py legistar crawl-calendar` crawls the Legistar calendar page, follows links for meeting and legislation sub-pages, grabs all document attachments, and updates the database.

- `manage.py documents ...` provides tools to extract and summarize text from one or multiple documents.

- `manage.py legistar summarize ...` provides tools to summarize one or multiple legislative actions or meetings.

- `manage.py distill-local ...` builds the static site into the `dist` directory.

### Summarizing documents

For every `Document`, `Legislation` (aka legislative agenda item in a meeting), and `Meeting`, we generate a summary record that includes:

- A short newspaper-style `headline`
- A longer `body` summary
- A small amount of bookkeeping/debugging data so we can better evaluate our summaries

The base model for all summarizations is found in `server/lib/summary_model.py`.

Most of SCC's documents are large PDFs or Word files. They very rarely fit into the token context window of the LLMs that we use to generate summaries.As a result, we segment documents into smaller chunks and summarize each chunk individually. We then concatenate the summaries together to form a single summary for the entire document. (If the first round of summaries itself does not fit into the token context window, we repeat the process.)

Right now, text extraction from PDFs uses [pdfplumber](https://github.com/jsvine/pdfplumber). This works _acceptably_ well for a first cut, but it fails to extract text from bitmaps found in documents. (Thankfully, most but not all SCC PDFs contain actual text, not scans.) Something like [Google Cloud Vision API](https://cloud.google.com/vision/docs/pdf) would likely provide _vastly_ better extraction results.

Currently we're pretty stupid about how we split our documents into chunks. We look for obvious boundaries; if those don't provide small enough chunks, we look for newlines and sentence ends. We should be _much_ smarter here: most SCC documents have obvious hierarchical structure, and we probably _should_ split them into chunks based on that structure in the future.

The system has a notion of a `style` for a summary. A "style" encompasses a number of things:

- The prompts used to generate summaries.
- The specific LLM used to generate summaries, and its parameters.

When I first built the site, I had close to a dozen styles, experimenting with wildly different prompts, and with different LLMs, including ChatGPT-3.5-Turbo, Vicuna 13B, and RedPajama 3B. After a lot of experimentation, I boiled things down to just a single style, called `concise`, which uses `ChatGPT-3.5-Turbo` and attempts to generate a neutral-voice summary that is as short as possible while still being informative.

One last point about summarization: I decided to use [LangChain](https://python.langchain.com/en/latest/index.html) since I'd never used it before. Alas, I don't think I'll use it again. At is heart, LangChain contains a set of tools for flexibly manipulating LLM prompts. It's a fine idea, but the actual implementation leaves _much_ to be desired. LangChain's primitives _feel_ like they should be composable but often aren't; the library suffers from type erasure, making it difficult to know what parameters are available for a given chain; the documentation is poor; there are key missing features &mdash; like counting _actual tokens used_ &mdash; that make it of limited use. I'm glad I tried it, though!

## Development

This is a Python 3.11 project, using Django 4.2, LangChain 0.0.1xx, and Django Distill 3.

We use [Poetry](https://python-poetry.org/) to manage dependencies.

To get started, create a virtual environment and install the dependencies:

```
poetry install
```

Then, copy the `.env-sample` file to a `.env` file and make any changes you'd like. (You can leave it as-is for now.)

Next, make sure to run the database migrations:

```
poetry run python manage.py migrate
```

Great; you should have an empty `data/db.sqlite3` file now and be ready to go.

To crawl the Seattle Legistar website, run:

```
poetry run python manage.py legistar crawl-calendar --start today
```

Next, extract and summarize the crawled documents, legislative agenda items, and meetings:

```
poetry run python manage.py documents extract all
poetry run python manage.py documents summarize all
poetry run python manage.py legistar summarize all-legislation
poetry run python manage.py legistar summarize all-meetings
```

From here, you can run the Django development server to see what you've got:

```
poetry run python manage.py runserver
```

Or you can build the static site into `./dist`:

```
poetry run python manage.py distill-local --force --collectstatic
```

All of the above commands are run by the GitHub actions workflow. For local development, there's also a convenient `./scripts/update-all.sh` script that runs all of the above commands in sequence.

### Project structure

This is a typical Django app, albeit with an atypical build-to-static-site deployment step.

Of interest:

- `server.lib.*` contains utility code used throughout
- `server.documents.*` contains code for storing our `Document` and `DocumentSummary` state. See `server/documents/models.py` for the database model definitions, `summarize.py` for the LangChain + OpenAI code to chunk and summarize individual documents, `extract.py` for our current (poor) PDF text extraction code, and `management/commands/documents.py` for the Django management commands that run the extraction and summarization.
- `server.legistar.*` contains code for storing meetings (`Meeting`) and legislative agenda items (`Legislation`), along with their summaries (`MeetingSummary`, `LegislationSummary`), code for crawling `seattle.legistar.com` (see `server/legistar/lib/crawl.py`), code for summarizing meetings and legislations (see `server/legistar/summarize/*.py`), and code to generate the static site (see `server/legistar/urls.py` and `server/legistar/views.py`).
