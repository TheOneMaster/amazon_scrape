import requests
from bs4 import BeautifulSoup
import re
import pandas as pd

import typing

from concurrent.futures import ThreadPoolExecutor
import time
import csv
import tqdm

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/54.0.2840.71 Safari/537.36',
    'Accept-Encoding': 'gzip, deflate',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'DNT': '1',
    'Connection': 'close',
    'Upgrade-Insecure-Requests': '1'
    }

class ProductData:
    
    def __init__(self, url: str, productType: str, response: requests.Response) -> None:
    
        self._soup = BeautifulSoup(response.content, "lxml")
        
        self._details = {
            "url": url,
            "title": None,
            "brand": None,
            "asin": None,
            "productType": productType,
            "price": None,
            "unitPrice": None,
            "rating": None,
            "numRatings": None,
            "formFactor": None,
            "firstAvailable": None
        }

    def to_list(self) -> list:
        
        return self._details.values()
    
    @property
    def columns(self) -> typing.List[str]:
        
        return self._details.keys()

class AmazonProductData(ProductData):

    def __init__(self, response: requests.Response, url: str, productType: str) -> None:
        super().__init__(url, productType, response)
        
        self._details['rank'] = None

        self.__processData__()     

  
    def _getTitle_(self) -> str:

        try: 
            title = self._soup.find("span", attrs={"id": "productTitle"})

            title_value = title.string
            title_str = title_value.strip()

        except AttributeError:
            title_str = "Unknown"

        return title_str

    def _getBrand_(self) -> str:

        try:

            brand_row = self._soup.find("tr", attrs={
                "class": "a-spacing-small po-brand"
            })
            
            brand_span = brand_row.find("span", attrs={
                "class": "po-break-word"
            })
            
            brand_str = brand_span.string

            
            brand_str = brand_str.strip()  

        except AttributeError:
            brand_str = "Unknown"

        return brand_str

    def _getASIN_(self) -> str:

        try:

            details = self._soup.find("div", attrs={
                "id": "detailBullets_feature_div"
            })

            asin = details.find("span", string=re.compile("ASIN")).find_next()

            asin_str = asin.string.strip()

        except AttributeError:
            asin_str = "Unknown"

        return asin_str

    def _getRating_(self) -> float:

        try: 
            span = self._soup.find(id="acrPopover")
            title = span.get_attribute_list("title")[0]
            rating_str = title.split(" ")[0]

            rating = float(rating_str)

        except:
            rating = 'N/A'

        return rating

    def _getNumRatings_(self) -> int:

        try:
            num_ratings_span = self._soup.find(id="acrCustomerReviewText")

            num_ratings_str = num_ratings_span.string
            num_ratings_str = num_ratings_str.split(" ")[0]
            num_ratings_str = num_ratings_str.replace(",", "")

            num_ratings_int = int(num_ratings_str)

        except:
            num_ratings_int = 'N/A'

        return num_ratings_int

    def _getPrice_(self) -> str:

        try:
            price_span = self._soup.find("span", attrs={
                "class": "a-price a-text-price a-size-medium apexPriceToPay"
            })

            price = price_span.findChild("span").string

        except AttributeError:
            price = "N/A"

        return price

    def _getPricePerUnit_(self) -> tuple[str, str]:

        try:
            unitPrice_span = self._soup.find("span", attrs={
                "class": "a-price a-text-price a-size-small"
            })
            
            if unitPrice_span is None:
                unitPrice_span = self._soup.find("span", attrs={
                    "class": "a-price a-text-price",
                    "data-a-size": "mini"
                })

            unitData_div = unitPrice_span.parent

            unitType = unitData_div.contents[-1].strip().replace(")", "")
            unitType = unitType.split()[-1]

        
            unitPrice = unitPrice_span.findChild("span").string
            unitPrice = unitPrice.strip()

        except:
            
            unitType, unitPrice = "N/A", "N/A"

        return (unitType, unitPrice)

    def _getFirstAvailable_(self) -> str:
        
        try:
            details = self._soup.find("div", attrs={
                "id": "detailBullets_feature_div"
            })
            
            available_str = re.compile("Date First Available")
            firstAvailable_span = details.find("span", string=available_str).find_next()
            
            firstAvailable_str = firstAvailable_span.string.strip()
        
        except AttributeError:
            firstAvailable_str = "N/A"
        
        return firstAvailable_str

    def _getBestSellerRank_(self) -> int:
        
        try:
            rank_str = re.compile("Health & Household")
            category_items = self._soup.findAll(string=rank_str)
            
            category_rank_str = [rank for rank in category_items if "#" in rank][0]
            category_rank_str = category_rank_str.strip()
            category_rank_str = category_rank_str.split()[0][1:]
            category_rank_str = category_rank_str.replace(",", "")
            
            category_rank = int(category_rank_str)
        
        except:
            category_rank = "N/A"
            
        return category_rank
    
    def _getFormFactor_(self) -> str:
        
        try:
            form_row = self._soup.find("tr", attrs={
                "class": "a-spacing-small po-item_form"
            })
            
            form_span = form_row.find("span", attrs={
                "class": "po-break-word"
            })
            
            form_str = form_span.string
        
        except:
            form_str = "N/A"
            
        return form_str
        

    def __processData__(self) -> None:
        
        self._details['title'] = self._getTitle_()
        self._details["brand"] = self._getBrand_()
        self._details["asin"] = self._getASIN_()
        
        self._details["price"] = self._getPrice_()
        self._details["unitType"], self._details["unitPrice"] = self._getPricePerUnit_()
        
        self._details["rating"] = self._getRating_()
        self._details["numRatings"] = self._getNumRatings_()
        self._details["rank"] = self._getBestSellerRank_()
        
        self._details["formFactor"] = self._getFormFactor_()
        self._details["firstAvailable"] = self._getFirstAvailable_()


