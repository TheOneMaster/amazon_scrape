from scrape import getDataFromSearch


if __name__ == "__main__":

    base_url = "https://www.amazon.com"
    search_term = "Ashwagandha"
    
    getDataFromSearch(base_url, search_term)
    

