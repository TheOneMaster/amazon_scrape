import typing


import requests
from bs4 import BeautifulSoup
import re

from .string_manip import getOtherIngredients


class ProductData:
    
    def __init__(self, response: requests.Response, url: str, productType: str) -> None:
    
        self._soup = BeautifulSoup(response.content, "lxml")
        
        self._details = {
            "source": None,
            "url": url,
            "title": None,
            "brand": None,
            "asin": None,
            "productType": productType,
            "price": None,
            "unitType": None,
            "unitPrice": None,
            "rating": None,
            "numRatings": None,
            "formFactor": None,
            "firstAvailable": None,
            "uses": None,
            "ingredients": None
        }

    def to_list(self) -> list:
        
        return self._details.values()
    
    @property
    def columns(self) -> typing.List[str]:
        
        return self._details.keys()


    def _getTitle_(self) -> None:
        raise NotImplementedError
    
    def _getBrand_(self) -> None:
        raise NotImplementedError

    def _getASIN_(self) -> None:
        raise NotImplementedError
    
    def _getPrice_(self) -> None:
        raise NotImplementedError

    def _getPricePerUnit_(self) -> None:
        raise NotImplementedError

    def _getRating_(self) -> None:
        raise NotImplementedError

    def _getNumRatings_(self) -> None:
        raise NotImplementedError

    def _getFormFactor_(self) -> None:
        raise NotImplementedError

    def _getFirstAvailable_(self) -> None:
        raise NotImplementedError

    def _getUses_(self) -> None:
        raise NotImplementedError

    def _getIngredients_(self) -> None:
        raise NotImplementedError

    def __process__(self) -> None:

        self._details["title"] = self._getTitle_()
        self._details["brand"] = self._getBrand_()
        self._details["asin"] = self._getASIN_()
        self._details["price"] = self._getPrice_()
         
        self._details["rating"] = self._getRating_()
        self._details["numRatings"] = self._getNumRatings_()
        self._details["formFactor"] = self._getFormFactor_()
        self._details["firstAvailable"] = self._getFirstAvailable_()
        self._details["uses"] = self._getUses_()
        self._details["ingredients"] = self._getIngredients_()


class AmazonProductData(ProductData):

    def __init__(self, response: requests.Response, url: str, productType: str) -> None:
        super().__init__(response, url, productType)
        
        self._details['rank'] = None
        self._details['source'] = "Amazon"


        self.__process__()     

  
    def _getTitle_(self) -> str:

        try: 
            title = self._soup.find("span", attrs={"id": "productTitle"})

            title_value = title.string
            title_str = title_value.strip()

        except AttributeError:
            title_str = "Unknown"

        return title_str

    def _getBrand_(self) -> str:

        brand_row = self._soup.find("tr", attrs={
            "class": "a-spacing-small po-brand"
        })
        
        if brand_row:
        
            brand_span = brand_row.find("span", attrs={
                "class": "po-break-word"
            })
            
            brand_str = brand_span.string

            
            brand_str = brand_str.strip()
            
            return brand_str
        
        details_table = self._soup.find(id="detailBullets_feature_div")
        
        try:  
            manufacturer_row = details_table.find("span", string=re.compile("^Manufacturer"))
            manufacturer_span = manufacturer_row.find_next_sibling()
            
            return manufacturer_span.string.strip()
        
        except:
            return "Unknown"

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
                "class": ["a-price a-text-price a-size-medium apexPriceToPay", "a-price aok-align-center"]
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
    
    def _getUses_(self) -> str:

        try:
        
            recommended_row = self._soup.find("tr", attrs={
                "class": "a-spacing-small po-recommended_uses_for_product"
            })
            
            if recommended_row:
                recommended_uses_span = recommended_row.find("span", attrs={
                    "class": "a-size-base po-break-word"
                })
                
                recommended_uses = recommended_uses_span.string
            
            return recommended_uses
        
        except:
            return "N/A"
    
    def _getIngredients_(self) -> str:

        try:
            information_div = self._soup.find(id="importantInformation_feature_div")
            ingredients_div = information_div.find("h4", string=re.compile("^Ingredients")).parent
            ingredients_str = ingredients_div.find_all("p")[-1].string.strip()

            ingredients = getOtherIngredients(ingredients_str, self._details['productType'])
            ingredients = ", ".join(ingredients)

            return ingredients

        except:
            return None

        # try:
        #     product_overview_div = self._soup.find(id="productOverview_feature_div")
        #     benefits = 

        # except


    def __process__(self) -> None:
        
        super().__process__()

        self._details["unitType"], self._details["unitPrice"] = self._getPricePerUnit_()
        self._details["rank"] = self._getBestSellerRank_()
        


class IHerbProductData(ProductData):
    
    def __init__(self, response: requests.Response, url: str, productType: str) -> None:
        super().__init__(response, url, productType)



        
            
            
    
    
    
    