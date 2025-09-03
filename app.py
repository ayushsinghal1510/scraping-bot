import uvicorn
import datetime
import json
from dotenv import load_dotenv
from fastapi import FastAPI, Request, HTTPException, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware

# Assuming your embedding model is a SentenceTransformer model
# which has an `encode` method.
from sentence_transformers import SentenceTransformer

# Assuming your clients are typed for clarity. Replace with actual types if available.
from groq import Groq
from pymilvus import MilvusClient
from redis import Redis
from transformers import Pipeline, PreTrainedTokenizer

from scripts.scrapper.services import get_pdf_links
from scripts.loader.loader import (
    load_embedding_model,
    load_sentiment_pipeline,
    load_tokenizer,
    load_milvus_client,
    load_redis_client,
    load_gemini_client,
    load_groq_client
)
from scripts.routers.routers import (
    scrape_page_route,
    scrape_pdf_route,
    scrape_pdf__file_route,
    # ask_route is now implemented in-app, so it's removed
    get_sentiment_route,
    get_token_count_route,
    get_category_route
)

load_dotenv()

# --- RAG Pipeline Helper Functions ---

async def rewrite_query_with_groq(
    groq_client: Groq, 
    session_id: str, 
    query: str, 
    redis_client: Redis
) -> str:
    history = redis_client.lrange(f"history:{session_id}", 0, -1)
    if not history:
        return query

    # Decode history from bytes if necessary
    decoded_history = [h.decode('utf-8') if isinstance(h, bytes) else h for h in history]
    context_str = "\n".join(decoded_history[-5:]) # Use last 5 interactions

    prompt = f"""
        Based on the following conversation history, rewrite the user's latest query to be a standalone question. If the query is already standalone, return it as is.
    
        Conversation History:
        {context_str}
    
        Latest User Query: {query}
    
        Rewritten Query:
    """

    try:
        chat_completion = groq_client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama3-8b-8192",
            temperature=0.0,
            max_tokens=100,
            stop=["\n"]
        )
        rewritten_query = chat_completion.choices[0].message.content.strip()
        return rewritten_query if rewritten_query else query
    except Exception as e:
        print(f"Error during query rewriting: {e}")
        return query

def search_milvus(
    milvus_client: MilvusClient,
    embedding_model: SentenceTransformer,
    collection_name: str,
    query: str,
    top_k: int = 10
) -> list:
    """Searches for relevant documents in Milvus."""
    query_embedding = embedding_model.encode(query, convert_to_tensor=False).tolist()
    
    # Assuming your Milvus collection has a field named 'embedding'
    search_params = {"metric_type": "COSINE", "params": {"nprobe": 10}}
    
    # Using MilvusClient's search method
    results = milvus_client.search(
        collection_name=collection_name,
        data=[query_embedding],
        # anns_field="embedding",
        search_params=search_params,
        limit=top_k,
        output_fields=["url", "title", "content", "content_date", "domain"] # Adjust fields as per your schema
    )
    
    # Process results into a list of dictionaries
    hits = []
    if results:
        for result in results[0]:
            hit = result.get('entity', {})
            hit['score'] = result.get('distance', 0.0)
            hits.append(hit)
    return hits

def check_freshness(doc: dict) -> bool:
    """Checks if a document is less than 15 days old."""
    content_date_str = doc.get("content_date")
    if not content_date_str:
        return False
    try:
        content_date = datetime.datetime.fromisoformat(content_date_str.replace("Z", "+00:00"))
        age_days = (datetime.datetime.now(datetime.timezone.utc) - content_date).days
        return age_days <= 15
    except (ValueError, TypeError):
        return False

def curate_results(hits: list) -> list:
    """Deduplicates results by URL, preferring the most recent."""
    curated = {}
    for doc in hits:
        url = doc.get("url", "").rstrip("/")
        if not url:
            continue
            
        if url not in curated or doc.get("content_date", "") > curated[url].get("content_date", ""):
            curated[url] = doc
            
    return sorted(list(curated.values()), key=lambda x: x.get("score", 0.0), reverse=True)[:5]

async def generate_answer_with_groq(groq_client: Groq, query: str, context_docs: list) -> str:
    """Generates an answer using Groq based on the provided context."""
    if not context_docs:
        return "I could not find any relevant information in my knowledge base to answer your question."

    context_text = "\n\n".join(
        [f"Source URL: {doc.get('url', 'N/A')}\nContent Date: {doc.get('content_date', 'N/A')}\nContent: {doc.get('content', '')}" for doc in context_docs]
    )

    prompt = f"""You are an expert AI assistant. Answer the user's question based *only* on the provided context.
Your answer must be accurate, detailed, and directly supported by the information in the sources.
At the end of your answer, you MUST include a "Citations" section listing the URLs of the sources you used.

Context:
---
{context_text}
---

User Question: {query}

Answer:"""

    try:
        chat_completion = groq_client.chat.completions.create(
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": prompt}
            ],
            model="llama3-70b-8192",
            temperature=0.2,
            max_tokens=1500,
        )
        return chat_completion.choices[0].message.content.strip()
    except Exception as e:
        print(f"Error during answer generation: {e}")
        return "I'm sorry, but I encountered an error while generating a response."

# --- Client and Model Loading ---

sentiment_pipeline = load_sentiment_pipeline()
tokenizer = load_tokenizer()
milvus_client = load_milvus_client() # Expects MilvusClient instance
chat_redis_client = load_redis_client(0)
db_redis_client = load_redis_client(1)
url_redis_client = load_redis_client(2)
embedding_model = load_embedding_model()
gemini_client = load_gemini_client()
groq_client = load_groq_client()

