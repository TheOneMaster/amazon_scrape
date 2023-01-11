from typing import Type, overload, Dict, Any
from types import TracebackType

from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

import re

from ProductData import ProductData


def updateAttributes(new_data: Dict[str, Any], current_data: ProductData):
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
    
    def __init__(self, headless=False) -> None:
        
        self.options = Options()
        self.options.headless = headless
        
        self.driver = webdriver.Firefox(options=self.options)
        
        amazon_url = "https://www.amazon.com"
        
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
            
        # Important information parsing
        important_info = self._parseImportantInfo_()
        updateAttributes(important_info, productData)
        
        return productData
    
    def _getPriceData_(self) -> Dict[str, str]:
        try:
            price_data = {}
            
            # Current Price
            core_price = self.driver.find_element(By.ID, "corePrice_desktop")
            price_el = core_price.find_element(By.CSS_SELECTOR, ".a-price.a-text-price")
            price = price_el.text.strip()
            
            # Unit Price
            unitPrice_span = price_el.find_element(By.XPATH, "following-sibling::*[1]")
            unitPrice_str = unitPrice_span.text
            unitPrice_str = re.sub(r"[()\s+]", "", unitPrice_str)
            
            unitPrice, unitType = unitPrice_str.split(r"/")
            
            price_data['price'] = price
            price_data["unitPrice"] = unitPrice
            price_data["unitType"] = unitType
            
            return price_data
    
        except AttributeError:
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
        
        except AttributeError:
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
                
                key = keyEl.text[:-2]
                
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

            # Ratings parse
            avgRatingEl = self.driver.find_element(By.ID, "acrPopover")
            avgRating = avgRatingEl.get_attribute("title").split()[0]
            avgRating = float(avgRating)

            numRatingsEl = self.driver.find_element(By.ID, "acrCustomerReviewText")
            numRatings_str = numRatingsEl.text
            numRatings_str = numRatings_str.split()[0]
            numRatings_str = numRatings_str.replace(",", "")
            numRatings = int(numRatings_str)
            
            details_dict["rating"] = avgRating
            details_dict['numRatings'] = numRatings

            return details_dict
            
        except AttributeError:
            return {}

    def _parseImportantInfo_(self) -> Dict[str, str]:
        try:
            important_info = self.driver.find_element(By.ID, "important-information")
            
            ingredients_header = important_info.find_element(By.XPATH, ".//div/h4[contains(text(), 'Ingredients')]/../p[2]")
            ingredient_str = ingredients_header.text
            
            # TODO: Manipulate ingredients string to get more relevant ingredients
            # manipulateIngredients(ingredients_str)
            
            
            return {'ingredients': ingredient_str}
            
            
        
        except AttributeError:
            return {}



if __name__ == "__main__":    
    with AmazonWebInstance() as amazonUS:
        
        url = "https://www.amazon.com/Banyan-Botanicals-Triphala-Detoxification-Rejuvenation/dp/B000Q454D8?th=1"
        data = amazonUS.parsePage(url, 'Triphala')
        
        print(data.to_dict())
