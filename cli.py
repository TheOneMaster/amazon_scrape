import argparse
import gspread
from gspread.utils import ValueInputOption

from scrape import getDataFromSearch

def check_positive_values(value: int) -> int:
    
    ivalue = int(value)
    if ivalue <= 0:
        raise argparse.ArgumentTypeError(f"{value} is an invalid positive int value")
    
    return ivalue

def createParser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="Website Scraping Tool",
        description="Get product details for all products from amazon search",
        usage="cli.py [-h] website searchTerm startRow [--sheet SHEET] [--maxProducts MAXPRODUCTS]"
    )
    
    spreadsheet_url = "https://docs.google.com/spreadsheets/d/1dVa8Oc8OSH_UtncNKjlyMPgkMAlDMdEYzDXC1RkcKVE/edit#gid=0"
    
    required = parser.add_argument_group("required arguments")
    optional = parser.add_argument_group("optional arguments")

    required.add_argument("website", choices=['Amazon', 'IHerb'], type=str,
                          metavar="website",
                          help="Choose the website to parse (Amazon, IHerb)")
    
    required.add_argument("searchTerm", type=str,
                          help="The term used for the search")
    
    required.add_argument("startRow", type=check_positive_values,
                          help="The row used to start dumping the product details")
    
    optional.add_argument("--sheet", type=str,
                          default=spreadsheet_url, required=False,
                          help="The url for the sheet used to dump the product info")
    
    optional.add_argument("--maxProducts", type=check_positive_values,
                          default=None, required=False,
                          help="The maximum number of products")
    
    return parser

def main(website: str, search_term: str, sheet: gspread.Worksheet, startRow: int, maxProducts=None) -> None:

    column_map = {
        "source": "A",
        "title": "B",
        "brand": "C",
        "url": "D",
        "asin": "E",
        "productType": "F",
        "ingredients": "H",
        "price": "I",
        "firstAvailable": "L",
        "numRatings": "M",
        "rating": "N",
        "rank": "O",
        "formFactor": "Q",
        "uses": "U",
        "pricePerCount": 'J',
        "pricePerOz": 'K'
    }

    header = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/5312 (KHTML, like Gecko) Chrome/38.0.866.0 Mobile Safari/5312"
    }

    product_data = getDataFromSearch(website, search_term, headers=header, maxProducts=maxProducts)



    columns = product_data.columns
    numProducts = len(product_data)

    # Update sheet for all columns except unitType and unitPrice
    for column in columns:

        data = product_data[column].astype(str)
        # data = data.fillna("")
        excel_column = column_map[column]

        if column in ['pricePerCount', 'pricePerOz']:
            data = data.fillna("")

        column_data = data.to_numpy().reshape(-1, 1).tolist()

        sheet.update(f"{excel_column}{startRow}:{excel_column}{startRow+numProducts}", column_data, value_input_option=ValueInputOption.user_entered)

if __name__ == "__main__":
    
    parser = createParser()
    args = parser.parse_args()
    
    website = args.website
    searchTerm = args.searchTerm
    startRow = args.startRow
    
    sheet = args.sheet
    maxProducts = args.maxProducts
    
    gc = gspread.service_account()
    spreadsheet = gc.open_by_url(sheet)
    worksheet = spreadsheet.worksheet("Product List")
    
    main(website, searchTerm, sheet, startRow=startRow, maxProducts=maxProducts)
    