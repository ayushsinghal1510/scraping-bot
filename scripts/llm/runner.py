from groq import Groq

async def run_groq(messages : list , groq_client : Groq, model = 'llama-3.3-70b-versatile') -> str :
    
    try : 

        chat_completion = groq_client.chat.completions.create(
            messages = messages , 
            model = model , 
            response_format = {'type' : 'json_object'}
        )

        return chat_completion.choices[0].message.content
    except : return 'Sorry we were not able to process the query for this'
    
import requests


async def run_model(messages : list , client : dict) -> str :

    # url = 'http://35.247.166.243:8080/v1/chat/completions'

    headers = {'Content-Type': 'application/json'}

    payload = {
        'model' : 'tgi' , 
        'messages' : messages , 
        'grammar': {'type' : 'json'}
    }

    response = requests.post(
        client['url'] , 
        headers = headers , 
        json = payload , 
    )

    full_response_content = response.json()['choices'][0]['message']['content']

    return full_response_content

async def img_captionising_tgi(messages : list , client : dict) -> str : 

    raise NotImplementedError('Currently Not Implemeneted')
