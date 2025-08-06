async def process_link(href):
    if (
        href and 
        isinstance(href, str) and  
        not href.startswith('mailto:') and

        # Exclude media/image/video formats
        not href.endswith(('png', 'jpg', 'jpeg', 'gif', 'bmp', 'tiff', 'svg', 'webp', 'webm', 'mp4')) and
        
        # Exclude links containing non-textual content markers
        'folder' not in href.lower() and 
        'upload' not in href.lower() and 
        'album' not in href.lower() and 
        'image' not in href.lower() and 
        'video' not in href.lower() and 
        'file' not in href.lower() and 
        'download' not in href.lower() and 
        'static' not in href.lower() and
        'media' not in href.lower()
    ):
        return href

    return None
