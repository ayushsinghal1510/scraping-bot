import ast 
import json
from requests import Response 
import requests

from google.genai.types import Part , Content

class LLM : 
    '''
    Base class for Language Model (LLM) services.

    This class provides methods to create messages for LLM requests and to post-process responses
    from the LLM. It is designed to be extended by specific LLM implementations such as Azure OpenAI or Groq.

    Methods:
        - create_messages(system_prompt: str, user_input: str) -> list[dict[str, str]]:
            Creates a list of messages formatted for LLM requests, including system and user prompts.
        - postprocess_response(response: str, dict_converter: str) -> dict:
            Post-processes the LLM response based on the specified dictionary converter type.
        - postprocess_response_ast(response: str) -> dict:
            Post-processes the LLM response using the AST literal evaluation method.
        - postprocess_response_json(response: str) -> dict:
            Post-processes the LLM response using the JSON parsing method.
    
    Attributes: 
        - None

    Args : 
        - None
    '''

    def __init__(self) : 

        pass

    async def create_messages(
        self , 
        system_prompt : str , 
        user_input : str
    ) -> list[dict[str , str]] : 
        '''
        Create messages for LLM requests.

        Args:
            - system_prompt (str): The system prompt to be included in the messages.
            - user_input (str): The user input to be included in the messages.

        Returns:
            - list[dict[str, str]]: A list of messages formatted for LLM requests.
        '''

        messages : list[dict[str , str]] = [
            {
                'role' : 'system' , 
                'content' : system_prompt
            } , 
            {
                'role' : 'user' , 
                'content' : user_input
            }
        ]

        return messages

    async def postprocess_response(self , response : str , dict_converter : str) -> dict :
        '''
        Post-process the LLM response based on the specified dictionary converter type.

        Args:

            - response (str): The raw response from the LLM.
            - dict_converter (str): The type of dictionary converter to use ('ast' or 'json').

        Returns:
            - dict: The processed response as a dictionary.

        Raises:
            - ValueError: If an unsupported dict_converter is provided.
        '''

        if dict_converter == 'ast' : return await self.postprocess_response_ast(response)

        elif dict_converter == 'json' : return await self.postprocess_response_json(response)

        else : 

            raise ValueError(f"Unsupported dict_converter: {dict_converter}")

    async def postprocess_response_ast(self , response : str) -> dict : 
        '''
        Post-process the LLM response using the AST literal evaluation method.

        Args:
            - response (str): The raw response from the LLM.

        Returns:
            - dict: The processed response as a dictionary.
        '''

        processed_response : str = response.replace('json' , '').replace('`' , '')

        json_response : dict = ast.literal_eval(processed_response)

        return json_response

    async def postprocess_response_json(self , response : str) -> dict : 
        '''
        Post-process the LLM response using the JSON parsing method.

        Args:
            - response (str): The raw response from the LLM.

        Returns:
            - dict: The processed response as a dictionary.
        '''

        processed_response : str = response.replace('json' , '').replace('`' , '')

        json_response : dict = json.loads(processed_response)

        return json_response
    
    async def image_to_bytes(self , img_url : str) -> bytes : 
        '''
        Convert an image URL to bytes.
        
        Args : 
            - img_url (str): The URL of the image to be converted.
            
        Returns : 
            - bytes: The image data in bytes.
        '''
        
        image_bytes : bytes = bytes()

        img_response : Response = requests.get(img_url , stream = True)
        img_response.raise_for_status()

        for chunk in img_response.iter_content() : image_bytes += chunk

        return image_bytes

    async def json_to_google_chat(self , chat : list) -> list : 
        '''
        Converts a typical Chat history to Google kind of chat history 
        
        Arguments 
        - chat : chat history
        should be like this 
        
        [
            {
                'role' : 'user' , 
                'content' : <user_query>
            } , 
            {
                'role' : 'assistant' , 
                'content' : <assistant_response>
            }
            .continues with user -> assistant
        ]
        ''' 

        contents = []

        for row in chat : 

            role : str = row['role']

            if role == 'user' : contents.append(
                Content(
                    role = 'user' , 
                    parts = [Part.from_text(text = str(row['content']))]
                )
            )

            else : contents.append(
                Content(
                    role = 'model' , 
                    parts = [Part.from_text(text = str(row['content']))]
                )
            )

        return contents