import yaml 
import requests

import xml.etree.ElementTree as ET

from tqdm import tqdm
from requests import Session , Response

from xml.etree.ElementTree import Element 

with open('config.yml') as config_file : config : dict = yaml.safe_load(config_file)

class SitemapExtractor : 

    def __init__(
        self , 
        url : str , 
        config : dict 
    ) : 

        self.url : str = url 
        self.config : dict = config 

        self.sitemap_data = []
        self.session : Session = Session()
        self.session.headers.update(config['session-headers'])

        self.root_namespaces : dict = self.config['namespaces']['general']
        self.index_namespaces : dict = self.config['namespaces']['index']
    
    def fetch_sitemap(self , url : str) -> str | None : 

        try : 

            response : Response = self.session.get(
                url = url , 
                timeout = 30
            )

            response.raise_for_status()

            return response.text

        except requests.RequestException as e : print(f"Error fetching sitemap from {url}: {e}") ; return None

    def find_element(
        self , 
        element : str , 
        sitemap , 
        namespaces : dict
    ) -> str | None : 

        value = sitemap.find(element , namespaces) 

        return value.text.strip() if (value is not None and value.text) else None

    def parse_sitemap_index(self, xml_content : str) -> list[str]:

        sitemap_urls = []

        try : 

            root = ET.fromstring(xml_content)
            
            for sitemap in root.findall('.//sitemap:sitemap' , self.index_namespaces) : 

                loc : str | None = self.find_element(
                    element = 'sitemap:loc' , 
                    sitemap = sitemap , 
                    namespaces = self.index_namespaces
                )

                # print(loc)

                sitemap_urls.append(loc) if loc else None

            return sitemap_urls

        except ET.ParseError as e : print(f"Error parsing sitemap index: {e}") ; return []

    def find_basic_entries_and_add_to_dict(
        self , 
        url , 
        url_data 
    ) -> dict : 

        basic_entries = [
            'loc' , 
            'lastmod' , 
            'changefreq' , 
            'priority'
        ]

        for entry in basic_entries : 

            value : str | None = self.find_element(
                element = f'sitemap:{entry}' , 
                sitemap = url , 
                namespaces = self.root_namespaces
            )

            url_data[entry] = value if value else None 

        return url_data

    def find_image_entries_and_add_to_dict(
        self , 
        url , 
        url_data 
    ) -> dict : 

        images = url.findall('image:image' , self.root_namespaces)

        if images : 

            url_data['images'] = []

            for img in images:

                img_data = {}

                image_entries = [
                    'loc' , 
                    'title' , 
                    'caption'
                ]

                for entry in image_entries : 

                    value : str | None = self.find_element(
                        element = f'image:{entry}' , 
                        sitemap = img , 
                        namespaces = self.root_namespaces
                    )

                    img_data[entry] = value if value else None 

                if img_data : url_data['images'].append(img_data)

        return url_data

    def find_news_entries_and_add_to_dict(
        self , 
        url , 
        url_data 
    ) -> dict : 

        news = url.find('news:news' , self.root_namespaces)

        if news : 

            news_data = {}
            publication = news.find('news:publication' , self.root_namespaces)

            if publication : 

                publication_entries = [
                    'name' , 
                    'language'
                ]

                for entry in publication_entries : 

                    value = self.find_element(
                        element = f'news:{entry}' , 
                        sitemap = publication , 
                        namespaces = self.root_namespaces
                    )

                    news_data[entry] = value if value else None 
            
            news_entries = [
                'publication_date' , 
                'title'
            ]

            for entry in news_entries : 

                value = self.find_element(
                    element = f'news:{entry}' , 
                    sitemap = news , 
                    namespaces = self.root_namespaces
                )

                news_data[entry] = value if value else None 

            if news_data : url_data['news'] = news_data

        return url_data


    def parse_sitemap(self, xml_content : str) -> list[dict] : 

        urls_data = []

        try : 

            root : Element = ET.fromstring(xml_content)
            
            for url in root.findall('.//sitemap:url', self.root_namespaces):
                url_data = {}
                
                url_data = self.find_basic_entries_and_add_to_dict(
                    url = url , 
                    url_data = url_data
                )
                
                url_data = self.find_image_entries_and_add_to_dict(
                    url = url , 
                    url_data = url_data
                )

                url_data = self.find_news_entries_and_add_to_dict(
                    url = url , 
                    url_data = url_data
                )

                if url_data : urls_data.append(url_data)
                
            
            return urls_data

        except ET.ParseError as e : print(f"Error parsing sitemap XML: {e}") ; return []
    
    def extract_sitemap(self) -> list : 

        print(f"Fetching sitemap from: {self.url}")
        
        # Get the xml content of the website
        xml_content = self.fetch_sitemap(self.url)

        if not xml_content : return []
        
        # First, try to parse as sitemap index
        sitemap_urls = self.parse_sitemap_index(xml_content)
        
        if sitemap_urls:

            all_urls = []
            
            for url in tqdm(sitemap_urls , total = len(sitemap_urls)) : 

                sub_xml = self.fetch_sitemap(url)

                if sub_xml : 

                    urls : list = self.parse_sitemap(sub_xml)
                    all_urls.extend(urls)

            return all_urls

        else:

            urls = self.parse_sitemap(xml_content)

            return urls

    def __call__(self) : 

        urls = self.extract_sitemap()

        return urls