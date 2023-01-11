from typing import Optional, Dict, List

import pandas as pd

class ProductData:

    __slots__ = ("source", "url", "title", "brand", "productType", "price", "unitPrice", "unitType", "asin",
                 "rating", "numRatings", "rank", "formFactor", "firstAvailable", "uses", "ingredient", "origin")

    def __init__(self, source: str, url: str, productType: str, **kwargs) -> None:

        # Set all values to None
        for slot in self.__slots__:
            setattr(self, slot, None)

        self.source = source
        self.url = url
        self.productType = productType

        # Add any other arguments to the data (if any applicable)
        for kwarg in kwargs:
            if kwarg in self.__slots__:
                setattr(self, kwarg, kwargs[kwarg])

    def to_dict(self) -> Dict[str, Optional[str|int|float]]:
        ret_dict = {slot: getattr(self, slot) for slot in self.__slots__}

        return ret_dict

    def to_list(self) -> List[Optional[str|int|float]]:
        ret_list = [ getattr(self, slot) for slot in self.__slots__ ]
        
        return ret_list


def convertDataToDataframe(data: List[ProductData]) -> pd.DataFrame:
    
    data_list = [prod.to_list() for prod in data]
    columns = data[0].__slots__
    
    df = pd.DataFrame(data_list, columns=columns)
    
    return df
