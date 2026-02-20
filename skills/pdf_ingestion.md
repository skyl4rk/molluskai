# PDF Ingestion

When the user provides a local file path ending in `.pdf`, extract and store its contents by replying with only:

    ingest pdf: <path>

where `<path>` is exactly the path the user provided.

When a PDF is sent via Telegram as an attachment, it is downloaded and ingested automatically — no extra step needed.

After ingestion, confirm briefly how many text chunks were stored and offer to search or summarise the content.
