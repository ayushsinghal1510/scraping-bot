from pymilvus import MilvusClient
from sentence_transformers import SentenceTransformer

class INGESTION : 

    def __init__(
        self , 
        milvus_client : MilvusClient , 
        collection_name : str , 
        config : dict
    ) -> None : 

        self.config : dict = config 

        self.client : MilvusClient = milvus_client
        self.collection_name : str = collection_name

        if not self.client.has_collection(self.collection_name) : self.client.create_collection(collection_name = self.collection_name)

        # self.constraints : dict[str , int | float]

        # self.constraints.update({'url' : 512})
        # self.constraints.update({'base_url' : 512})

        # self.constraints.update({'pdf_name' : 512})

    # def validate_document(self , document : dict) -> tuple[bool , str] : 

    #     for field , max_length in self.constraints.items() : 

    #         if field in document : 

    #             field_value = str(document[field])

    #             if len(field_value) > max_length : return False , f"Field '{field}' exceeds max length {max_length} (actual: {len(field_value)})"

    #     return True , ''

    def add_to_vectordb(
        self , 
        embedding_client : SentenceTransformer , 
        documents : list[dict[str , str]]
    ) : 

        vectors = embedding_client.encode(
            [document['text'] for document in documents] , 
            show_progress_bar = True
        )

        data = []
        skipped_documents = []

        for index , (document , vector) in enumerate(zip(
            documents , 
            vectors
        )) : 

            # is_valid , error_msg = self.validate_document(document)
            is_valid , error_msg = True , ''
            
            if not is_valid : 

                skipped_documents.append({
                    'index' : index , 
                    'reason' : error_msg , 
                    'document' : document
                })

                print(f'⚠️  Skipping document at index {index}: {error_msg}')

                continue

            input_dict = {
                'id' : index , 
                'vector' : vector , 
            }

            for key , value in zip(document.keys() , document.values()) : input_dict[key] = value

            data.append(input_dict)

        if data : res = self.client.insert(
            collection_name=self.collection_name,
            data=data
        )
        else : print('⚠️  No valid documents to insert')

        if skipped_documents : 

            print(f'\n⚠️  Skipped {len(skipped_documents)} document(s) due to validation errors:')

            for skipped in skipped_documents : print(f'   - Index {skipped["index"]}: {skipped["reason"]}')
        
        return {
            'inserted' : len(data) , 
            'skipped' : len(skipped_documents) , 
            'skipped_details' : skipped_documents
        }