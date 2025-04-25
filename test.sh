
# Root Endpoint (/) - Remains GET as it doesn't take a body
curl http://localhost:8888/

# Scrape URL Endpoint (/scrape-url)
curl -X POST http://localhost:8888/scrape-url \
-H "Content-Type: application/json" \
-d '{
        "base-html": "http://example.com/exmple.html",
        "perm-url": "http://example.com"
    }'

# Scrape Page Endpoint (/scrape-page)
curl -X POST http://localhost:8888/scrape-page \
-H "Content-Type: application/json" \
-d '{
        "url": "http://example.com/some-web-page",
        "scrape-images": true
    }'

# Scrape PDF Endpoint (/scrape-pdf)
curl -X POST http://localhost:8888/scrape-pdf \
-H "Content-Type: application/json" \
-d '{
        "url": "http://example.com/path/to/your/document.pdf",
        "scrape-image": false
    }'

# Ask Endpoint (/ask)
curl -X POST https://-01j7860s1h540pyys2dz7kcae1fbk9.cloudspaces.litng.ai/ask \
-H "Content-Type: application/json" \
-d '{
        "query": "What is the main topic of the ingested documents?",
        "session_id": "user123_chat789"
    }'

# Update Image Prompt Endpoint (/update-image-prompt)
curl -X POST http://localhost:8888/update-image-prompt \
-H "Content-Type: application/json" \
-d '{
        "prompt": "Please provide a detailed description of the following image: {}",
        "session_id" : "5b58b140-5226-4d9e-ba77-58ac27db26d3"
    }'