import uvicorn
import asyncio
from typing import Dict
from dotenv import load_dotenv
from fastapi import FastAPI, Request, HTTPException, File, UploadFile, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware

from scripts.scrapper.services import get_pdf_links
from scripts.loader.loader import (
    load_embedding_model,
    load_sentiment_pipeline, 
    load_tokenizer, 
    load_milvus_client, 
    load_redis_client, 
    load_embedding_model, 
    load_gemini_client, 
    load_groq_client
)

from scripts.routers.routers import (
    scrape_page_route, 
    scrape_pdf_route, 
    scrape_pdf__file_route, 
    ask_route, 
    get_sentiment_route, 
    get_token_count_route, 
    get_category_route
)

load_dotenv()

# Global storage for background task results
task_results: Dict[str, dict] = {}

# Load all clients and models
sentiment_pipeline = load_sentiment_pipeline()
tokenizer = load_tokenizer()
milvus_client = load_milvus_client()

chat_redis_client = load_redis_client(0)
db_redis_client = load_redis_client(1)
url_redis_client = load_redis_client(2)

embedding_model = load_embedding_model()
gemini_client = load_gemini_client()
groq_client = load_groq_client()

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

@app.get('/')
async def read_root():
    return {'Hello': 'World'}

# Background task function
async def scrape_url_background(task_id: str, url: str):
    try:
        # If get_pdf_links is synchronous, run it in a thread pool
        loop = asyncio.get_event_loop()
        pdf_links, all_links = await loop.run_in_executor(
            None, lambda: asyncio.run(get_pdf_links(url)) if asyncio.iscoroutinefunction(get_pdf_links) 
            else get_pdf_links(url)
        )
        
        task_results[task_id] = {
            'status': 'completed',
            'result': {
                'pdf_links': pdf_links,
                'all_links': all_links
            }
        }
    except Exception as e:
        task_results[task_id] = {
            'status': 'failed',
            'error': str(e)
        }

@app.post('/scrape-url')
async def scrape_url(request: Request, background_tasks: BackgroundTasks) -> dict:
    request_data = await request.json()
    url: str = request_data.get('url', '')
    
    if not url:
        raise HTTPException(
            status_code=400,
            detail='URL was not supplied'
        )
    
    # Generate unique task ID
    import uuid
    task_id = str(uuid.uuid4())
    
    # Initialize task status
    task_results[task_id] = {'status': 'processing'}
    
    # Add background task
    background_tasks.add_task(scrape_url_background, task_id, url)
    
    return {
        'task_id': task_id,
        'status': 'started',
        'message': 'Scraping started in background. Use /task-status/{task_id} to check progress.'
    }

@app.get('/task-status/{task_id}')
async def get_task_status(task_id: str) -> dict:
    if task_id not in task_results:
        raise HTTPException(status_code=404, detail='Task not found')
    
    return task_results[task_id]

# Alternative: Synchronous version that runs in thread pool
@app.post('/scrape-url-sync')
async def scrape_url_sync(request: Request) -> dict:
    request_data = await request.json()
    url: str = request_data.get('url', '')
    
    if not url:
        raise HTTPException(
            status_code=400,
            detail='URL was not supplied'
        )
    
    # Run the potentially blocking operation in a thread pool
    loop = asyncio.get_event_loop()
    
    try:
        if asyncio.iscoroutinefunction(get_pdf_links):
            pdf_links, all_links = await get_pdf_links(url)
        else:
            # Run synchronous function in thread pool to avoid blocking
            pdf_links, all_links = await loop.run_in_executor(None, get_pdf_links, url)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
    return {
        'pdf_links': pdf_links,
        'all_links': all_links
    }

@app.post('/scrape-page')
async def scrape_page(request: Request) -> None:
    request_data = await request.json()
    url = request_data.get('url')
    scrape_images = request_data.get('scrape-images')
    
    if (not url or not (scrape_images in [False, True])):
        raise HTTPException(
            status_code=400,
            detail='Correct Params was not supplied'
        )
    
    await scrape_page_route(
        url,
        embedding_model,
        milvus_client,
        gemini_client,
        url_redis_client,
        scrape_images
    )

@app.post('/scrape-pdf-file')
async def scrape_pdf_file(file: UploadFile = File(...)) -> None:
    contents = await file.read()
    filename = str(file.filename)
    
    if not contents:
        raise HTTPException(
            status_code=400,
            detail='Correct Params was not supplied'
        )
    
    await scrape_pdf__file_route(
        filename,
        contents,
        embedding_model,
        milvus_client,
        url_redis_client,
    )

@app.post('/scrape-pdf')
async def scrape_pdf(request: Request) -> None:
    request_data = await request.json()
    url = request_data.get('url')
    scrape_images = request_data.get('scrape-image')
    
    if (not url or not (scrape_images in [False, True])):
        raise HTTPException(
            status_code=400,
            detail='Correct Params was not supplied'
        )
    
    await scrape_pdf_route(
        url,
        embedding_model,
        milvus_client,
        gemini_client,
        url_redis_client,
        scrape_images
    )

@app.post('/ask')
async def ask(request: Request) -> dict:
    request_data = await request.json()
    query = request_data.get('query')
    session_id = request_data.get('session_id')
    
    if not query or not session_id:
        raise HTTPException(
            status_code=400,
            detail='Correct Params was not supplied'
        )

    response: str = await ask_route(
        query,
        session_id,
        embedding_model,
        milvus_client,
        chat_redis_client,
        db_redis_client,
        groq_client,
        tokenizer,
        sentiment_pipeline
    )
    
    return {'response': response}

@app.get('/number-of-queries')
async def number_of_queries() -> dict:
    nqueries = db_redis_client.lrange('query', 0, -1)
    return {'nqueries': nqueries}

@app.get('/sentiment')
async def get_sentiment() -> dict:
    nqueries_: dict = await get_sentiment_route(db_redis_client)
    return {'nqueries': nqueries_}

@app.get('/token-count')
async def get_token_count() -> dict:
    response: dict = await get_token_count_route(db_redis_client)
    return response

@app.get('/category')
async def get_category() -> dict:
    response: dict = await get_category_route(db_redis_client)
    return response

if __name__ == '__main__':
    uvicorn.run(
        'app:app',
        host='0.0.0.0',
        port=8888,
        workers=1  # For development. For production, consider multiple workers
    )