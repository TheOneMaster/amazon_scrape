from typing import Dict, Optional, Tuple

import requests
from bs4 import BeautifulSoup
import re

from .ProductData import ProductData, updateAttributes


class PageScrape:
    
    def __init__(self, response: requests.Response, website: str, url: str, productType: str) -> None:
        self.soup = BeautifulSoup(response.content, "lxml")
        self.productData = ProductData(website, url, productType)
        self.__process__()
        
    def __process__(self) -> None:
        raise NotImplementedError
    
    def getData(self) -> Dict[str, str|int|float]:
        return self.productData.to_dict()
    
    
class AmazonPageScrape(PageScrape):
    
    COLUMN_MAP = {
        "Item Form": "formFactor",
        "Brand": "brand",
        "Recommended Uses For Product": "uses",
        "Date First Available": "firstAvailable",
        "Manufacturer": "manufacturer",
        "ASIN": "asin",
        "Best Sellers Rank": "rank",
        "Country of Origin": "origin",
        "Manufacturer": "manufacturer",
        "Ingredients": "ingredients",
        
        # Alternative titles
        "Material Feature": "uses"
    }
    
    BASE_URL = "https://www.amazon.com"
    
    
    def __init__(self, response: requests.Response, url: str, productType: str) -> None:
        super().__init__(response, 'Amazon', url, productType)
    
    def __process__(self) -> None:
        
        try:
            self.productData.title = self.soup.find(id="productTitle").text.strip()
        except:
            pass
        
        price_data = self._getPriceData_()
        updateAttributes(price_data, self.productData)
        
        rating_data = self._getRatingData_()
        updateAttributes(rating_data, self.productData)
        
        product_data = self._getProductData_()
        updateAttributes(product_data, self.productData)
        
        self.productData.rank = self._getRank_()
    
    def __parseProductOverview__(self) -> Dict[str, str]:
        try:
            product_overview = self.soup.find(id="productOverview_feature_div")
            table = product_overview.find_all("tr")
            
            ret_dict = {}
            for row in table:
                keyEl, valueEl = row.find_all("td")
                key = keyEl.text.replace(":", "").strip()
                if key in self.COLUMN_MAP:
                    attr = self.COLUMN_MAP[key]
                    ret_dict[attr] = valueEl.text.strip()
                    
            return ret_dict
        except:
            return {}

    def __parseProductDetails__(self) -> Dict[str, str]:
        try: 
            product_details = self.soup.find(id="detailBullets_feature_div")
            rows = product_details.find_all("li")
            
            ret_dict = {}
            for row in rows:
                keyEl, valueEl = row.select("span > span")   
                
                key_text = re.sub(r"[^A-z\s]", "", keyEl.text)
                key = key_text.strip()
                
                if key in self.COLUMN_MAP:
                    attr = self.COLUMN_MAP[key]
                    ret_dict[attr] = valueEl.text.strip()
                    
            return ret_dict
        
        except:
            return {}
   
    def __parseProductInformation__(self) -> Dict[str, str]:
        try:
            info_div = self.soup.find(id="important-information")
            sections = info_div.find_all("div", recursive=False)
            
            ret_dict = {}
            for section in sections:
                heading_str = section.find("h4").text.strip()
                if (heading_str in self.COLUMN_MAP) and (getattr(self.productData, self.COLUMN_MAP[heading_str]) is None):
                    column = self.COLUMN_MAP[heading_str]
                    
                    value_El = section.find("p", string=re.compile(r"[A-z]"))
                    value = value_El.text.strip()
                    
                    ret_dict[column] = value
            
            return ret_dict
            
        except:
            return {}
    
    def _getPriceData_(self) -> Dict[str, str]:
        ret_dict = {}
        try:           
            center_div = self.soup.find(id="centerCol")
            price_div = center_div.select_one("[id*='corePrice']")
            
            if price_div.find("table"):
                price_div_el = price_div.find(string=re.compile("^Price")).parent.find_next()
                price_parts = price_div_el.findChildren("span", recursive=False)
                
                main_price = price_parts[0].findChild("span").text.strip()
                ret_dict['price'] = main_price
                
                price_per_unit = price_parts[1].text
                price_per_unit = re.sub(r"[()\s]", "", price_per_unit)
                price_per_unit, unit_type = price_per_unit.split("/")
                price_per_unit = price_per_unit[:len(price_per_unit)//2]
                
                ret_dict['unitPrice'] = price_per_unit
                ret_dict['unitType'] = unit_type
                
            else:
                price_parts = price_div.find_all(class_="a-offscreen")
                main_price = price_parts[0].text.strip()
                ret_dict["price"] = main_price
                
                price_per_unit = price_parts[1].text.strip()
                ret_dict["unitPrice"] = price_per_unit
                
                unit_type_div = price_parts[1].parent.parent
                unit_type_str = unit_type_div.text
                unit_type = unit_type_str.split("/")[1]
                unit_type = re.sub(r"[()\s]", "", unit_type)
                ret_dict["unitType"] = unit_type
            
            return ret_dict
            
        except:
            return ret_dict
    
    def _getProductData_(self) -> Dict[str, str]:
        product_overview = self.__parseProductOverview__()
        product_details = self.__parseProductDetails__()
        product_information = self.__parseProductInformation__()
        
        prod_data = product_overview | product_details | product_information
        
        if ('brand' not in prod_data) and ('manufacturer' in prod_data):
            prod_data['brand'] = prod_data.pop("manufacturer")
        
        return prod_data

    def _getRatingData_(self) -> Dict[str, str|int]:
        try:
            ret_dict = {}
            rating_str = self.soup.find(id="acrPopover").get("title")
            rating = float(rating_str.split()[0])
            
            num_ratings_str = self.soup.find(id="acrCustomerReviewText").text
            num_ratings_str = num_ratings_str.split()[0]
            num_ratings_str = num_ratings_str.replace(",", "")
            num_ratings = int(num_ratings_str)
            
            ret_dict['rating'] = rating
            ret_dict['numRatings'] = num_ratings
            
            return ret_dict
        
        except:
            return {}

    def _getRank_(self) -> Optional[int]:
        try:
            HH_elements = self.soup.find_all(string=re.compile(r"Health & Household"))
            rank_str = [ _ for _ in HH_elements if "#" in _ ][0]
            rank_str = re.sub(r"[(),]", "", rank_str).strip()
            rank_str = rank_str.split()[0]
            rank_str = rank_str[1:]
            rank_str = int(rank_str)
            
            return rank_str
        except:
            return None

class IHerbPageScrape(PageScrape):
    
    def __init__(self, response: requests.Response, url: str, productType: str) -> None:
        super().__init__(response, "Iherb", url, productType)
