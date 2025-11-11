import os 
import json
import base64

from logging import Logger 
from dotenv import load_dotenv

from google.genai import Client 

from google.genai.types import (
    GenerateContentConfig , ThinkingConfig , 
    Part , Content
)

from .llm_ import LLM

from ..services import method_log_timer


class GEMINI(LLM) : 
    '''
    Gemini Model (LLM) Client for text generation and image captioning.
    This class inherits from the LLM base class and provides methods to interact with the Gemini API.
    
    Args : 
        - env_path (str) : Path to the environment file containing Gemini API credentials.
        - config (dict) : Configuration dictionary containing Gemini settings, including model name, thinking budget, system prompt, and response MIME type.
        - logger (Logger) : Logger instance for logging information.
    
    Attributes : 
        - client (Client) : Gemini API client instance.
        - model_name (str) : Name of the Gemini model to use.
        - thinking_budget (int) : Budget for the model's thinking process.
        - system_prompt (str) : System prompt to guide the model's responses.
        - response_mime_type (str) : MIME type for the model's responses.
        - logger (Logger) : Logger instance for logging information.
        
    Methods : 
        - generate_config(thinking_budget : int | None , system_prompt : str | None , response_mime_type : str | None) -> GenerateContentConfig :
            Generates a configuration for content generation.
        - generate_content(generate_content_config : GenerateContentConfig , contents : list , model : str | None) -> str :
            Generates content based on the provided configuration and contents. 
        - captionize_image_bytes(image_bytes : bytes, system_prompt : str , model_name : str | None , mime_type : str) -> str :
            Captions an image provided as bytes.
        - captionize_image_base64(base64_array : str, system_prompt : str , model_name : str | None , mime_type : str) -> str :
            Captions an image provided as a base64 string.
        - captionize_image_str(image_path : str, system_prompt : str , model_name : str | None , mime_type : str) -> str :
            Captions an image provided as a file path.
        - captionize_image(image_bytes : bytes , model_name : str | None , system_prompt : str , mime_type : str) -> str :
            Core method to caption an image provided as bytes.
    '''

    def __init__(
        self , 
        env_path : str , 
        config : dict , 
        logger : Logger 
    ) -> None : 
        
        super().__init__()
        
        load_dotenv(env_path)

        self.client : Client = Client(
            api_key = os.getenv('GEMINI_API_KEY')
        )

        self.model_name : str = config['model-name']
        self.thinking_budget : int = config['thinking-budget']
        self.system_prompt : str = config['system-prompt']
        self.response_mime_type : str = config['response-mime-type']
        self.logger : Logger = logger

        self.base_system_prompt_file : str = config['base-system-prompt-file-path']

        with open(self.base_system_prompt_file) as base_system_prompt_file : self.base_system_prompt : str = base_system_prompt_file.read()

        
        self.logger.info(f'Initialized Gemini LLM Client with config {json.dumps(config , indent = 4)}')

    @method_log_timer
    async def generate_config(
        self , 
        thinking_budget : int | None = None , 
        system_prompt : str | None = None , 
        response_mime_type : str | None = None
    ) -> GenerateContentConfig :
        '''
        Generates a configuration for content generation.
        
        Parameters :
            - thinking_budget (int | None) : Budget for the model's thinking process. Defaults to instance's thinking_budget.
            - system_prompt (str | None) : System prompt to guide the model's responses. Defaults to instance's system_prompt.
            - response_mime_type (str | None) : MIME type for the model's responses. Defaults to instance's response_mime_type.
            
        Returns :
            - GenerateContentConfig : Configuration object for content generation.
        '''

        thinking_config : ThinkingConfig = ThinkingConfig(
            thinking_budget = thinking_budget if thinking_budget else self.thinking_budget
        )

        system_prompt_config : list = [
            Part.from_text(
                text = system_prompt if system_prompt else self.system_prompt
            )
        ] 

        generate_content_config : GenerateContentConfig = GenerateContentConfig(
            thinking_config = thinking_config , 
            response_mime_type = response_mime_type if response_mime_type else self.response_mime_type , 
            system_instruction = system_prompt_config
        )

        return generate_content_config

    @method_log_timer
    async def generate_content(
        self , 
        generate_content_config : GenerateContentConfig , 
        contents : list , 
        model : str | None = None , 
    ) -> str : 
        '''
        Generates content based on the provided configuration and contents.
        
        Parameters :
            - generate_content_config (GenerateContentConfig) : Configuration for content generation.
            - contents (list) : List of Content objects to be processed by the model.
            - model (str | None) : Name of the model to use. Defaults to instance's model_name.
            
        Returns :
            - str : Generated content as a string.
        '''

        response : str = ''

        print(model)

        for chunk in self.client.models.generate_content_stream(
            model = model if model else self.model_name , 
            contents = contents , 
            config = generate_content_config
        ) : 

            if chunk.text : response += chunk.text

        return response
    
    @method_log_timer
    async def captionize_image_bytes(
        self , 
        image_bytes : bytes, 
        system_prompt : str = '' , 
        model_name : str | None = None , 
        mime_type : str = 'image/png'
    ) -> str : 
        '''
        Captions an image provided as bytes.
        
        Parameters :
            - image_bytes (bytes) : Image data in bytes.
            - system_prompt (str) : System prompt to guide the model's responses.
            - model_name (str | None) : Name of the model to use. Defaults to instance's model_name.
            - mime_type (str) : MIME type of the image. Defaults to 'image/png'.
            
        Returns :
            - str : Generated caption for the image.
        '''

        response : str = await self.captionize_image(
            image_bytes = image_bytes , 
            system_prompt = system_prompt , 
            model_name = model_name , 
            mime_type = mime_type
        )
        
        return response
    
    @method_log_timer
    async def captionize_image_base64(
        self , 
        base64_array : str, 
        system_prompt : str = '' , 
        model_name : str | None = None , 
        mime_type : str = 'image/png'
    ) -> str : 
        '''
        Captions an image provided as a base64 string.
        
        Parameters :
            - base64_array (str) : Image data in base64 string format.
            - system_prompt (str) : System prompt to guide the model's responses.
            - model_name (str | None) : Name of the model to use. Defaults to instance's model_name.
            - mime_type (str) : MIME type of the image. Defaults to 'image/png'.
            
        Returns : 
            - str : Generated caption for the image.
        '''
        
        image_bytes : bytes = base64.b64decode(base64_array)
        
        response : str = await self.captionize_image(
            image_bytes = image_bytes , 
            system_prompt = system_prompt , 
            model_name = model_name , 
            mime_type = mime_type
        )
        
        return response

    @method_log_timer
    async def captionize_image_str(
        self , 
        image_path : bytes, 
        system_prompt : str = '' , 
        model_name : str | None = None , 
        mime_type : str = 'image/png'
    ) -> str : 
        '''
        Captions an image provided as a file path.
        
        Parameters :
            - image_path (str) : Path to the image file.
            - system_prompt (str) : System prompt to guide the model's responses.
            - model_name (str | None) : Name of the model to use. Defaults to instance's model_name.
            - mime_type (str) : MIME type of the image. Defaults to 'image/png'.
            
        Returns :
            - str : Generated caption for the image.
        '''

        with open(image_path , 'rb') as image_file : image_bytes : bytes = image_file.read()
        
        response : str = await self.captionize_image(
            image_bytes = image_bytes , 
            system_prompt = system_prompt , 
            model_name = model_name , 
            mime_type = mime_type
        )

        return response 

    @method_log_timer
    async def captionize_image(
        self , 
        image_bytes : bytes , 
        model_name : str | None = None , 
        system_prompt : str = '' , 
        mime_type : str = 'image/png'
    ) -> str : 
        '''
        Core method to caption an image provided as bytes.
        
        Parameters :
            - image_bytes (bytes) : Image data in bytes.
            - model_name (str | None) : Name of the model to use. Defaults to instance's model_name.
            - system_prompt (str) : System prompt to guide the model's responses.
            - mime_type (str) : MIME type of the image. Defaults to 'image/png'.
            
        Returns :
            - str : Generated caption for the image.
        '''
        
        generate_content_config : GenerateContentConfig = await self.generate_config(
            system_prompt = system_prompt
        )

        contents = [
            Content(
                role = 'user' , 
                parts = [
                    Part.from_bytes(
                        mime_type = mime_type , 
                        data = image_bytes , 
                    )
                ]
            )
        ]
        
        response : str = await self.generate_content(
            generate_content_config = generate_content_config , 
            contents = contents , 
            model = model_name
        )
        
        return response