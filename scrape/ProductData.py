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
    
    def to_dict(self) -> dict: 
        ret_dict = {}
        
        for slot in self.__slots__:
            ret_dict[slot] = getattr(self, slot)

        return ret_dict
