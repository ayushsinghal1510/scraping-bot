import os 
import json

from groq import Groq 
from typing import Tuple
from logging import Logger
from dotenv import load_dotenv

from .llm_ import LLM

from ..services import method_log_timer

load_dotenv()

class GROQ(LLM) : 
    '''
    A class to interact with Groq's LLM service.

    This class extends the base LLM class and provides methods to run models, handle message history, and process responses.

    Attributes:
        - client (Groq): The Groq client for making API requests.
        - model (str): The name of the model to be used for inference.
        - dict_converter (str): The type of dictionary converter to be used for post-processing responses.
        - logger (Logger) : Logger instance for logging information.
        

    Args:
        - env_path (str): Path to the environment file containing Groq API credentials.
        - config (dict): Configuration dictionary containing Groq settings, including model name.
        - logger (Logger) : Logger instance for logging information.
        
    Methods:
        - run_model(messages: list, model: str | None = None) -> str:
            Runs the specified model with the provided messages and returns the response as a string.
        - run_model_json(messages: list, model: str | None = None, dict_converter: str | None = None) -> dict:
            Runs the specified model with the provided messages and returns the response as a JSON object.
        - run_model_history(query: str, history: list, model: str | None = None) -> Tuple[str, list]:
            Runs the model with the provided query and history, updating the history with the response.
        - run_model_history_json(query: str, history: list, model: str | None = None) -> Tuple[dict, list]:
            Runs the model with the provided query and history, returning the response as a JSON object and updating the history.
        - __call__(messages: list, model: str | None = None) -> str:
            Calls the run_model method with the provided messages and returns the response as a string.
    '''

    def __init__(self , env_path : str , config : dict , logger : Logger) -> None : 

        super().__init__()

        load_dotenv(env_path)
        self.config = config

        self.client : Groq = Groq(api_key = os.getenv('GROQ_API_KEY'))

        self.model = config['model-name']
        self.dict_converter = config['preprocess']['dict-converter']
        self.base_system_prompt_file : str = config['base-system-prompt-file-path']

        with open(self.base_system_prompt_file) as base_system_prompt_file : self.base_system_prompt : str = base_system_prompt_file.read()

        self.logger = logger

        print(f'Groq LLM initialized with config : {json.dumps(config , indent = 4)}')

    @method_log_timer
    async def run_model(
        self , 
        messages : list , 
        model : str | None = None
    ) -> str :
        '''
        Runs the specified model with the provided messages and returns the response as a string.

        Args:
            - messages (list): A list of messages to be sent to the model.
            - model (str | None): The name of the model to be used. If None, uses the default model.

        Returns:
            - str: The content of the model's response.
        
        Raises:
            - Exception: If there is an error in processing the response.
        '''

        chat_completion = self.client.chat.completions.create(
            messages = messages , 
            model = model if model else self.model
        )

        if chat_completion.choices[0].message.content : return chat_completion.choices[0].message.content
        else : self.logger.warning(f'No message from OpenAI sending empty responses') ; return ''

    @method_log_timer
    async def run_model_json(
        self , 
        messages : list , 
        model : str | None = None , 
        dict_converter : str | None = None
    ) -> dict :
        '''
        Runs the specified model with the provided messages and returns the response as a JSON object.

        Args:
            - messages (list): A list of messages to be sent to the model.
            - model (str | None): The name of the model to be used. If None, uses the default model.
            - dict_converter (str | None): The type of dictionary converter to be used for post-processing. If None, uses the default converter.

        Returns:
            - dict: The processed response from the model as a JSON object.

        Raises:
            - Exception: If there is an error processing the response.
        '''

        chat_completion = self.client.chat.completions.create(
            messages = messages , 
            model = model if model else self.model , 
            response_format = {'type' : 'json_object'}
        )

        if chat_completion.choices[0].message.content : 

            try : json_response : dict = await self.postprocess_response(
                chat_completion.choices[0].message.content , 
                dict_converter = dict_converter if dict_converter else self.dict_converter
            )
            except Exception as e : self.logger.error(f'Invalid JSON found {chat_completion.choices[0].message.content} , sending empty json') ; json_response = {}

        else : self.logger.warning(f'No message receieved from OpenAI, sending empty json') ; json_response = {}

        return json_response

    @method_log_timer
    async def __call__(
        self , 
        messages : list , 
        model : str | None = None
    ) -> str : 
        '''
        Calls the run_model method with the provided messages and returns the response as a string.

        Args:
            - messages (list): A list of messages to be sent to the model.
            - model (str | None): The name of the model to be used. If None, uses the default model.

        Returns:
            - str: The content of the model's response.
        '''

        response : str = await self.run_model(
            messages = messages , 
            model = model
        )

        return response