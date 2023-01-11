from concurrent.futures import ThreadPoolExecutor
from typing import Dict, List, Literal, Optional, Type, TypedDict

import pandas as pd
import requests
import tqdm
from bs4 import BeautifulSoup

from scrape.webpageScrape import (AmazonProductData, IHerbProductData, P,
                                  ProductData)

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/54.0.2840.71 Safari/537.36',
    'Accept-Encoding': 'gzip, deflate',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'DNT': '1',
    'Connection': 'close',
    'Upgrade-Insecure-Requests': '1'
}


WEB_DATA = TypedDict("WEBSITE DATA", {
    "url": str,
    "class": Type[ProductData]
})

WEBSITE_DATA: Dict[str, WEB_DATA] = {
    "Amazon": {
        "url": "https://www.amazon.com",
        "class": AmazonProductData
    },
    "IHerb": {
        "url": "https://www.iherb.com",
        "class": IHerbProductData
    }
}


def createSearchLink(base_url: str, search_term: str, page: int) -> str:

    if base_url == WEBSITE_DATA["Amazon"]['url']:

        return f"{base_url}/s?k={search_term}&page={page}"

    elif base_url == WEBSITE_DATA["IHerb"]['url']:

        raise NotImplementedError

    else:
        raise ValueError("Website not supported")


# Helper functions
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


def loadLinksFromSearch(links: list[str], headers: dict) -> Dict[str, requests.Response]:

    url_to_response = {}

    with ThreadPoolExecutor() as executor:

        futures_to_url = {executor.submit(
            loadSessionUrl, url, headers): url for url in links}

        for future in tqdm.tqdm(futures_to_url, desc="URL requests", unit="links"):

            url = futures_to_url[future]
            response = future.result()

            url_to_response[url] = response

    return url_to_response


def loadSessionUrl(url: str, headers: dict) -> requests.Response:

    return requests.get(url, headers=headers)

# Main function to get data


def getDataFromSearch(website: Literal["Amazon", "IHerb"], search_term: str, headers=None, page=1, maxProducts: Optional[int] = None) -> List[ProductData]:

    website_data = WEBSITE_DATA[website]
    base_url = website_data['url']
    WebsiteClass = website_data['class']

    search_url = createSearchLink(base_url, search_term, page)

    search_headers = HEADERS.copy()

    if isinstance(headers, dict):
        search_headers.update(headers)

    search_page = requests.get(search_url, headers=search_headers)
    search_soup = BeautifulSoup(search_page.content, "lxml")

    links = getLinksFromSearch(search_soup, base_url)

    if maxProducts is not None:
        links = links[:maxProducts]

    url_to_response = loadLinksFromSearch(links, search_headers)

    product_data_list = [WebsiteClass(response, url, search_term) for url, response in tqdm.tqdm(
        url_to_response.items(), desc="Processing webpages", unit="webpages")]

    return product_data_list


def convertDataToDataFrame(dataArray: List[P]) -> pd.DataFrame:

    product_information_array = [product.to_list() for product in dataArray]
    columns = dataArray[0].columns

    data_df = pd.DataFrame(product_information_array, columns=columns)

    return data_df


def dfPriceManipulation(df: pd.DataFrame) -> pd.DataFrame:

    df_modified = df.drop(columns=['unitPrice', 'unitType'])

    count_type_index = df['unitType'] == 'Count'

    df_modified['pricePerCount'] = df[count_type_index]['unitPrice']
    df_modified["pricePerOz"] = df[~count_type_index]['unitPrice']

    return df_modified


def search(website: Literal['Amazon', 'IHerb'], search_term: str, page=1, maxProducts: Optional[int] = None, **kwargs) -> pd.DataFrame:

    headers = kwargs.get("header", None)

    data = getDataFromSearch(
        website, search_term, page=page, maxProducts=maxProducts, headers=headers)

    df = convertDataToDataFrame(data)
    df = dfPriceManipulation(df)

    return df
