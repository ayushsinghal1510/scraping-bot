from fastapi import FastAPI , Request 
from pymilvus import MilvusClient
from redis import Redis 
from uuid import uuid4 

import uvicorn
from halo import Halo
from wasabi import msg
import os 
from sentence_transformers import SentenceTransformer

import google.generativeai as genai
import json
from groq import Groq 

from scripts.scrapper.services import get_pdf_links
from scripts.scrapper.page import page_to_docs
from scripts.scrapper.pdf import pdf_to_docs
from scripts.llm.services import save_history , load_history
from scripts.llm.runner import run_groq
from fastapi.middleware.cors import CORSMiddleware

from dotenv import load_dotenv
load_dotenv()

db_name = os.getenv('MILVUS_DB_NAME' , '')

model_name = os.getenv('MILVUS_MODEL_NAME')
vector_size = int(os.getenv('MILVUS_MODEL_SIZE' , 384))
collection_name = os.getenv('MILVUS_COLLECTION_NAME' , '')
all_docs = {}

spinner = Halo(text = 'Loading Milvus Client' , spinner = 'dots')
spinner.start()
milvus_client = MilvusClient(db_name)
milvus_client.create_collection(collection_name = collection_name , dimension = vector_size)
spinner.stop()
msg.good('Milvus Client Loaded')

spinner = Halo(text = 'Loading Redit Client' , spinner = 'dots')
spinner.start()
redis_client = Redis(
    host = os.getenv('REDIS_HOST' , 'localhost') ,  
    port = int(os.getenv('REDIS_PORT' , 6379)) ,  
    decode_responses = True
)
spinner.stop()
msg.good('Redit Client Loaded')

spinner = Halo(text = 'Loading Embedding Model' , spinner = 'dots')
spinner.start()
embedding_model = SentenceTransformer(model_name)
spinner.stop()
msg.good('Embedding Model Loaded')

spinner = Halo(text = 'Loading Gemini Client' , spinner = 'dots')
spinner.start()
# genai.configure(api_key = '<Enter the Gemini API Key here>') # ! Can deploy a Llama 3.2 Model and use that instead, which can increase speed and avoid rate limits and increase safety as well
# image_model = genai.GenerativeModel('gemini-1.5-flash')
image_model = ''
spinner.stop()
msg.good('Embedding Model Loaded')

spinner = Halo(text = 'Loading GROQ Client' , spinner = 'dots')
spinner.start()
groq_client = Groq()
llm_model = os.getenv('GROQ_MODEL')
# groq_client = ''
spinner.stop()
msg.good('GROQ Model Loaded')

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
async def scrape_url(request : Request) : 

    request = await request.json()

    base_html = request['base-html']
    perm_url = request['perm-url']

    pdf_links , all_links = await get_pdf_links(base_html , perm_url)

    return {
        'pdf_links' : pdf_links , 
        'all_links' : all_links
    }

@app.post('/scrape-page')
async def scrape_page(request : Request) : 

    request = await request.json()

    url = request['url']
    scrape_image = request['scrape-images']

    documents = await page_to_docs(url , scrape_image)

    texts = [document['text'] for document in documents]
    embeddings = embedding_model.encode(texts , show_progress_bar = True)

    for document , embedding in zip(documents , embeddings) : 

        uid = int(str(int(uuid4()))[:5])

        data = {
            'id' :  uid , # ! Fix this
            'vector' : embedding
        }

        all_docs[uid] = document

        for key , value in zip(document.keys() , document.values()) : data[key] = value

        milvus_client.insert(
            collection_name = collection_name , 
            data = [data]
        )

    return {'Added Docs Successfully'}

@app.post('/scrape-pdf')
async def scrape_pdf(request : Request) :

    request = await request.json()

    pdf_link = request['url']
    scrape_image = request['scrape-image'] # ! use post and error handling/ checks for the server

    documents = await pdf_to_docs(pdf_link , scrape_image , image_model)

    texts = [document['text'] for document in documents]
    embeddings = embedding_model.encode(texts , show_progress_bar = True)

    for document , embedding in zip(documents , embeddings) : 

        uid = int(str(int(uuid4()))[:5])

        data = {
            'id' :  uid , # ! Fix this
            'vector' : embedding
        }

        all_docs[uid] = document

        for key , value in zip(document.keys() , document.values()) : data[key] = value

        milvus_client.insert(
            collection_name = collection_name , 
            data = [data]
        )

    return {'Added Docs Successfully'}

@app.post('/ask') 
async def ask(request : Request) : 

    request = await request.json()

    query = request['query']
    session_id = request['session_id']

    print(session_id)

    query_embeddings = embedding_model.encode(query)

    results = milvus_client.search(
        collection_name = collection_name , 
        data = [query_embeddings] , 
        limit = 2 , 
        output_fields = ['text' , 'source']
    )

    # print(json.dumps(results , indent = 4))

    results = results[0]

    context = '\n'.join([f'''Content : {row['entity']['text']} + {row['entity']['source']}''' for row in results])

    with open('assets/database/prompt/rag.md') as rag_prompt_file : prompt = rag_prompt_file.read()

    history = await load_history(redis_client , session_id)

    if history == [] : history = [
        {
            'role' : 'system' , 
            'content' : prompt
        }
    ]

    history.append({
        'role' : 'user' , 
        'content' : f'''
Context : {context}

Query : {query}
        '''
    })

    response = await run_groq(history , groq_client , llm_model)
    # response = 'this is a sample respone'

    history.append({
        'role' : 'assistant' , 
        'content' : response
    })

    await save_history(redis_client , history , session_id)

    return {'response' : response}

@app.post('/update-image-prompt')
async def update_image_prompt(request : Request) : 

    request = await request.json()

    prompt = request['prompt']

    if '{}' not in prompt : return {'Error' : 'Prompt should contain {}'}

    with open('assets/database/prompt/image_ingestion.md' , 'w') as image_ingestion_prompt_file : image_ingestion_prompt_file.write(prompt)

    return {'Prompt Updated Successfully'}


if __name__ == '__main__' : uvicorn.run(
    'app:app' , 
    host = '0.0.0.0' , 
    port = 7860
)