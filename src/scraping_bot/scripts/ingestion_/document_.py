from datetime import datetime

class Document : 

    def __init__(
        self , 
        text : str , 
        type_ : str , 
        url : str = '' , 
        base_url : str = '' , 
        pdf_name : str = '' , 
    ) : 

        self.text : str = text 
        self.type_ : str = type_
        self.url : str = url 
        self.base_url : str = base_url 
        self.pdf_name : str = pdf_name

        if self.type_ not in ['pdf' , 'web'] : raise ValueError(f'type_ must be one of [pdf , web], received : {self.type_}')

        if self.type_ == 'pdf' : 

            if not self.pdf_name : raise ValueError('pdf_name must be provided for pdf documents')

        elif self.type_ == 'web' : 

            if not self.url : raise ValueError('url must be provided for web documents')
            if not self.base_url : raise ValueError('base_url must be provided for web documents')

            if self.pdf_name : raise ValueError('pdf_name should not be provided for web documents, if this is a web pdf, use type_ = pdf and use url and base_url accordingly')
        
    def convert_datetime_str_to_int(self , datetime_str : str) -> int : 

        if not datetime_str or datetime_str == 'not provided' : return 0

        try :         
            
            if isinstance(datetime_str , datetime) : return int(datetime_str.timestamp() * 1000)
            return int(datetime.fromisoformat(datetime_str).timestamp() * 1000)

        except Exception as e : print(f'Error converting datetime string to int : {e}' , datetime) ; return 0

    def to_dict(self) -> dict : 

        attributes = {}

        for attr in dir(self):

            if (
                not attr.startswith('__') and 
                not callable(getattr(self , attr))
            ) : attributes[attr] = getattr(self, attr)

        return attributes