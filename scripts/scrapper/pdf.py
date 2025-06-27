import requests
import os 
import fitz
import PyPDF2
from tqdm import tqdm
from scripts.llm.image import caption_image

async def download_pdf(pdf_link : str) -> str | None : 

    try : 

        response = requests.get(pdf_link , stream=True)

        filename = os.path.basename(pdf_link)
        filename = f'assets/pdfs/{filename}'

        with open(filename , 'wb') as pdf_file :  # ! Save in folder

            for chunk in response.iter_content(chunk_size = 8192) : pdf_file.write(chunk)

        return filename
    
    except : return None


async def pdf_to_docs(pdf_link : str , scrape_image : bool , gemini_client) -> list | None : 

    documents = []

    pdf_name : str | None  = await download_pdf(pdf_link)
    
    if pdf_name : 

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
                    image_bytes : bytes = image['image'] 

                    response : str = caption_image(image_bytes , gemini_client , text)

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
    
    return None 

async def pdf_file_to_docs(pdf_name : str) : 

    documents = []

    py_pdf_object = PyPDF2.PdfReader(pdf_name)

    num_pages = len(py_pdf_object.pages)

    for page_num in tqdm(range(num_pages) , total = num_pages) : 

        page = py_pdf_object.pages[page_num]
        text = page.extract_text()

        text_chunks = [text[index : index + 512] for index in range(0 , len(text) , 512)]

        documents.extend([
            {
                'type' : 'text' , 
                'text' : chunk , 
                'source' : (pdf_name , page_num) , 
                'raw_source' : pdf_name , 
                'type' : 'pdf'
            } for chunk in text_chunks
            if chunk
        ])


    return documents