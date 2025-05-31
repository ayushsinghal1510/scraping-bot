
# Root Endpoint (/) - Remains GET as it doesn't take a body
curl https://8888-01jvz3v9phphmvq0twsmakz8zy.cloudspaces.litng.ai/

# Scrape URL Endpoint (/scrape-url)
curl -X POST https://8888-01jvz3v9phphmvq0twsmakz8zy.cloudspaces.litng.ai/scrape-url \
-H "Content-Type: application/json" \
-d '{
        "url": "https://www.nrsc.gov.in/Knowledge_EBooks/",
    }'

# Scrape Page Endpoint (/scrape-page)
curl -X POST https://8888-01jvz3v9phphmvq0twsmakz8zy.cloudspaces.litng.ai/scrape-page \
-H "Content-Type: application/json" \
-d '{
        "url": "https://voicexp.ai/",
        "scrape-images": true
    }'

# Scrape PDF Endpoint (/scrape-pdf)
curl -X POST https://8888-01jvz3v9phphmvq0twsmakz8zy.cloudspaces.litng.ai/scrape-pdf \
-H "Content-Type: application/json" \
-d '{
        "url": "http://example.com/path/to/your/document.pdf",
        "scrape-image": false
    }'

curl -X POST "https://8888-01jvz3v9phphmvq0twsmakz8zy.cloudspaces.litng.ai/scrape-pdf-file" \
    -H "Content-Type: multipart/form-data" \
    -F "file=@/path/to/your/document.pdf"


# Ask Endpoint (/ask)
curl -X POST https://-01j7860s1h540pyys2dz7kcae1fbk9.cloudspaces.litng.ai/ask \
-H "Content-Type: application/json" \
-d '{
        "query": "What is the main topic of the ingested documents?",
        "session_id": "user123_chat789"
    }'

curl -X GET "https://8888-01jvz3v9phphmvq0twsmakz8zy.cloudspaces.litng.ai/number-of-queries"

curl -X GET "https://8888-01jvz3v9phphmvq0twsmakz8zy.cloudspaces.litng.ai/sentiment"

curl -X GET "https://8888-01jvz3v9phphmvq0twsmakz8zy.cloudspaces.litng.ai/token-count"

curl -X GET "https://8888-01jvz3v9phphmvq0twsmakz8zy.cloudspaces.litng.ai/category"