# --- FastAPI App Initialization ---

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

# --- API Endpoints ---

@app.get('/')
async def read_root():
    return {'Hello': 'World'}

@app.post('/scrape-url')
async def scrape_url(request: Request) -> dict:
    request_data = await request.json()
    url: str = request_data.get('url', '')
    if not url:
        raise HTTPException(status_code=400, detail='URL was not supplied')
    
    pdf_links, all_links = await get_pdf_links(url)
    return {'pdf_links': pdf_links, 'all_links': all_links}

@app.post('/scrape-page')
async def scrape_page(request: Request) -> None | dict:
    request_data = await request.json()
    url = request_data.get('url')
    scrape_images = request_data.get('scrape-images')

    if not url or scrape_images not in [True, False]:
        raise HTTPException(status_code=400, detail='Correct Params was not supplied')

    status: None | str = await scrape_page_route(
        url, embedding_model, milvus_client, gemini_client, url_redis_client, scrape_images
    )
    if isinstance(status, str):
        raise HTTPException(status_code=404, detail=status)

@app.post('/scrape-pdf-file')
async def scrape_pdf_file(file: UploadFile = File(...)) -> None:
    contents = await file.read()
    filename = str(file.filename)
    if not contents:
        raise HTTPException(status_code=400, detail='Correct Params was not supplied')
        
    await scrape_pdf__file_route(
        filename, contents, embedding_model, milvus_client, url_redis_client,
    )

@app.post('/scrape-pdf')
async def scrape_pdf(request: Request) -> None:
    request_data = await request.json()
    url = request_data.get('url')
    scrape_images = request_data.get('scrape-image')

    if not url or scrape_images not in [True, False]:
        raise HTTPException(status_code=400, detail='Correct Params was not supplied')

    status: int | None = await scrape_pdf_route(
        url, embedding_model, milvus_client, gemini_client, url_redis_client, scrape_images
    )
    if status == 404:
        raise HTTPException(status_code=404, detail='PDF not found')

@app.post('/ask')
async def ask(request: Request) -> dict:
    request_data = await request.json()
    query = request_data.get('query')
    session_id = request_data.get('session_id')

    if not query or not session_id:
        raise HTTPException(status_code=400, detail='Correct Params (query, session_id) were not supplied')

    # --- Start of Integrated RAG Pipeline ---

    # 1. Log original query for analytics (preserving original functionality)
    try:
        sentiment = sentiment_pipeline(query)[0]
        token_count = len(tokenizer.encode(query))
        log_entry = {
            "query": query,
            "sentiment_label": sentiment['label'],
            "sentiment_score": sentiment['score'],
            "token_count": token_count,
            "timestamp": datetime.datetime.utcnow().isoformat()
        }
        db_redis_client.lpush('queries', json.dumps(log_entry))
    except Exception as e:
        print(f"Could not log query analytics: {e}")

    # 2. Rewrite query for better contextual search
    rewritten_query = await rewrite_query_with_groq(groq_client, session_id, query, chat_redis_client)
    
    # 3. Search Milvus for relevant documents
    # IMPORTANT: Replace 'web_content' with your actual Milvus collection name
    hits = search_milvus(milvus_client, embedding_model, 'd2', rewritten_query, top_k=10)
    
    # 4. Curate results (deduplicate & sort) and check freshness
    curated_docs = curate_results(hits)
    fresh_docs = [doc for doc in curated_docs if check_freshness(doc)]
    
    # Use fresh docs if available, otherwise fall back to the most relevant stale docs
    final_context_docs = fresh_docs if fresh_docs else curated_docs
    is_stale = not bool(fresh_docs) and bool(curated_docs)
    
    # 5. Generate the final answer using Groq
    answer = await generate_answer_with_groq(groq_client, rewritten_query, final_context_docs)
    
    # 6. Update chat history in Redis
    chat_redis_client.rpush(f"history:{session_id}", f"User: {query}")
    chat_redis_client.rpush(f"history:{session_id}", f"AI: {answer.split('Citations:')[0].strip()}")
    chat_redis_client.ltrim(f"history:{session_id}", -10, -1) # Keep last 5 interactions (10 entries)

    # 7. Construct and return the final detailed response
    response = {
        "response": answer,
        "response_type": "IN_DOMAIN" if final_context_docs else "OUT_OF_SCOPE",
        "retrieval_timestamp": datetime.datetime.utcnow().isoformat(),
        "staleness_flag": is_stale,
        "source_audit": [
            {
                "url": doc.get("url"),
                "content_date": doc.get("content_date"),
                "is_fresh": check_freshness(doc),
                "retrieval_score": doc.get("score")
            } for doc in final_context_docs
        ]
    }
    return response

@app.get('/number-of-queries')
async def number_of_queries() -> dict:
    nqueries = db_redis_client.lrange('query', 0, -1)
    return {'nqueries': nqueries}

@app.get('/sentiment')
async def get_sentiment() -> dict:
    nqueries_ = await get_sentiment_route(db_redis_client)
    return {'nqueries': nqueries_}

@app.get('/token-count')
async def get_token_count() -> dict:
    response = await get_token_count_route(db_redis_client)
    return response

@app.get('/category')
async def get_category() -> dict:
    response = await get_category_route(db_redis_client)
    return response

if __name__ == '__main__':
    uvicorn.run('app:app', host='0.0.0.0', port=8888)
