from typing import Type, overload, Dict, Any, Optional, List
from types import TracebackType

from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException

import re
import numpy as np
import tqdm

from ProductData import ProductData, convertDataToDataframe


def updateAttributes(new_data: Dict[str, Any], current_data: ProductData) -> None:
    """Update the attributes of the current data with the keys from the new data"""
    for key, value in new_data.items():
        if key in current_data.__slots__:
            setattr(current_data, key, value)


class AmazonWebInstance:
    
    PRODUCT_OVERVIEW_MAP = {
        "Item Form": "formFactor",
        "Brand": "brand",
        "Recommended Uses For Product": "uses"
    }
    
    PRODUCT_DETAILS_MAP = {
        "Date First Available": "firstAvailable",
        "Manufacturer": "manufacturer",
        "ASIN": "asin",
        "Best Sellers Rank": "rank",
        "Country of Origin": "origin"
    }
    
    BASE_URL = "https://www.amazon.com"
    
    
    def __init__(self, headless=False) -> None:
        
        self.options = Options()
        self.options.headless = headless
        
        self.options.set_preference("permissions.default.stylesheet", 2)
        # self.options.set_preference("permissions.default.image", 2)
        # profile = webdriver.FirefoxProfile()
        # profile.add_extension("ublock_origin-1.46.0.xpi")
        
        self.driver = webdriver.Firefox(options=self.options)
        self.driver.install_addon("ext/ublock_origin-1.46.0.xpi", temporary=True)
        # self
        
        amazon_url = "https://www.amazon.com/ref=nav_bb_logo"
        
        self.driver.get(amazon_url)
    
        self.driver.find_element(By.ID, "nav-global-location-popover-link").click()

        WebDriverWait(self.driver, 10).until(EC.element_to_be_clickable((By.ID, "GLUXZipUpdateInput")))

        self.driver.find_element(By.ID, "GLUXZipUpdateInput").send_keys("10001")
        self.driver.find_element(By.ID, "GLUXZipUpdate").click()
        
        
        
    def __enter__(self) -> 'AmazonWebInstance':
        return self
    
    @overload
    def __exit__(self, type: None, value: None, traceback: None) -> None:
        ...
    
    @overload
    def __exit__(self, type: Type[BaseException], value: BaseException, traceback: TracebackType) -> None:
        ...
        
    def __exit__(self, type: Type[BaseException]|None, value: BaseException|None, traceback: TracebackType|None) -> None:
        self.driver.quit()
    
    
    def parsePage(self, page: str, prodType: str) -> ProductData:
        
        self.driver.get(page)
        
        productData = ProductData("Amazon", page, prodType)
        
        productData.title = self.driver.find_element(By.ID, "productTitle").text.strip()
        unavailable_str = "N/A"
        
        # Price data
        price_data = self._getPriceData_()
        updateAttributes(price_data, productData)
        
        # Product Overview Table parsing
        info_table_data = self._parseProductOverviewTable_()
        updateAttributes(info_table_data, productData)
        
        # Prouct Details parsing
        prod_details = self._parseProductDetails_()
        updateAttributes(prod_details, productData)
        
        if productData.brand is None:
            productData.brand = prod_details.get("manufacturer", unavailable_str)
            
        ratings_data = self._parseRatings_()
        updateAttributes(ratings_data, productData)
            
        # Important information parsing
        important_info = self._parseImportantInfo_()
        updateAttributes(important_info, productData)
        
        return productData
    
    def _getPriceData_(self) -> Dict[str, str]:
        try:
            price_data = {}
            
            # Current Price
            core_price = self.driver.find_element(By.CSS_SELECTOR, "div[id*='corePrice']")
            price_el = core_price.find_element(By.CSS_SELECTOR, "span[class*='a-price']")
            price = re.sub(r"\s", ".", price_el.text)
            
            # Unit Price
            unitPrice_span = price_el.find_element(By.XPATH, "following-sibling::*[1]")
            unitPrice_str = unitPrice_span.text
            unitPrice_str = re.sub(r"[()\s+]", "", unitPrice_str)
            
            unitPrice, unitType = unitPrice_str.split(r"/")
            
            price_data['price'] = price
            price_data["unitPrice"] = unitPrice
            price_data["unitType"] = unitType
            
            return price_data
    
        except:
            return {}
        
    def _parseProductOverviewTable_(self) -> Dict[str, str]:
        try:
            info_table = self.driver.find_element(By.ID, "productOverview_feature_div").find_element(By.TAG_NAME, "table")
            info_rows = info_table.find_elements(By.TAG_NAME, "tr")
            
            values = {}
            
            for row in info_rows:                
                keyEl, valueEl = row.find_elements(By.TAG_NAME, "td")
                
                if keyEl.text in self.PRODUCT_OVERVIEW_MAP:
                    attr = self.PRODUCT_OVERVIEW_MAP[keyEl.text]     
                    values[attr] = valueEl.text
            
            return values
        
        except:
            return {}
        
    def _parseProductDetails_(self) -> Dict[str, str|int]:
        try:
            details = self.driver.find_element(By.ID, "detailBulletsWrapper_feature_div")
            
            # Main details
            main_details = details.find_element(By.TAG_NAME, "div")
            details_list = main_details.find_elements(By.TAG_NAME, "li")
            details_dict = {}
            
            for detail in details_list:
                keyEl, valueEl = detail.find_element(By.TAG_NAME, "span").find_elements(By.XPATH, "*")
                
                key = keyEl.text.replace(":", "").strip()
                
                if key in self.PRODUCT_DETAILS_MAP:
                    attr = self.PRODUCT_DETAILS_MAP[key]
                    details_dict[attr] = valueEl.text
            
            # Best seller rank (Health & Household)
            best_sellers = details.find_element(By.XPATH, "./ul[1]/li/span")
            ranking_table = best_sellers.text.split("\n")
            ranking_str = [rank for rank in ranking_table if 'Health & Household' in rank]
            
            # If health and household category exists
            if ranking_str:
                ranking_str = ranking_str[0]
                rank_str = next(value for value in ranking_str.split() if value[0] == "#")
                rank_str = rank_str.replace(",", "")
                rank = int(rank_str[1:])
            
                details_dict['rank'] = rank

            return details_dict
            
        except NoSuchElementException:
            
            try:
                table = self.driver.find_element(By.ID, "productDetails_detailBullets_sections1")
                rows = table.find_elements(By.TAG_NAME, "tr")
                
                details_dict = {}
                for row in rows:
                    keyEl, valueEl = row.find_elements(By.XPATH, "*")
                    
                    key = keyEl.text
                    if key in self.PRODUCT_DETAILS_MAP:
                        col = self.PRODUCT_DETAILS_MAP[key]
                        
                        if key != "Best Sellers Rank":
                            details_dict[col] = valueEl.text
                        else:
                            ranking_table = valueEl.text.split(r"\n")
                            ranking_str = [rank for rank in ranking_table if "Health and Household" in rank]
                            
                            if ranking_str:
                                ranking_str = ranking_str[0]
                                rank_str = next(value for value in ranking_str.split() if value[0] == "#")
                                rank_str = rank_str.replace(",", "")
                                rank = int(rank_str[1:])
                        
                                details_dict['rank'] = rank
                        
                return details_dict
                
            except:
                return {}
        
        except:
            return {}

    def _parseImportantInfo_(self) -> Dict[str, str]:
        try:
            important_info = self.driver.find_element(By.ID, "important-information")
            
            ingredients_header = important_info.find_element(By.XPATH, ".//div/h4[contains(text(), 'Ingredients')]/../p[2]")
            ingredient_str = ingredients_header.text
            
            # TODO: Manipulate ingredients string to get more relevant ingredients
            # manipulateIngredients(ingredients_str)
            
            
            return {'ingredients': ingredient_str}
            
            
        
        except:
            return {}

    def _parseRatings_(self) -> Dict[str, str|int]:

        try:
            ratings_dict = {}
            # Ratings parse
            avgRatingEl = self.driver.find_element(By.ID, "acrPopover")
            avgRating = avgRatingEl.get_attribute("title").split()[0]
            avgRating = float(avgRating)

            numRatingsEl = self.driver.find_element(By.ID, "acrCustomerReviewText")
            numRatings_str = numRatingsEl.text
            numRatings_str = numRatings_str.split()[0]
            numRatings_str = numRatings_str.replace(",", "")
            numRatings = int(numRatings_str)
            
            ratings_dict["rating"] = avgRating
            ratings_dict['numRatings'] = numRatings
            
            return ratings_dict
        except:
            return {}

    def getSearchProductLinks(self, term: str, maxResults: Optional[int]=None, page: Optional[int]=1) -> List[str]:
        
        search_link = f"{self.BASE_URL}/s?k={term}&i=hpc&crid=31LYPP9IF70TO&page={page}"
        
        self.driver.get(search_link)
        
        links = self.driver.find_elements(By.CSS_SELECTOR, "a[class*='a-link-normal s-no-outline']")
        
        ret_links = []
        
        for link in links:
            href = link.get_dom_attribute("href")
            
            is_amazon_page = href[0:4] != "http"
            sponsored_product = "gp/slredirect" in href
            
            if is_amazon_page and not sponsored_product:
                cleaned_href = href.rsplit("/ref=", 1)[0]
                
                is_full_link = "www.amazon.com" in cleaned_href
                
                if is_full_link:
                    ret_links.append(cleaned_href)
                else:
                    ret_links.append(f"{self.BASE_URL}{cleaned_href}")
                    
        unique_links = np.unique(ret_links)
        
        if max_links is not None:
            unique_links = unique_links[:max_links]
        
        return unique_links.tolist()



if __name__ == "__main__":    
    with AmazonWebInstance() as amazonUS:
        
        # url = "https://www.amazon.com/Banyan-Botanicals-Triphala-Detoxification-Rejuvenation/dp/B000Q454D8?th=1"
        searchTerm = "Neem"
        productNo = 50
        
        searchLinks = []
        
        i = 1
        while len(searchLinks) < productNo:
            
            max_links = productNo - len(searchLinks)
            newLinks = amazonUS.getSearchProductLinks(searchTerm, page=i, maxResults=max_links)
            
            searchLinks.extend(newLinks)
            i += 1
                
            # print(len(searchLinks))
        # amazonUS.driver.install_addon("noscript-11.4.14.xpi", temporary=True)
        
        data = [ amazonUS.parsePage(link, searchTerm) for link in tqdm.tqdm(searchLinks, desc="Processing webpages", unit="webpage")]
            
    data = convertDataToDataframe(data)
    data.to_csv("output.csv", index=False, sep=";", quotechar="|")
