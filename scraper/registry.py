''' Old file: scraper/registry.py
# scraper/registry.py
from providers.ca_post.list import CAPostLister
from providers.ca_post.parse import CAPostParser



PROVIDERS = {
    "ca_post": {
        "lister": CAPostLister,
        "parser": CAPostParser,
    }
}
'''

# scraper/registry.py (new updated file)
from providers.ca_post import CAPostLister, CAPostParser

PROVIDERS = {
    "ca_post": {
        "lister": CAPostLister,
        "parser": CAPostParser,
    }
}
