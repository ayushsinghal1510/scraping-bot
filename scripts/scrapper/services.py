import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from collections import deque

from scripts.services.services import process_link

async def create_soup(url) : 

    response = requests.get(url)
    response.raise_for_status()
    soup = BeautifulSoup(response.content , 'html.parser')

    return soup

async def process_page(url) : 

    soup = await create_soup(url)

    links = soup.find_all('a' , href = True)

    for a_tag in links : 

        href = a_tag['href']

        href = await process_link(href)

        if href : yield href

async def get_pdf_links(base_html) : 

    pdf_links = []
    all_links = set()

    visited_urls = set()
    
    url_queue = deque([base_html])

    visited_urls.add(base_html)

    while url_queue : 

        try : 

            current_url = url_queue.popleft()

            print(current_url , len(url_queue))

            async for link in process_page(current_url) : 

                if link.endswith('pdf') : pdf_links.append(link)
                else :

                    absolute_url = urljoin(current_url , link)

                    if absolute_url.startswith(base_html) : 

                        if absolute_url not in visited_urls : 

                            visited_urls.add(absolute_url)
                            all_links.add(absolute_url)
                            url_queue.append(absolute_url)

        except : pass

    return pdf_links , all_links