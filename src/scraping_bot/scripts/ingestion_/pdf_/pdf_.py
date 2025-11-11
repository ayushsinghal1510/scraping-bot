
from io import BytesIO
from tqdm import tqdm
from pymilvus import MilvusClient

from unstructured.partition.pdf import partition_pdf
from unstructured.documents.elements import Element

from ..ingestion_ import INGESTION
from ..document_ import Document

class PDF(INGESTION) : 

    def __init__(
        self , 
        milvus_client : MilvusClient , 
        pdf_bytes : bytes , 
        collection_name : str , 
        config : dict , 
        embedding_client , 
        pdf_name : str = ''
    ) -> None : 

        super().__init__(
            milvus_client = milvus_client , 
            collection_name = collection_name , 
            config = config 
        )

        self.pdf_bytes : bytes = pdf_bytes
        self.collection_name : str = collection_name 
        self.config : dict = config 
        self.embedding_client = embedding_client
        self.pdf_name : str = pdf_name

        self.chunks : list = []

    def create_chunks_and_add_to_vectordb(
        self , 
        chunk_size : int | None = None 
    ) -> int : 

        self.chunk_size : int = chunk_size if chunk_size else self.config['chunk-size']

        partitioned_elements : list[Element] = partition_pdf(file = BytesIO(self.pdf_bytes))
        narrative_elements : list[Element] = [element for element in partitioned_elements if element.category in ["NarrativeText", "ListItem" , 'Element' , 'Title']]

        for element in tqdm(
            narrative_elements , 
            total = len(narrative_elements) , 
            leave = False
        ) : 

            dict_element : dict = element.to_dict()
            element_text : str = dict_element['text']

            words : list[str] = element_text.split()

            self.chunks.extend(
                [
                    Document(
                        text = ' '.join(words[index : index + self.chunk_size]) , 
                        type_ = 'pdf' ,
                        pdf_name = str(self.pdf_name)
                    ).to_dict() 
                    for index in range(0 , len(words) , self.chunk_size)
                ]
            )

        self.add_to_vectordb(
            embedding_client = self.embedding_client , 
            documents = self.chunks
        )

        return len(self.chunks)

    def __call__(
        self , 
        chunk_size : int | None = None
    ) -> int : return self.create_chunks_and_add_to_vectordb(chunk_size = chunk_size)