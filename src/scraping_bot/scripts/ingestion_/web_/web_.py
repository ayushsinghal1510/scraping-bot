import re
import requests 

from tqdm import tqdm
from collections import deque
from requests import Response
from pymilvus import MilvusClient

from bs4 import BeautifulSoup , Tag

from urllib.parse import urljoin
from bs4._typing import _QueryResults
from unstructured.documents.elements import Element
from unstructured.partition.html import partition_html

from ..ingestion_ import INGESTION
from .sitemap_ import SitemapExtractor
from ..document_ import Document

class WEB(INGESTION) : 

    def __init__(
        self , 
        milvus_client : MilvusClient , 
        url : str , 
        collection_name : str , 
        config : dict , 
        embedding_client
    ) -> None : 

        super().__init__(
            milvus_client = milvus_client , 
            collection_name = collection_name , 
            config = config 
        )

        self.url : str = url
        self.collection_name : str = collection_name 
        self.config : dict = config 
        self.embedding_client = embedding_client

        self.chunks : list[dict[str , str]] = []

    def extract_sitemap(self) -> list | None : 

        self.sitemap_url : str = f'{self.url}/sitemap.xml'

        if requests.get(self.sitemap_url).status_code == 200 : sitemap_extractor = SitemapExtractor(
            url = self.sitemap_url , 
            config = self.config['sitemap']
        )

        else : 

            self.sitemap_url = f'{self.url}/sitemap_index.xml'

            if requests.get(self.sitemap_url).status_code == 200 : sitemap_extractor = SitemapExtractor(
                url = self.sitemap_url , 
                config = self.config['sitemap']
            )

            else : 

                _ , all_links = self.get_all_links(base_html = self.url)

                self.indexed_urls = [{'loc' : link} for link in all_links]

                return self.indexed_urls

        self.indexed_urls = sitemap_extractor()

        return self.indexed_urls

    def extract_custom_sitemap(self) -> dict : 

        self.sitemap_url : str = f'{self.url}/sitemap.xml'

        if requests.get(self.sitemap_url).status_code == 200 : sitemap_extractor = SitemapExtractor(
            url = self.sitemap_url , 
            config = self.config['sitemap']
        )

        else : 

            self.sitemap_url = f'{self.url}/sitemap_index.xml'

            if requests.get(self.sitemap_url).status_code == 200 : sitemap_extractor = SitemapExtractor(
                url = self.sitemap_url , 
                config = self.config['sitemap']
            )

            else : 

                pdf_links , all_links = self.get_all_links(base_html = self.url)

                return {
                    'pdf_links' : pdf_links , 
                    'html_links' : all_links
                }

        self.indexed_urls : list = sitemap_extractor()

        return self.indexed_urls

    def process_link(self , href : str) -> str | None : 
        
        for element in self.config['link-exclusions'] : 
            if element in href : return None

        return href

    def process_page(self , url : str) : 
        '''
        Processes a single page to extract all valid links. 
        
        Args :
            - url (str) : The URL of the web page to process.
            
        Yields : 
            - str : Valid links found on the page.
        '''

        soup : BeautifulSoup = self.create_soup(url)

        links : _QueryResults = soup.find_all('a' , href = True)

        for a_tag in links : 

            href : str= a_tag['href']

            proc_href : str | None = self.process_link(href = href)

            if proc_href : yield proc_href

    def create_soup(self , url : str) -> BeautifulSoup : 
        '''
        Creates a BeautifulSoup object from the content of the given URL. 
        
        Args : 
            - url (str) : The URL of the web page to scrape. 
            
        Returns : 
            - BeautifulSoup : A BeautifulSoup object representing the parsed HTML content of the page.
        '''

        response : Response = requests.get(url)
        response.raise_for_status()
        soup : BeautifulSoup = BeautifulSoup(
            markup = response.content , 
            features = 'html.parser'
        )

        return soup

    def get_all_links(self , base_html : str) : 
        '''
        Extracts all PDF links from the given base HTML page.
        
        Args : 
            - base_html (str) : The base HTML page URL to start scraping from.

        Returns :   
            - tuple[set[str] , set[str]] : A tuple containing a set of PDF links and a set of all visited links.
        '''

        pdf_links : set[str] = set()
        all_links : set[str] = set()

        all_links.add(base_html)

        visited_urls : set[str] = set()

        url_queue : deque = deque([base_html])

        visited_urls.add(base_html)

        while url_queue : 

            try : 

                current_url : str = url_queue.popleft()

                print(current_url , len(url_queue))

                for link in self.process_page(current_url) : 

                    if link.endswith('pdf') : 

                        if not link.startswith('http') : link : str = f'{base_html}{link}'
                        
                        pdf_links.add(link)

                    else :

                        absolute_url : str = urljoin(current_url , link)

                        if absolute_url.startswith(base_html) : 

                            if absolute_url not in visited_urls : 

                                visited_urls.add(absolute_url)
                                all_links.add(absolute_url)
                                url_queue.append(absolute_url)

            except : pass

        return pdf_links , all_links

    def extract_text_from_url(
        self , 
        url  : str , 
        chunk_length : int , 
        tags : list = ['h1' , 'h2' , 'h3' , 'h4' , 'h5' , 'h6']
    ) -> dict : 
        '''
        Extracts text content from the given URL and splits it into chunks of specified length. 
        
        Args : 
            - url (str) : The URL of the web page to extract text from.
            - chunk_length (int) : The number of words per chunk.
            
        Returns : 
        '''
        
        soup : BeautifulSoup = self.create_soup(url)
        structured_content : dict = {}
        all_headings : list = soup.find_all(tags)
        
        for heading in all_headings : 

            key = heading.get_text(strip = True).lower()
            key = re.sub(r'\s+' , '-' , key)
            key = re.sub(r'[^a-z0-9-]' , '' , key)

            content_parts = []

            for sibling in heading.find_next_siblings():

                if sibling.name in tags : break
                
                if isinstance(sibling , Tag) : content_parts.append(sibling.get_text(separator = ' ' , strip = True))

            full_text = ' '.join(content_parts)
            
            if full_text.strip() : 

                words = full_text.split()

                text_chunks = [' '.join(words[index : index + chunk_length]) for index in range(0 , len(words) , chunk_length)]
                
                if key in structured_content : structured_content[key].extend(text_chunks)
                else : structured_content[key] = text_chunks

        return structured_content

    def create_direct_chunks_and_add_to_vectordb(
        self
    ) -> int : 

        partitioned_elements : list[Element] = partition_html(url = self.url)
        narrative_elements : list[Element] = [element for element in partitioned_elements if element.category in ["NarrativeText", "ListItem" , 'Element' , 'Title']]

        for element in tqdm(
            narrative_elements , 
            total = len(narrative_elements) , 
            leave = False
        ) : 

            dict_element : dict = element.to_dict()
            element_text : str = dict_element['text']

            words : list[str] = element_text.split()

            if len(words) <= self.config['min-word-count'] : continue

            self.chunks.extend(
                [
                    Document(
                        text = ' '.join(words[index : index + self.chunk_size]) , 
                        url = str(url) , 
                        base_url = str(self.url) , 
                        type_ = 'web'
                    ).to_dict()
                ]
                for index in range(0 , len(words) , self.chunk_size)
            )

            self.add_to_vectordb(
                embedding_client = self.embedding_client , 
                documents = self.chunks
            )

            return len(self.chunks)

    def create_chunks_and_add_to_vectordb(
        self , 
        chunk_size : int | None = None 
    ) -> int : 

        self.extract_sitemap()

        self.chunk_size = chunk_size if chunk_size else self.config['chunk-size']
        
        for url in tqdm(self.indexed_urls , total = len(self.indexed_urls)) : 

            try : 

                loc : str = url['loc']

                partitioned_elements : list[Element] = partition_html(url = loc)
                narrative_elements : list[Element] = [element for element in partitioned_elements if element.category in ["NarrativeText", "ListItem" , 'Element' , 'Title']]

                for element in tqdm(
                    narrative_elements , 
                    total = len(narrative_elements) , 
                    leave = False
                ) : 

                    dict_element : dict = element.to_dict()
                    element_text : str = dict_element['text']

                    words : list[str] = element_text.split()

                    if len(words) <= self.config['min-word-count'] : continue

                    self.chunks.extend(
                        [
                            Document(
                                text = ' '.join(words[index : index + self.chunk_size]) , 
                                url = str(url) , 
                                base_url = str(self.url) , 
                                type_ = 'web'
                            ).to_dict()
                        ]
                        for index in range(0 , len(words) , self.chunk_size)
                    )

            except Exception as e : print(f'Error processing {url}: {e}') ; continue

        self.add_to_vectordb(
            embedding_client = self.embedding_client , 
            documents = self.chunks
        )

        return len(self.chunks)

    def create_chunks_navigation_and_to_vectordb(
        self , 
        chunk_size : int | None = None
    ) : 

        self.extract_sitemap()

        self.chunk_size : int = chunk_size if chunk_size else self.config['chunk-size']

        for url in tqdm(self.indexed_urls , total = len(self.indexed_urls)) : 

            try : 

                loc : str = url['loc']

                structured_content : dict = self.extract_text_from_url(
                    url = loc , 
                    chunk_length = self.chunk_size
                )

                for key , value in zip(structured_content.keys() , structured_content.values()) : 

                    if len(value) <= self.config['min_word_count'] : continue

                    for val in value : self.chunks.append(
                        Document(
                            url = self.url , 
                            text = val , 
                            type_ = 'web'
                        ).to_dict()
                    )

            except Exception as e : print(f'Error processing {url}: {e}') ; continue

        self.add_to_vectordb(
            embedding_client = self.embedding_client , 
            documents = self.chunks
        )

        return len(self.chunks)

    def __call__(
        self , 
        chunk_size : int | None = None , 
        type_ = 'normal' 
    ) -> int : 
    
        if type_ == 'normal' : return self.create_chunks_and_add_to_vectordb(chunk_size = chunk_size)
        else : return self.create_chunks_navigation_and_to_vectordb(chunk_size = chunk_size)