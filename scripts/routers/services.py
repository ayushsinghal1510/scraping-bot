import hashlib 
from pymilvus import MilvusClient
from redis import Redis
import json
import os 

async def hash_url(url : str) -> int :  
    
    url_hash = hashlib.md5(url.encode()).hexdigest()[:8]  # 15 hex chars = 60 bits
    
    url_prefix = int(url_hash , 16)
    
    return url_prefix

async def clean_redis(
    url : str , 
    url_redis_client : Redis , 
    milvus_client : MilvusClient
) -> None : 
    
    collection_name = os.getenv('MILVUS_COLLECTION_NAME' , 'd1')
    
    existing_ids : list = url_redis_client.get(url)

    if existing_ids : 
        

        existing_ids = json.loads(existing_ids)

        print(f'Cleaning Milvus for {url} : {existing_ids}')

        milvus_client.delete(
            collection_name = collection_name,
            filter=f'id in {existing_ids}'
        )