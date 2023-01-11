import typing

import re

def getOtherIngredients(ingredientString: str, mainIngredient: str) -> typing.List[str]:
    """ Return the list of ingredients from the string other than the ones that include the main ingredient
    """

    # Remove unneccessary parts of the string (Ex: other ingredients: )
    # 
    # Explanation for the Regex:
    # The first square bracket matches any of the potential seperators (, . ; -)
    # The second one matches any character except the seperators and can be repeated infinitely (using the * symbol)
    # Finally, end when a : symbol is found, end the regex match
    
    remove_unneccessary_text = re.sub(r"[.;,-][^.;,-]*:", "", ingredientString)
    
    # Split on any of the seperators not in parentheses and subsequent whitespace
    # Explanation here: https://stackoverflow.com/questions/24197423/replace-a-comma-that-is-not-in-parentheses-using-regex

    ingredient_list = re.split(r"[,.;-](?![^()]*\))\s*", remove_unneccessary_text)

    # Return any ingredient that does not include the main ingredient
    ingredients_not_main = [ingredient for ingredient in ingredient_list if mainIngredient not in ingredient]

    return ingredients_not_main