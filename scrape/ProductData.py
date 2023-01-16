from typing import Dict, List, Any

class ProductData:
    
    __slots__ = ("source", "url", "title", "brand", "productType", "asin", "price", "unitPrice", "unitType", "rank",
                 "rating", "numRatings", "formFactor", "firstAvailable", "uses", "ingredients", "origin")
    
    def __init__(self, source: str, url: str, productType: str, **kwargs) -> None:
        
        for slot in self.__slots__:
            setattr(self, slot, None)
        
        self.source = source
        self.url = url
        self.productType = productType
        
        for kwarg in kwargs:
            if kwarg in self.__slots__:
                setattr(self, kwarg, kwargs[kwarg])
                
    def to_dict(self) -> Dict[str, Any]:
        ret_dict = { slot: getattr(self, slot) for slot in self.__slots__ }
        return ret_dict
    
    def to_list(self) -> List[Any]:
        ret_list = [ getattr(self, slot) for slot in self.__slots__ ]
        return ret_list
        
def updateAttributes(attrs: dict, current_data: ProductData) -> None:
    for attr in attrs:
        if attr in current_data.__slots__:
            setattr(current_data, attr, attrs[attr])
