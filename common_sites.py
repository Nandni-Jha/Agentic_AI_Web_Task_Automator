# common_sites.py

FAMOUS_SITES = {
    "google": "https://www.google.com",
    "youtube": "https://www.youtube.com",
    "wikipedia": "https://www.wikipedia.org",
    "amazon": "https://www.amazon.com",
    "facebook": "https://www.facebook.com",
    "twitter": "https://www.twitter.com", # (Now X)
    "x": "https://www.x.com",
    "github": "https://www.github.com",
    "linkedin": "https://www.linkedin.com",
    "reddit": "https://www.reddit.com",
    "bbc news": "https://www.bbc.com/news",
    "cnn": "https://www.cnn.com",
    "nytimes": "https://www.nytimes.com",
    "openai": "https://www.openai.com",
    "hugging face": "https://huggingface.co",
    # Add more sites
}

def get_url_for_site(site_name: str) -> str | None:
    """
    Returns the URL for a common site name, if found.
    Performs a case-insensitive lookup.
    """
    return FAMOUS_SITES.get(site_name.lower())

if __name__ == '__main__':
    print(get_url_for_site("Google"))
    print(get_url_for_site("GooGLe"))
    print(get_url_for_site("non existent"))