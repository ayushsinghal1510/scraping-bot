import requests
import os 
import fitz
import PyPDF2
from tqdm import tqdm
from scripts.llm.image import caption_image

async def download_pdf(pdf_link) : 

    response = requests.get(pdf_link , stream=True)
    response.raise_for_status()

    filename = os.path.basename(pdf_link)

    with open(filename , 'wb') as pdf_file :  # ! Save in folder

        for chunk in response.iter_content(chunk_size = 8192) : pdf_file.write(chunk)

    return filename


async def pdf_to_docs(pdf_link , scrape_image , image_model) : 

    documents = []

    pdf_name = await download_pdf(pdf_link)

    py_pdf_object = PyPDF2.PdfReader(pdf_name)
    fi_pdf_object = fitz.open(pdf_name)

    num_pages = len(py_pdf_object.pages)

    for page_num in tqdm(range(num_pages) , total = num_pages) : 

        page = py_pdf_object.pages[page_num]
        text = page.extract_text()

        text_chunks = [text[index : index + 512] for index in range(0 , len(text) , 512)]

        documents.extend([
            {
                'type' : 'text' , 
                'text' : chunk , 
                'source' : (pdf_link , page_num) , 
                'raw_source' : pdf_link , 
                'type' : 'pdf'
            } for chunk in text_chunks
            if chunk
        ])

        if scrape_image : 

            page = fi_pdf_object.load_page(num_pages)
            images = page.get_images(full = True)

            for image in tqdm(images , total = len(images)) : 

                image = fi_pdf_object.extract_image(image[0])
                image_bytes = image['image'] 

                response = caption_image(image_bytes , image_model , text)

                documents.append(
                    {
                        'type' : 'image' , 
                        'text' : response , 
                        'souce' : pdf_name , 
                        'raw_source' : image_bytes , 
                        'type' : 'image'
                    }
                )

    return documents