class IHerbProductData(ProductData):
    
    def __init__(self) -> None:
        super().__init__()


# Helper functions
def getLinksFromSearch(soup: BeautifulSoup, base_url: str) -> list[str]:
    
    links = soup.find_all("a", attrs={
        "class": "a-link-normal s-no-outline"
    })

    ret_links = []

    for link in links:

        href = link.get("href")

        is_amazon_page = href[0:5] != "https"
        sponsored_product = "gp/slredirect" in href

        if is_amazon_page and not sponsored_product:

            # Remove references from URL
            cleaned_href = href.rsplit("/ref=", 1)[0]

            ret_links.append(f"{base_url}{cleaned_href}")

    unique_links = pd.unique(ret_links)

    return unique_links

def loadLinksFromSearch(links: list[str], session: requests.Session, headers: dict) -> typing.Dict[str, requests.Response]:
    
    url_to_response = {}
    
    with ThreadPoolExecutor() as executor:
        
        futures_to_url = {executor.submit(loadSessionUrl, session, url, headers): url for url in links}
        start_time = time.time()
        
        for future in tqdm.tqdm(futures_to_url, desc="URL requests"):
            
            url = futures_to_url[future]
            response = future.result()
            
            url_to_response[url] = response
            
    return url_to_response

def loadSessionUrl(session: requests.Session, url: str, headers: dict):
    
    return session.get(url, headers=headers)


# Main function to get data
def getDataFromSearch(base_url: str, search_term: str, headers=None, page=1, output_file=True, raw=False) -> list[AmazonProductData]:
    
    search_url = f"{base_url}/s?k={search_term}&page={page}"
    
    headers = HEADERS.copy()
    if isinstance(HEADERS, dict):
        headers.update(headers)
    
    search_page = requests.get(search_url, headers=headers)
    search_soup = BeautifulSoup(search_page.content, "lxml")
    
    links = getLinksFromSearch(search_soup, base_url)
    
    session = requests.Session()
    
    url_to_response = loadLinksFromSearch(links, session, headers)
           
    if raw:
        return url_to_response
            
    product_data_list = [AmazonProductData(response, url, search_term) for url, response in tqdm.tqdm(url_to_response.items(), desc="Processing webpages")]
    
    
    
    product_data = [product.to_list() for product in product_data_list]
    columns = product_data_list[0].columns
    
    product_df = pd.DataFrame(product_data, columns=columns)
    
    if output_file:
        product_df.to_csv("output.csv", index=False, mode="w", encoding="utf-8",
                          quotechar="|", quoting=csv.QUOTE_MINIMAL, sep=";")
    
    return product_df
        
        
            
            
    
    
    
    