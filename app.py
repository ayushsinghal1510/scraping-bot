from fastapi import FastAPI , Request , HTTPException 
from pymilvus import MilvusClient
from redis import Redis 
from uuid import uuid4 

import uvicorn
import os 
from sentence_transformers import SentenceTransformer

import google.generativeai as genai
from tqdm import tqdm
import json
from groq import Groq 

from scripts.scrapper.services import get_pdf_links
from scripts.scrapper.page import page_to_docs
from scripts.scrapper.pdf import pdf_to_docs
from scripts.llm.services import save_history , load_history
from scripts.llm.runner import run_groq
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime

from dotenv import load_dotenv
load_dotenv()

from transformers import AutoTokenizer
from transformers import pipeline

sentiment_pipeline = pipeline('sentiment-analysis')

tokenizer = AutoTokenizer.from_pretrained('meta-llama/Meta-Llama-3-8B')

db_name = os.getenv('MILVUS_DB_NAME' , '')

model_name = os.getenv('MILVUS_MODEL_NAME')
vector_size = int(os.getenv('MILVUS_MODEL_SIZE' , 384))
collection_name = os.getenv('MILVUS_COLLECTION_NAME' , '')
all_docs = {}


milvus_client = MilvusClient(db_name)
milvus_client.create_collection(collection_name = collection_name , dimension = vector_size)

chat_redis_client = Redis(
    host = os.getenv('REDIS_HOST' , 'localhost') ,  
    port = int(os.getenv('REDIS_PORT' , 6379)) , 
    db = 0  , 
    decode_responses = True
)
db_redis_client = Redis(
    host = os.getenv('REDIS_HOST' , 'localhost') ,  
    port = int(os.getenv('REDIS_PORT' , 6379)) , 
    db = 1 ,  
    decode_responses = True
)

embedding_model = SentenceTransformer(model_name)

# genai.configure(api_key = '<Enter the Gemini API Key here>') # ! Can deploy a Llama 3.2 Model and use that instead, which can increase speed and avoid rate limits and increase safety as well
# image_model = genai.GenerativeModel('gemini-1.5-flash')
image_model = ''


groq_client = Groq()
llm_model = os.getenv('GROQ_MODEL' , '')
# groq_client = ''

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

    url = request['url']
    
    if url : 
    
        pdf_links , all_links = await get_pdf_links(url)

        return {
            'pdf_links' : pdf_links , 
            'all_links' : all_links
        }

    return HTTPException(
        status_code = 400 , 
        detail = 'URL was not supplied'
    )

@app.post('/scrape-page')
async def scrape_page(request : Request) : 

    request = await request.json()

    url = request.get('url')
    scrape_images = request.get('scrape-images')

    if (
        url and (
            scrape_images == False or 
            scrape_images == True 
        )
    ) : 

        documents = await page_to_docs(url , scrape_images)

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

    return HTTPException(
        status_code = 400 , 
        detail = 'Correct Params was not supplied'
    )

@app.post('/scrape-pdf')
async def scrape_pdf(request : Request) :

    request = await request.json()

    url = request.get('url')
    scrape_images = request.get('scrape-images') # ! use post and error handling/ checks for the server

    if (
        url and (
            scrape_images == False or 
            scrape_images == True 
        )
    ) : 


        documents = await pdf_to_docs(url , scrape_images , image_model)

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

    return HTTPException(
        status_code = 400 , 
        detail = 'Correct Params was not supplied'
    )

@app.post('/ask') 
async def ask(request : Request) : 

    request = await request.json()

    query = request.get('query')
    session_id = request.get('session_id')
    
    if query and session_id : 

        query_embeddings = embedding_model.encode(query)

        results = milvus_client.search(
            collection_name = collection_name , 
            data = [query_embeddings] , 
            limit = 2 , 
            output_fields = ['text' , 'source']
        )

        results = results[0]

        context = '\n'.join([f'''Content : {row['entity']['text']} + {row['entity']['source']}''' for row in results])

        with open('assets/database/prompt/rag.md') as rag_prompt_file : prompt = rag_prompt_file.read()

        history = await load_history(chat_redis_client , session_id)

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
        response = json.loads(response)
        categories = response['category']
        response = response['response']
        # response = 'this is a sample respone'

        history.append({
            'role' : 'assistant' , 
            'content' : response
        })
        
        db_redis_client.rpush('query' , json.dumps({
            'query' : query , 
            'time' :  str(datetime.now()) , 
            'token_count' : len(tokenizer(query)['input_ids']) , 
            'sentiment' : sentiment_pipeline(query)[0]['score'] , 
            'category' : categories
        }))
        
        db_redis_client.rpush('response' , json.dumps({
            'query' : query , 
            'time' :  str(datetime.now()) , 
            'token_count' : len(tokenizer(response)['input_ids']) , 
        }))

        await save_history(chat_redis_client , history , session_id)

        return {'response' : response}

    return HTTPException(
        status_code = 400 , 
        detail = 'Correct Params was not supplied'
    )

@app.get('/number-of-queries')
async def number_of_queries() : 
    
    nqueries = db_redis_client.lrange('query' , 0 , -1)
    
    return {'nqueries' : nqueries}

@app.get('/sentiment')
async def get_sentiment() : 

    nqueries = db_redis_client.lrange('query' , 0 , -1)
    
    nqueries_ = {'time' : [] , 'sentiment' : []}
    
    for nthquery in tqdm(nqueries , total = len(nqueries)) : 
        
        try : 
            
            data = json.loads(nthquery)
            
            nqueries_['time'].append(data['time'])
            nqueries_['sentiment'].append(data['sentiment'])

        except Exception as e : print(e)
            
    return {'nqueries' : nqueries_}

@app.get('/token-count')
async def get_token_count() : 

    nqueries = db_redis_client.lrange('query' , 0 , -1)
    nresponses = db_redis_client.lrange('response' , 0 , -1)
    
    nqueries_ = {'time' : [] , 'token_count' : []}
    nresponses_ = {'time' : [] , 'token_count' : []}
    
    for nthquery in tqdm(nqueries , total = len(nqueries)) : 
        
        try : 
            
            data = json.loads(nthquery)
            
            nqueries_['time'].append(data['time'])
            nqueries_['token_count'].append(data.get('token_count'))

        except Exception as e : print(e)

    for nthresponse in tqdm(nresponses , total = len(nresponses)) : 
        
        try : 
            
            data = json.loads(nthresponse)
            
            nresponses_['time'].append(data['time'])
            nresponses_['token_count'].append(data.get('token_count'))

        except Exception as e : print(e)
    
    return {
        'nqueries' : nqueries_ , 
        'nresponses' : nresponses_
    }


@app.get('/category')
async def get_category() : 

    nqueries = db_redis_client.lrange('query' , 0 , -1)
    
    nqueries_ = {'time' : [] , 'category' : []}
    
    for nthquery in tqdm(nqueries , total = len(nqueries)) : 
        
        try : 
            
            data = json.loads(nthquery)
            
            nqueries_['time'].append(data['time'])
            nqueries_['category'].append(data.get('category'))

        except Exception as e : print(e)
    
    return {'nqueries' : nqueries_}





if __name__ == '__main__' : uvicorn.run(
    'app:app' , 
    host = '0.0.0.0' , 
    port = 7860
)