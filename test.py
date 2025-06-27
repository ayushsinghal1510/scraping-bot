import requests 
import json
from tqdm import tqdm

# response = requests.post(
#     'http://localhost:8888/scrape-url' , 
#     json = {
#         'url' : 'https://seedlingschools.com/'
#     }
# )

# with open('file.json' , 'w') as json_file : json.dump(response.json() , json_file)

# with open('file.json') as json_file : links = json.load(json_file)

# pdf_links = links['pdf_links']
# all_links = links['all_links']

# for link in tqdm(all_links , total = len(all_links)) : 
    
#     response = requests.post(
#         'http://localhost:8888/scrape-page' , 
#         json = {
#             'url' : link , 
#             'scrape-images' : False
#         }
#     )

# response = requests.post(
#     'http://localhost:8888/ask' , 
#     json = {
#         'query' : 'I am a parent, I wanna see, my child marks, How do I see that over the Seedling ERP' , 
#         'session_id' : 'eds'
#     }
# )

# print(json.dumps(response.json() , indent = 4))

response = requests.post(
    'http://localhost:8888/scrape-pdf' , 
    json = {
        'url' : 'www.dwedsf.pdf' , 
        'scrape-image' : False
    }
)

print(response.json())