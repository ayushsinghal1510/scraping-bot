import os 
import json

from datetime import datetime 

from scripts.scrapper.page import page_to_docs
from scripts.scrapper.pdf import pdf_to_docs , pdf_file_to_docs
from scripts.llm.runner import run_groq

from scripts.llm.services import save_history , load_history
from scripts.routers.services import hash_url , clean_redis

from sentence_transformers import SentenceTransformer
from pymilvus import MilvusClient
from redis import Redis
from groq import Groq 
from transformers.pipelines import Pipeline
from transformers.tokenization_utils_fast import PreTrainedTokenizerFast
import numpy as np

from tqdm import tqdm

async def scrape_page_route(
    url : str , 
    embedding_model : SentenceTransformer , 
    milvus_client : MilvusClient , 
    image_model , 
    url_redis_client : Redis , 
    scrape_images : bool = False
) -> str | None : 
    
    url_prefix : int = await hash_url(url)
    _ : None = await clean_redis(
        url , 
        url_redis_client , 
        milvus_client
    )
    
    chunk_counter = 1   
    
    collection_name = os.getenv('MILVUS_COLLECTION_NAME' , 'd1')
    
    documents : list = await page_to_docs(url , scrape_images , image_model)
    
    if not isinstance(documents[0] , str) : 

        texts = [document['text'] for document in documents]
        embeddings : np.ndarray = embedding_model.encode(texts[ : 100_000] , show_progress_bar = True)
        ids = []

        for document , embedding in zip(documents , embeddings) : 

            id_ = url_prefix * 100_000 + chunk_counter
            chunk_counter += 1
            
            ids.append(id_)

            data = {
                'id' : id_ ,
                'vector' : embedding
            }

            for key , value in zip(document.keys() , document.values()) : data[key] = value

            milvus_client.insert(
                collection_name = collection_name , 
                data = [data]
            )
            
        if len(documents) > 100_000 : print(f'Warning: Document from {url} had {len(documents)} chunks, but only processed 100_000 ')
        
        url_redis_client.set(url , json.dumps(ids))
        
        return None
        
    return documents[0]

async def scrape_pdf_route(
    url : str , 
    embedding_model : SentenceTransformer , 
    milvus_client : MilvusClient , 
    image_model , 
    url_redis_client : Redis , 
    scrape_images : bool = False
) -> None | int : 
    
    url_prefix : int = await hash_url(url)
    _ : None = await clean_redis(
        url , 
        url_redis_client , 
        milvus_client
    )
    
    chunk_counter = 1  

    collection_name = os.getenv('MILVUS_COLLECTION_NAME' , 'd1')
    
    documents : list | None = await pdf_to_docs(url , scrape_images , image_model)
    
    if documents : 

        texts = [document['text'] for document in documents]
        embeddings : np.ndarray = embedding_model.encode(texts[ : 100_000] , show_progress_bar = True)
        ids = []

        for document , embedding in zip(documents , embeddings) : 

            id_ = url_prefix * 100_000 + chunk_counter
            chunk_counter += 1
            
            ids.append(id_)

            data = {
                'id' : id_ ,
                'vector' : embedding
            }

            for key , value in zip(document.keys() , document.values()) : data[key] = value

            milvus_client.insert(
                collection_name = collection_name , 
                data = [data]
            )
            
        if len(documents) > 100_000 : print(f'Warning: Document from {url} had {len(documents)} chunks, but only processed 100_000 ')
        
        url_redis_client.set(url , json.dumps(ids))
        
        return None
        
    return 404
    
