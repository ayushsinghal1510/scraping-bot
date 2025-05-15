import io 
from PIL import Image

def caption_image(image_bytes : bytes , image_model , surrounding_text : str ) -> str : 

    with open('assets/database/prompt/image_ingestion.md') as image_ingestion_prompt_file : prompt = image_ingestion_prompt_file.read().format(surrounding_text)

    image = Image.open(io.BytesIO(image_bytes))

    response = image_model.generate_content([image , prompt])
    response : str = response.text

    return response

