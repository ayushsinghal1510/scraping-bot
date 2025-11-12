import uvicorn

from dotenv import load_dotenv

from urllib.request import urlopen
from urllib.request import Request as urlRequest

from fastapi import HTTPException, Request
from .scripts import (
    load_all_clients , 

    WEB , PDF , 
    INFERENCE
)

load_dotenv()

(
    config , 
    sentiment_pipeline , 
    tokenizer , 
    milvus_client , 
    chat_redis_client , 
    db_redis_client , 
    url_redis_client , 
    embedding_model , 
    gemini_client , 
    groq_client , 
    app , 
    logger
) = load_all_clients()

inference_client : INFERENCE = INFERENCE(
    milvus_client = milvus_client , 
    chat_redis_client = chat_redis_client , 
    embedding_model = embedding_model , 
    config = config['inference'] , 
    groq_client = groq_client
)

@app.post('/scrape-url')
async def scrape_url(request : Request) -> dict : 

    data : dict = await request.json()

    if (
        'url' not in data
    ) : raise HTTPException(
        status_code = 400 , 
        detail = 'URL was not supplied'
    )

    web : WEB = WEB(
        milvus_client = milvus_client , 
        url = data['url'] , 
        collection_name = 'd2' , 
        config = config['website'] , 
        embedding_client = embedding_model
    )

    return web.extract_custom_sitemap()

@app.post('/scrape-page')
async def scrape_page(request : Request) : 

    data : dict = await request.json()

    if (
        'url' not in data and 
        'scrape-images' not in data
    ) : raise HTTPException(
        status_code = 400 , 
        detail = 'Correct Params was not supplied'
    )

    web : WEB = WEB(
        milvus_client = milvus_client , 
        url = data['url'] , 
        collection_name = 'd2' , 
        config = config['website'] , 
        embedding_client = embedding_model
    )

    web.create_direct_chunks_and_add_to_vectordb()

@app.post('/scrape-pdf')
async def scrape_pdf(request : Request) : 

    data : dict = await request.json()

    if (
        'url' not in data and 
        'scrape-image' not in data
    ) : raise HTTPException(
        status_code = 400 , 
        detail = 'Correct Params was not supplied'
    )

    req = urlRequest(data['url'] , headers = {'User-Agent' : 'Mozilla/5.0'})

    with urlopen(req) as response: pdf_bytes : bytes = response.read()

    pdf : PDF = PDF(
        milvus_client = milvus_client , 
        pdf_bytes = pdf_bytes , 
        collection_name = 'd2' , 
        config = config['website'] , 
        embedding_client = embedding_model , 
        pdf_name = data['url']
    )

    pdf()

@app.post('/ask')
async def ask(request : Request) : 

    data : dict = await request.json()

    if (
        'query' not in data and 
        'session_id' not in data
    ) : raise HTTPException(
        status_code = 400 , 
        detail = 'Correct params was not supplied'
    )

    response : dict = await inference_client(
        query = data['query'] , 
        session_id = data['session_id']
    )

    print(response)

    return response


def main() : uvicorn.run(
    app , 
    host = '0.0.0.0' , 
    port = 7860
)



    