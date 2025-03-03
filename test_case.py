import bs4
import requests

def parse_case(case_url: str):
    # Get the page content using requests
    response = requests.get(case_url)
    
    # Get page source and create BeautifulSoup object
    soup = bs4.BeautifulSoup(response.text, "html.parser")
    
    # Find all divs with class paragWrapper
    parag_divs = soup.find_all("div", class_="paragWrapper")
    
    # Extract text from each div
    texts = []
    for div in parag_divs:
        texts.append(div.get_text())
        
    return "\n".join(texts)


print(parse_case("https://www.canlii.org/en/on/onsc/doc/2025/2025onsc1/2025onsc1.html"))