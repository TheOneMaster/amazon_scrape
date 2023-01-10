from typing import Literal, List, Dict

import requests
from bs4 import BeautifulSoup

from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
import tqdm

import pandas as pd
import csv

from scrape.webpageScrape import AmazonProductData, IHerbProductData

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/54.0.2840.71 Safari/537.36',
    'Accept-Encoding': 'gzip, deflate',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'DNT': '1',
    'Connection': 'close',
    'Upgrade-Insecure-Requests': '1'
}

WEBSITE_TO_URL = {
    "Amazon": "https://www.amazon.com",
    "IHerb": "https://www.iherb.com"
}

WEBSITE_BASE_TO_CLASS = {
    "Amazon": AmazonProductData,
    "IHerb": IHerbProductData,
}

def createSearchLink(website: Literal["Amazon", "IHerb"], search_term: str, page: int) -> str:

    base_url = WEBSITE_TO_URL.get(website, None)


    if website == "Amazon":

        return f"{base_url}/s?k={search_term}&page={page}"

    elif website == "IHerb":

        raise NotImplementedError
    
    else:
        raise ValueError("Website not supported")


# Helper functions
def getLinksFromSearch(soup: BeautifulSoup, base_url: str) -> List[str]:
    
    links = soup.find_all("a", attrs={
        "class": "a-link-normal s-no-outline"
    })

    ret_links = []

    for link in links:

        href = link.get("href")

        # Conditions to remove link from the list
        is_amazon_page = href[0:5] != "https"
        sponsored_product = "gp/slredirect" in href
        is_amazon_search = "www.amazon.com" in href

        if is_amazon_page and not sponsored_product and not is_amazon_search:

            # Remove references from URL
            cleaned_href = href.rsplit("/ref=", 1)[0]

            is_full_link = "www.amazon.com" in href

            if is_full_link:
                ret_links.append(f'https://{cleaned_href}')
            else:
                ret_links.append(f"{base_url}{cleaned_href}")

    unique_links = pd.unique(ret_links)

    return unique_links

def loadLinksFromSearch(links: list[str], headers: dict) -> Dict[str, requests.Response]:
    
    url_to_response = {}
    
    with ThreadPoolExecutor() as executor:
        
        futures_to_url = {executor.submit(loadSessionUrl, url, headers): url for url in links}
        
        for future in tqdm.tqdm(futures_to_url, desc="URL requests", unit="links"):
            
            url = futures_to_url[future]
            response = future.result()
            
            url_to_response[url] = response
            
    return url_to_response

def loadSessionUrl(url: str, headers: dict) -> requests.Response:
    
    return requests.get(url, headers=headers)

# Try to make this work
def multiprocessedParse(product_dict: dict, productType: str) -> List[AmazonProductData|IHerbProductData]:
    
    with ProcessPoolExecutor() as executor:
        
        products = []
        product_list = [executor.submit(lambda url, response: AmazonProductData(response, url, productType)._details) for url, response in product_dict.items()]
        
        for prod in product_list:
            products.append(prod.result())
        
        return products

# Main function to get data
def getDataFromSearch(website: Literal["Amazon", "IHerb"], search_term: str, headers=None, page=1, output_file=False, as_df=True, raw=False, maxProducts: int=None) -> pd.DataFrame|List[AmazonProductData]:

    search_url = createSearchLink(website, search_term, page)
    
    search_headers = HEADERS.copy()
    
    if isinstance(headers, dict):
        search_headers.update(headers)
    
    search_page = requests.get(search_url, headers=search_headers)
    search_soup = BeautifulSoup(search_page.content, "lxml")
    
    base_url = WEBSITE_TO_URL[website]
    links = getLinksFromSearch(search_soup, base_url)

    if maxProducts is not None:
        links = links[:maxProducts]
    
    url_to_response = loadLinksFromSearch(links, search_headers)
    
    if raw:
        return url_to_response
            
    product_data_list = [AmazonProductData(response, url, search_term) for url, response in tqdm.tqdm(url_to_response.items(), desc="Processing webpages", unit="webpages")]
    
    if as_df:
        product_data = [product.to_list() for product in product_data_list]
        columns = product_data_list[0].columns
        
        product_df = pd.DataFrame(product_data, columns=columns)

        # unitPrice and unitType manipulation
        product_df['pricePerCount'] = product_df[product_df["unitType"]=='Count']['unitPrice']
        product_df['pricePerOz'] = product_df[product_df['pricePerCount'].isnull()]['unitPrice']
        
        if output_file:
            product_df.to_csv("output.csv", index=False, mode="w", encoding="utf-8",
                            quotechar="|", quoting=csv.QUOTE_MINIMAL, sep=";")
        

        product_df = product_df.drop(columns=['unitPrice', 'unitType'])

        return product_df
        
    return product_data_list