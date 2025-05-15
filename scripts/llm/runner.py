from groq import Groq

async def run_groq(messages : list , groq_client : Groq, model = 'llama-3.3-70b-versatile') -> str :

    chat_completion = groq_client.chat.completions.create(
        messages = messages , 
        model = model , 
        response_format = {'type' : 'json_object'}
    )

    return chat_completion.choices[0].message.content