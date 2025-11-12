import json

from ddgs import DDGS
from tqdm import tqdm
from io import BytesIO
from redis import Redis
from numpy import ndarray
from pymilvus import MilvusClient
from sentence_transformers import SentenceTransformer

from datetime import datetime , timezone

from redis.typing import ResponseT
from urllib.request import urlopen

from unstructured.partition.html import partition_html
from unstructured.partition.pdf import partition_pdf
from unstructured.documents.elements import Element

from urllib.request import Request as urlRequest

from ..llm import GROQ

class INFERENCE : 

    def __init__(
        self , 
        milvus_client : MilvusClient , 
        chat_redis_client : Redis , 
        embedding_model : SentenceTransformer ,
        config : dict , 
        groq_client : GROQ 
    ) -> None : 

        self.milvus_client : MilvusClient = milvus_client
        self.chat_redis_client : Redis = chat_redis_client
        self.embedding_model : SentenceTransformer = embedding_model

        self.groq_client : GROQ = groq_client

        self.config : dict = config 
        self.search_client : DDGS = DDGS()

        with open(self.config['system-prompt-path']) as system_prompt_file : self.system_prompt : str = system_prompt_file.read()

    def get_history(
        self , 
        session_id : str
    ) -> list[dict[str , str]] : 

        stringified_json_history : ResponseT | str | None = self.chat_redis_client.get(session_id)

        if isinstance(stringified_json_history , str) : return json.loads(stringified_json_history)
        else : return []

    def save_history(
        self , 
        session_id : str , 
        value : list[dict[str , str]]
    ) -> None : 

        self.chat_redis_client.set(
            name = session_id , 
            value = json.dumps(value)
        )

    async def expand_query(
        self , 
        query : str 
    ) -> str : 

        # ! make it file 

        prompt : str = f'''
            You are a linguistic normalization engine for web queries.
            Expand the query to include synonyms, morphological variants, prepositional changes, 
            active/passive alternations, and pragmatic paraphrases while keeping domain focus (ISRO, space, satellites, missions).
            Always return a single line query that contains all the variants
        '''

        response : str = await self.groq_client(
            messages = await self.groq_client.create_messages(
                system_prompt = prompt , 
                user_input = f'Query : {query}' , 
            )
        )

        return response

    async def extract_text_from_url_and_create_chunks(
        self , 
        url : str
    ) -> str : 

        partitioned_elements : list[Element] = partition_html(url = url)
        narrative_elements : list[Element] = [element for element in partitioned_elements if element.category in ["NarrativeText", "ListItem" , 'Element' , 'Title']]

        sentence : str = ''

        for element in tqdm(
            iterable = narrative_elements , 
            total = len(narrative_elements) , 
            leave = False
        ) : 

            dict_element : dict = element.to_dict()
            element_text : str = dict_element['text']

            words : list[str] = element_text.split()

            sentence += ' '.join(words)

        return sentence

    async def extract_text_from_pdf_and_create_chunks(
        self , 
        pdf_url : str
    ) -> str : 

        req = urlRequest(pdf_url , headers = {'User-Agent' : 'Mozilla/5.0'})

        with urlopen(req) as response: pdf_bytes : bytes = response.read()

        partitioned_elements : list[Element] = partition_pdf(file = BytesIO(pdf_bytes))
        narrative_elements : list[Element] = [element for element in partitioned_elements if element.category in ["NarrativeText", "ListItem" , 'Element' , 'Title']]

        sentence : str = ''

        for element in tqdm(
            iterable = narrative_elements , 
            total = len(narrative_elements) , 
            leave = False
        ) : 

            dict_element : dict = element.to_dict()
            element_text : str = dict_element['text']

            words : list[str] = element_text.split()

            sentence += ' '.join(words)

        return sentence

    async def get_web_search_results(
        self , 
        query : str 
    ) -> str : 

        expanded_query : str = await self.expand_query(query = query)

        results = [result for result in self.search_client.text(
            expanded_query , 
            max_results = self.config['search-top-k']
        )]

        print(results)

        page_infos : list[dict] = []

        for item in results[:self.config['search-top-k']] : 

            url = item.get('url') or item.get('link')

            if (
                url 
                # any(d in url for d in self.config['allowed-domains'])
            ) : 

                text , last_modified_data = '' , None

                if url.lower().endswith('.pdf') : text = await self.extract_text_from_pdf_and_create_chunks(pdf_url = url)
                else : text = await self.extract_text_from_url_and_create_chunks(url = url)

                page_infos.append({
                    'url' : url , 
                    'text' : text , 
                    'last_modified' : last_modified_data or datetime.now(timezone.utc) # ! isint this a lot misleading ?
                })

        sorted_pages = sorted(page_infos , key = lambda x : x["last_modified"])

        print(f'Sorted Pages ---------> : {sorted_pages}')

        search_results : str = ''

        for index , page in enumerate(sorted_pages , start = 1) : 

            date_str : str = page['last_modified'].strftime('%Y-%m-%d')

            search_results += f'[SRC{index}] (Published: {date_str})\n{page["text"]}\n'

        return search_results

    async def get_vectordb_results(
        self , 
        query : str
    ) -> str : 

        query_embeddings : ndarray = self.embedding_model.encode(
            sentences = query , 
            convert_to_numpy = True , 
            normalize_embeddings = True
        )

        results : list[dict] = self.milvus_client.search(
            collection_name = 'd2' , 
            data = [query_embeddings] , 
            limit = self.config['vector-top-k'] , 
            output_fields = ["id", "vector", "text", "source", "score"] , 
        )[0]

        text : str = ' '.join(row['entity']['text'] for row in results)

        return text

    async def forward(
        self , 
        query : str , 
        session_id : str
    ) -> dict : 

        history : list[dict[str , str]] = self.get_history(session_id = session_id)

        if history == [] : history = [
            {
                'role' : 'system' , 
                'content' : self.system_prompt
            }
        ]

        web_search_results : str = await self.get_web_search_results(query = query)

        print(f'-------------> : {web_search_results}')
        vectordb_results : str = await self.get_vectordb_results(query = query)

        print(f'-------------> VectorDB Results : {vectordb_results}')

        history.append(
            {
                'role' : 'user' , 
                'content' : f'''
                Web Search Results : {web_search_results}

                Contextual Results : {vectordb_results}

                Query : {query}
                '''
            }
        )

        response : dict = await self.groq_client.run_model_json(messages = history)

        history.append(
            {
                'role' : 'assistant' , 
                'content' : str(response)
            }
        )

        self.save_history(
            session_id = session_id , 
            value = history
        )

        return response

    async def __call__(
        self , 
        query : str , 
        session_id : str
    ) -> dict : 

        return await self.forward(
            query = query , 
            session_id = session_id
        )