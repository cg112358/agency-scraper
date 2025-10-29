# scraper/registry.py
from providers.ca_post.list import CAPostLister
from providers.ca_post.parse import CAPostParser

PROVIDERS = {
    "ca_post": {
        "lister": CAPostLister,
        "parser": CAPostParser,
    }
}
