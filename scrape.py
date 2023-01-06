import requests
from bs4 import BeautifulSoup
import re

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
    
    def __init__(self) -> None:
        
        self.url = None
        self._soup = None
        
        self.title = None
        self.brand = None
        self.asin = None
        self.productType = None
        
        self.price = None
        self.unitType, self.unitPrice = None, None
        
        self.rating = None
        self.numRatings = None
        self.rank = None
        self.formFactor = None
        self.firstAvailable = None

    def write(self, writer) -> None:
        csv_items = [self.url, self.title, self.brand, self.asin, self.productType,
                        self.price, self.unitPrice, self.unitType, self.firstAvailable,
                        self.rating, self.numRatings, self.rank, self.formFactor]
        
        csv_items = [str(item) for item in csv_items]
        
        writer.writerow(csv_items)


class AmazonProductData(ProductData):

    def __init__(self, response: requests.Response, url: str, productType: str) -> None:
        super().__init__()

        self.productType = productType

        self._soup = BeautifulSoup(response.content, "lxml")

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
        self.title = self._getTitle_()
        self.brand = self._getBrand_()
        self.asin = self._getASIN_()
        
        self.price = self._getPrice_()
        self.unitType, self.unitPrice = self._getPricePerUnit_()
        
        self.rating = self._getRating_()
        self.numRatings = self._getNumRatings_()
        self.rank = self._getBestSellerRank_()
        self.formFactor = self._getFormFactor_()
        self.firstAvailable = self._getFirstAvailable_()


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

    return ret_links

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
def getDataFromSearch(base_url: str, search_term: str, headers=None, page=1, output=True) -> list[AmazonProductData]:
    
    search_url = f"{base_url}/s?k={search_term}&page={page}"
    
    if headers is None:
        headers = HEADERS.copy()
    
    search_page = requests.get(search_url, headers=headers)
    search_soup = BeautifulSoup(search_page.content, "lxml")
    
    links = getLinksFromSearch(search_soup, base_url)
    
    session = requests.Session()
    
    url_to_response = loadLinksFromSearch(links, headers)
            
            
    product_data_list = [AmazonProductData(response, url, search_term) for url, response in url_to_response.items()]
    
    if output:
            
        with open("output.csv", "w") as output_file:
            
            writer = csv.writer(output_file, delimiter=";", quotechar="|", quoting=csv.QUOTE_MINIMAL)
            
            Columns = ["Url", "Title", "Brand", "ASIN", "Product Type",
                    "Price", "Unit Price", "Unit Type", "First Available",
                    "Average Rating", "Number of Ratings", "Rank",
                    "Form Factor"]
            
            writer.writerow(Columns)
            
            for product in product_data_list:
                
                product.write(writer)
                
    return product_data_list
        
        
            
            
    
    
    
    