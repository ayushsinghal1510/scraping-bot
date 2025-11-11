import json
from pymilvus import MilvusClient
from redis import Redis
from redis.typing import ResponseT

from ..llm import GROQ

class INFERENCE : 

    def __init__(
        self , 
        milvus_client : MilvusClient , 
        chat_redis_client : Redis , 
        config : dict , 
        groq_client : GROQ 
    ) -> None : 

        self.milvus_client : MilvusClient = milvus_client
        self.chat_redis_client : Redis = chat_redis_client

        self.groq_client : GROQ = groq_client

        self.config : dict = config 

        with open(self.config['system-prompt-path']) as system_prompt_file : self.system_prompt : str = system_prompt_file.read()

    def get_history(
        self , 
        session_id : str
    ) -> list[dict[str , str]] : 

        stringified_json_history : ResponseT | str | None = self.chat_redis_client.get(session_id)

        if isinstance(stringified_json_history , str) : return json.loads(stringified_json_history)
        else : return []

    async def expand_query(
        self , 
        query : str 
    ) -> str : 

        # ! make it file 

        prompt : str = f'''
            You are a linguistic normalization engine for web queries.
            Expand the query to include synonyms, morphological variants, prepositional changes, 
            active/passive alternations, and pragmatic paraphrases while keeping domain focus (ISRO, space, satellites, missions).
        '''

        response : str = await self.groq_client(
            messages = await self.groq_client.create_messages(
                system_prompt = prompt , 
                user_input = f'Query : {query}' , 
            )
        )

        return response

    async def forward(
        self , 
        query : str , 
        session_id : str
    ) : 

        history : list[dict[str , str]] = self.get_history(session_id = session_id)

        if history == [] : history = [
            {
                'role' : 'system' , 
                'content' : self.system_prompt
            }
        ]

        expanded_query : str = await self.expand_query(query = query)