async def scrape_pdf__file_route(
    filename : str , 
    contents : bytes , 
    embedding_model : SentenceTransformer , 
    milvus_client : MilvusClient , 
    url_redis_client : Redis ,
) -> None : 

    url_prefix : int = await hash_url(filename)
    _ : None = await clean_redis(
        filename , 
        url_redis_client , 
        milvus_client
    )
    
    chunk_counter = 1  

    collection_name = os.getenv('MILVUS_COLLECTION_NAME' , 'd1')
    filename = f'assets/pdfs/{filename}' 
    
    with open(filename , 'wb') as pdf_file : pdf_file.write(contents)
    
    documents : list = await pdf_file_to_docs(filename)

    texts = [document['text'] for document in documents]
    embeddings : np.ndarray = embedding_model.encode(texts[ : 100_000] , show_progress_bar = True)
    ids = []

    for document , embedding in zip(documents , embeddings) : 

        id_ = url_prefix * 100_000 + chunk_counter
        chunk_counter += 1
        
        ids.append(id_)

        data = {
            'id' : id_ ,
            'vector' : embedding
        }

        for key , value in zip(document.keys() , document.values()) : data[key] = value

        milvus_client.insert(
            collection_name = collection_name , 
            data = [data]
        )
        
    if len(documents) > 100_000 : print(f'Warning: Document from {filename} had {len(documents)} chunks, but only processed 100_000 ')
    
    url_redis_client.set(filename , json.dumps(ids))

async def ask_route(
    query : str , 
    session_id : str , 
    embedding_model : SentenceTransformer , 
    milvus_client : MilvusClient , 
    chat_redis_client : Redis , 
    db_redis_client : Redis , 
    groq_client : Groq , 
    tokenizer : PreTrainedTokenizerFast , 
    sentiment_pipeline : Pipeline  
) -> str : 
    
    query_embeddings = embedding_model.encode(query)

    collection_name = os.getenv('MILVUS_COLLECTION_NAME' , 'd1')

    results : list = milvus_client.search(
        collection_name = collection_name , 
        data = [query_embeddings] , 
        limit = 2 , 
        output_fields = ['text' , 'source']
    )[0]

    context = '\n'.join([f'''Content : {row['entity']['text']} + {row['entity']['source']}''' for row in results])

    with open('assets/database/prompt/rag.md') as rag_prompt_file : prompt = rag_prompt_file.read()

    history : list = await load_history(chat_redis_client , session_id)

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

    response : str  = await run_groq(history , groq_client)
    dict_response : dict = json.loads(response)
    categories :list = dict_response['category']
    answer : str = dict_response['response']

    history.append({
        'role' : 'assistant' , 
        'content' : answer
    })
    
    db_redis_client.rpush('query' , json.dumps({
        'query' : query , 
        'time' :  str(datetime.now()) , 
        'token_count' : len(tokenizer(query).get('input_ids' , [0])) , 
        'sentiment' : sentiment_pipeline(query)[0].get('score' , 0) , 
        'category' : categories
    }))
    
    db_redis_client.rpush('response' , json.dumps({
        'query' : query , 
        'time' :  str(datetime.now()) , 
        'token_count' : len(tokenizer(answer).get('input_ids' , [0])) , 
    }))

    await save_history(chat_redis_client , history , session_id)
    
    return answer

async def get_sentiment_route(db_redis_client : Redis) -> dict : 
    
    nqueries = db_redis_client.lrange('query' , -200 , -1)
    
    nqueries_ = {'time' : [] , 'sentiment' : []}
    
    for nthquery in tqdm(nqueries , total = len(nqueries)) : 
        
        try : 
            
            data = json.loads(nthquery)
            
            nqueries_['time'].append(data['time'])
            nqueries_['sentiment'].append(data['sentiment'])

        except Exception as e : print(e)
    
    
    
    return nqueries_

async def get_token_count_route(db_redis_client : Redis) -> dict : 
    
    nqueries = db_redis_client.lrange('query' , -200, -1)
    nresponses = db_redis_client.lrange('response' , -200 , -1)
    
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

            data : dict = json.loads(nthresponse)

            nresponses_['time'].append(data['time'])
            nresponses_['token_count'].append(data.get('token_count'))

        except Exception as e : print(e)

    return {
        'nqueries' : nqueries_ , 
        'nresponses' : nresponses_
    }

async def get_category_route(db_redis_client : Redis) -> dict : 
    
    nqueries = db_redis_client.lrange('query' , -200 , -1)
    
    nqueries_ = {'time' : [] , 'category' : []}
    
    for nthquery in tqdm(nqueries , total = len(nqueries)) : 
        
        try : 
            
            data = json.loads(nthquery)
            
            nqueries_['time'].append(data['time'])
            nqueries_['category'].append(data.get('category'))

        except Exception as e : print(e)
    
    return {'nqueries' : nqueries_}
