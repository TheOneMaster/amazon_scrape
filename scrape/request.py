from concurrent.futures import ThreadPoolExecutor
from typing import Dict, List, Literal, Optional, Type, TypedDict

import pandas as pd
import requests
import tqdm
from bs4 import BeautifulSoup
from dotenv import dotenv_values
import json

from .types import WEBSITE_DATA, Scrape, Proxy

temp_headers = dotenv_values(".env")
HEADERS: Dict[str, str] = { key: value for key, value in temp_headers.items() if value is not None}

# Helper functions
def createSearchLink(base_url: str, search_term: str, page: int) -> str:
    if base_url == WEBSITE_DATA["Amazon"]['url']:
        return f"{base_url}/s?k={search_term}&page={page}"

    elif base_url == WEBSITE_DATA["IHerb"]['url']:
        raise NotImplementedError

    else:
        raise ValueError("Website not supported")

def getLinksFromSearch(soup: BeautifulSoup, base_url: str) -> List[str]:
    links = soup.find_all("a", attrs={
        "class": "a-link-normal s-no-outline"
    })
    
    ret_links: List[str] = []
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
    return unique_links.tolist()

def loadLinksFromSearch(links: list[str], headers: dict, session) -> Dict[str, requests.Response]:
    url_to_response = {}
    with ThreadPoolExecutor() as executor:
        futures_to_url = { executor.submit(loadSessionUrl, url, session): url for url in links }

        for future in tqdm.tqdm(futures_to_url, desc="URL requests", unit="links"):
            url = futures_to_url[future]
            response = future.result()
            url_to_response[url] = response

    return url_to_response

def loadSessionUrl(url: str, session) -> requests.Response:
    return session.get(url)


# Data Manipulation
def convertDataToDataFrame(dataArray: List[Scrape]) -> pd.DataFrame:
    product_information_array = [product.getData() for product in dataArray]
    data_df = pd.DataFrame.from_records(product_information_array)

    return data_df

def dfPriceManipulation(df: pd.DataFrame) -> pd.DataFrame:
    df_modified = df.drop(columns=['unitPrice', 'unitType'])

    count_type_index = df['unitType'] == 'Count'
    df_modified['pricePerCount'] = df[count_type_index]['unitPrice']
    df_modified["pricePerOz"] = df[~count_type_index]['unitPrice']

    return df_modified


# Main functions to get data
def getDataFromSearch(website: Literal["Amazon", "IHerb"], search_term: str, headers=None, page=1, maxProducts: Optional[int] = None,
                      proxy: Optional[Proxy] = None) -> Dict[str, requests.Response]:

    website_data = WEBSITE_DATA[website]
    base_url = website_data['url']
    search_url = createSearchLink(base_url, search_term, page)
    session = requests.Session()
    
    # Headers
    search_headers = HEADERS.copy()
    if isinstance(headers, dict):
        search_headers.update(headers)
        
    session.headers.update(search_headers)
    
    # Proxies
    if proxy is None:
        proxy = {
            "location": "NY",
            "type": "http"
        }
        
    with open("proxies.json") as proxy_JSON:
        proxy_dict = json.load(proxy_JSON)
        location_proxy_data = proxy_dict[proxy['location']]
        proxy_type_data = location_proxy_data[proxy['type']]
        
        proxy_data: List[str] = proxy_type_data

    session.proxies.update({
        "http": proxy_data[0],
        "https": proxy_data[0]
    })
        
    # Search for products
    search_page = session.get(search_url)
    search_soup = BeautifulSoup(search_page.content, "lxml")
    links = getLinksFromSearch(search_soup, base_url)

    if maxProducts is not None:
        links = links[:maxProducts]

    url_to_response = loadLinksFromSearch(links, search_headers, session)

    return url_to_response


def search(website: Literal['Amazon', 'IHerb'], search_term: str, page=1, maxProducts: Optional[int] = None, **kwargs) -> pd.DataFrame:
    headers = kwargs.get("header", None)

    WebsiteClass = WEBSITE_DATA[website]["class"]
    data = getDataFromSearch(website, search_term, page=page, maxProducts=maxProducts, headers=headers)
    data_list = [WebsiteClass(response, url, search_term) for url, response in tqdm.tqdm(data.items(), desc="Processing webpages", unit="webpages")]

    df = convertDataToDataFrame(data_list)
    df = dfPriceManipulation(df)

    return df
