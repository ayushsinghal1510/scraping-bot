import uvicorn

from dotenv import load_dotenv

from fastapi import FastAPI , Request , HTTPException , File , UploadFile

from fastapi.middleware.cors import CORSMiddleware

from scripts.scrapper.services import get_pdf_links

from scripts.loader.loader import (
    load_embedding_model,
    load_sentiment_pipeline , 
    load_tokenizer , 
    load_milvus_client , 
    load_redis_client , 
    load_embedding_model , 
    load_gemini_client , 
    load_groq_client
)

from scripts.routers.routers import (
    scrape_page_route , 
    scrape_pdf_route , 
    scrape_pdf__file_route , 
    ask_route , 
    get_sentiment_route , 
    get_token_count_route , 
    get_category_route
)

load_dotenv()

global num_rows

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
    CORSMiddleware , 
    allow_origins = ['*'] , 
    allow_credentials = True , 
    allow_methods = ['*'] , 
    allow_headers = ['*'] , 
)

@app.get('/')
async def read_root() : return {'Hello' : 'World'}

@app.post('/scrape-url')
async def scrape_url(request : Request) -> dict : 

    request = await request.json()

    url : str = request.get('url' , '')
    
    if not url : raise HTTPException(
        status_code = 400 , 
        detail = 'URL was not supplied'
    )

    pdf_links , all_links = await get_pdf_links(url)

    return {
        'pdf_links' : pdf_links , 
        'all_links' : all_links
    }

@app.post('/scrape-page')
async def scrape_page(request : Request) -> None : 

    request = await request.json()

    url = request.get('url')
    scrape_images = request.get('scrape-images')
    
    if (
        not url or 
        not (
            scrape_images == False or 
            scrape_images == True
        )
    ) : raise HTTPException(
        status_code = 400 , 
        detail = 'Correct Params was not supplied'
    )
    
    await scrape_page_route(
        url , 
        embedding_model , 
        milvus_client , 
        gemini_client , 
        url_redis_client ,  
        scrape_images
    )

@app.post('/scrape-pdf-file')
async def scrape_pdf_file(request : Request , file : UploadFile = File(...)) -> None :

    request = await request.json()
    contents = await file.read()
    filename = str(file.filename)

    scrape_images = request.get('scrape-images')
    
    if (
        not contents or 
        not (
            scrape_images == False or 
            scrape_images == True
        )
    ) : raise HTTPException(
        status_code = 400 , 
        detail = 'Correct Params was not supplied'
    )
    
    await scrape_pdf__file_route(
        filename , 
        contents , 
        embedding_model , 
        milvus_client , 
        gemini_client , 
        url_redis_client ,  
        scrape_images
    )

@app.post('/scrape-pdf')
async def scrape_pdf(request : Request) -> None :

    request = await request.json()

    url = request.get('url')
    scrape_images = request.get('scrape-images')
    
    if (
        not url or 
        not (
            scrape_images == False or 
            scrape_images == True
        )
    ) : raise HTTPException(
        status_code = 400 , 
        detail = 'Correct Params was not supplied'
    )
    
    await scrape_pdf_route(
        url , 
        embedding_model , 
        milvus_client , 
        gemini_client , 
        url_redis_client ,  
        scrape_images
    )

@app.post('/ask') 
async def ask(request : Request) -> dict : 

    request = await request.json()

    query = request.get('query')
    session_id = request.get('session_id')
    
    if (
        not query or 
        not session_id
    ) : raise HTTPException(
        status_code = 400 , 
        detail = 'Correct Params was not supplied'
    )

    response : str  = await ask_route(
        query , 
        session_id , 
        embedding_model , 
        milvus_client , 
        chat_redis_client , 
        db_redis_client , 
        groq_client , 
        tokenizer , 
        sentiment_pipeline
    )
    
    return {'response' : response}

@app.get('/number-of-queries')
async def number_of_queries() -> dict : 
    
    nqueries = db_redis_client.lrange('query' , 0 , -1)
    
    return {'nqueries' : nqueries}

@app.get('/sentiment')
async def get_sentiment() -> dict : 

    nqueries_ : dict = await get_sentiment_route(db_redis_client)
            
    return {'nqueries' : nqueries_}

@app.get('/token-count')
async def get_token_count() -> dict : 

    response : dict = await get_token_count_route(db_redis_client)

    return response 

@app.get('/category')
async def get_category() -> dict : 
    
    response : dict = await get_category_route(db_redis_client)

    return response

if __name__ == '__main__' : uvicorn.run(
    'app:app' , 
    host = '0.0.0.0' , 
    port = 8888
)