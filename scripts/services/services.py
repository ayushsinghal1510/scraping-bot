async def process_link(href) : 

    if (
        href and 
        isinstance(href , str) and  
        not href.startswith('mailto:') and
        not href.endswith('png') and 
        not href.endswith('jpg') and
        not href.endswith('jpeg') and
        not href.endswith('gif') and
        not href.endswith('bmp') and
        not href.endswith('tiff') and
        not href.endswith('svg') and
        not href.endswith('webp') # ! Add conditions as needed 
    ) : return href

    return None

