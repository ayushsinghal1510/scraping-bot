import requests
from tqdm import tqdm

from urllib.parse import urljoin

from scripts.scrapper.services import create_soup
from scripts.llm.image import caption_image

async def get_images(soup , url) : 

    img_tags = soup.find_all('img')

    for img_tag in tqdm(img_tags , total = len(img_tags) , desc = 'Saving Images' , leave = False) : 

        img_url = img_tag.get('src')

        if img_url : yield urljoin(url , img_url)

async def image_to_bytes(img_url) : 

    img_response = requests.get(img_url , stream = True)
    img_response.raise_for_status()

    for chunk in img_response.iter_content() : image_bytes += chunk

    return image_bytes

async def page_to_docs(url , image_model , scrape_image = False) : 

    documents = []

    soup = await create_soup(url)

    text_content = soup.get_text(separator = '\n' , strip = True)
    text_chunks = text_content.split(' ')

    text_chunks = [' '.join(text_chunks[index : index + 512]) for index in range(0 , len(text_content) , 512)]

    documents.extend([
        {
            'type' : 'text' , 
            'text' : chunk , 
            'source' : url , 
            'raw_source' : url , 
            'type' : 'url'
        } for chunk in text_chunks
        if chunk
    ])

    if scrape_image : 

        async for img_url in get_images(soup , url) :

            image_bytes = image_to_bytes(img_url)

            response = caption_image(image_bytes , image_model , text_content)

            documents.append(
                {
                    'type' : 'image' , 
                    'text' : response , 
                    'souce' : img_url , 
                    'raw_source' : image_bytes , 
                    'type' : 'image'
                }
            )

    return documents