from transformers import pipeline , AutoTokenizer
from pymilvus import MilvusClient
import os 
from redis import Redis
from sentence_transformers import SentenceTransformer
import google.generativeai as genai
from pymilvus import Collection
from groq import Groq

from transformers.pipelines import Pipeline
from transformers.tokenization_utils_fast import PreTrainedTokenizerFast

def load_sentiment_pipeline(model_name = '') -> Pipeline : 
    
    pipe : Pipeline = pipeline('sentiment-analysis')
    
    return pipe

def load_tokenizer(model_name = 'meta-llama/Meta-Llama-3-8B') -> PreTrainedTokenizerFast : 

    tokenizer = AutoTokenizer.from_pretrained(model_name)
    
    return tokenizer

def load_milvus_client() -> MilvusClient: 
    
    db_name = os.getenv('MILVUS_DB_NAME' , 'assets/database/vectordb/demo.db')

    vector_size = int(os.getenv('MILVUS_MODEL_SIZE' , 384))
    collection_name = os.getenv('MILVUS_COLLECTION_NAME' , 'd1')

    milvus_client = MilvusClient(db_name)
    milvus_client.create_collection(collection_name = collection_name , dimension = vector_size)

    return milvus_client

def load_redis_client(db_name : int) -> Redis : 

    redis_client = Redis(
        host = os.getenv('REDIS_HOST' , 'localhost') ,  
        port = int(os.getenv('REDIS_PORT' , 6379)) , 
        db = db_name  , 
        decode_responses = True
    )
    
    return redis_client

def load_embedding_model(model_name = '') -> SentenceTransformer : 
    
    if not model_name : model_name = os.getenv('EMBEDDING_MODEL_NAME' , 'all-MiniLM-L6-v2')
    
    embedding_model = SentenceTransformer(model_name)
    
    return embedding_model

def load_gemini_client() : 
    
    gemini_api_key = os.getenv('GEMINI_API_KEY' , '')
    
    if not gemini_api_key : model = ''
    else : 
        genai.configure(api_key = '<Enter the Gemini API Key here>') # ! Can deploy a Llama 3.2 Model and use that instead, which can increase speed and avoid rate limits and increase safety as well
        model = genai.GenerativeModel(os.getenv('GEMINI_API_KEY' , 'gemini-1.5-flash'))
        
    return model

def load_groq_client() -> Groq : 

    groq_client = Groq()
    # groq_client = ''
    
    return groq_client