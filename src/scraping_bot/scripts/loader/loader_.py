import os

from transformers.models.auto.tokenization_auto import AutoTokenizer
from transformers.pipelines import pipeline
import yaml

from groq import Groq
from redis import Redis

from fastapi import FastAPI 
from pymilvus import MilvusClient
from sentence_transformers import SentenceTransformer

from logging import (
    Logger , getLogger , 
    StreamHandler , Formatter , 
    DEBUG , INFO , WARNING , ERROR , CRITICAL , 
    LogRecord
)

from google.genai import Client

from transformers.pipelines.base import Pipeline
from fastapi.middleware.cors import CORSMiddleware

from transformers.tokenization_utils_fast import PreTrainedTokenizerFast

def load_sentiment_pipeline(config : dict) -> Pipeline : return pipeline(
    task = config['task'] , 
    model = config['model-name']
)

def load_tokenizer(config : dict) -> PreTrainedTokenizerFast : return AutoTokenizer.from_pretrained(
    pretrained_model_name_or_path = config['model-name'] , 
    token = os.environ['HF_TOKEN']
)

def load_milvus_client(config : dict) -> MilvusClient : 

    client : MilvusClient = MilvusClient(config['db-path'])

    # ! Add logic : if collection exists, do not create collection again

    client.create_collection(
        collection_name = config['collection-name'] , 
        dimension = config['vector-size']
    )

    return client 

def load_redis_client(config : dict) -> Redis : return Redis(
    host = config['host'] , 
    port = config['port'] , 
    db = config['db-name'] , 
    decode_responses = True
)

def load_embedding_model(config : dict) -> SentenceTransformer : return SentenceTransformer(config['model-name'])

def load_gemini_client() -> Client : return Client(api_key=os.environ['GEMINI_API_KEY'])

def load_groq_client() -> Groq : return Groq(api_key = os.environ['GROQ_API_KEY'])

class ColoredFormatter(Formatter) : 

    def __init__(
        self , 
        fmt : str , 
        config : dict , 
        datefmt : str | None = None
    ) -> None :

        super().__init__(fmt , datefmt)
        
        self.COLORS = {
            DEBUG : config['color']['debug'] ,
            INFO : config['color']['info'] , 
            WARNING : config['color']['warning'] , 
            ERROR : config['color']['error'] , 
            CRITICAL : config['color']['critical']
        }

        self.RESET = config['color']['reset']

        self.fmt = fmt

    def format(self , record : LogRecord) -> str : 

        color = self.COLORS.get(record.levelno)

        if color : log_fmt = color + self.fmt + self.RESET
        else : log_fmt = self.fmt

        formatter = Formatter(log_fmt , self.datefmt)

        return formatter.format(record)

def load_logger(config : dict) -> Logger:
    
    logger: Logger = getLogger(__name__)
    logger.setLevel(DEBUG) 

    if logger.handlers : 

        for handler in logger.handlers : logger.removeHandler(handler)

    console_handler = StreamHandler()

    log_format = config['log-format']

    color_config = {
        'color' : {
            key : value.encode().decode('unicode_escape') 
            for key , value in config['color'].items()
        }
    }

    formatter = ColoredFormatter(
        fmt = log_format , 
        config = color_config , 
        datefmt = ''
    )
    console_handler.setFormatter(formatter)

    logger.addHandler(console_handler)

    return logger

def load_fastapi(config : dict) -> FastAPI :  

    app : FastAPI = FastAPI()
    app.add_middleware(
        CORSMiddleware , 
        allow_origins = config['cors']['allowed-origins'] , 
        allow_credentials = config['cors']['allowed-credentials'] , 
        allow_methods = config['cors']['allowed-methods'] , 
        allow_headers = config['cors']['allowed-headers'] , 
    )

    return app

def load_all_clients() -> tuple[
    dict , 
    Pipeline , 
    PreTrainedTokenizerFast , 
    MilvusClient , 
    Redis , Redis , Redis , 
    SentenceTransformer , 
    Client , 
    Groq , 
    FastAPI , 
    Logger
]: 

    with open('config.yml') as config_file : config : dict = yaml.safe_load(config_file)

    sentiment_pipeline : Pipeline = load_sentiment_pipeline(config = config['sentiment'])
    tokenizer : PreTrainedTokenizerFast = load_tokenizer(config = config['tokenizer'])
    milvus_client : MilvusClient = load_milvus_client(config = config['vector-db'])
    chat_redis_client : Redis = load_redis_client(config = config['redis']['chat'])
    db_redis_client : Redis = load_redis_client(config = config['redis']['db'])
    url_redis_client : Redis = load_redis_client(config = config['redis']['url'])
    embedding_model : SentenceTransformer = load_embedding_model(config = config['embedding'])
    gemini_client : Client = load_gemini_client()
    groq_client : Groq = load_groq_client()

    fast_api : FastAPI = load_fastapi(config = config['fast-api'])
    logger : Logger = load_logger(config = config['logger'])

    return (
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
        fast_api , 
        logger
    )