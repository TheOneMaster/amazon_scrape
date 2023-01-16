from typing import TypedDict, Dict, Type, TypeVar

from .PageScrape import PageScrape, AmazonPageScrape, IHerbPageScrape
from .ProductData import ProductData

WEB_DATA = TypedDict("WEBSITE DATA", {
    "url": str,
    "class": Type[AmazonPageScrape|IHerbPageScrape]
})

WEBSITE_DATA: Dict[str, WEB_DATA] = {
    "Amazon": {
        "url": "https://www.amazon.com",
        "class": AmazonPageScrape
    },
    "IHerb": {
        "url": "https://www.iherb.com",
        "class": IHerbPageScrape
    }
}

Scrape = TypeVar("Scrape", bound=PageScrape)

Proxy = TypedDict("Proxy", {
    "location": str,
    "type": str
})
