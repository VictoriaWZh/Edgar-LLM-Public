from bs4 import BeautifulSoup as bs
import requests
import os
import unicodedata

TAGS_TO_GET = ["h1", "h2", "h3", "h4", "h5", "h6", "p"]

def get_data(content):
    content_string = ""
    for tag in content.find_all():
        if tag.name in TAGS_TO_GET:
            examining_string = unicodedata.normalize("NFKD", str(tag.get_text(strip=True)))
            content_string += examining_string + " "
    return content_string

def get_eps_data(url, sidebar_id):
    data = " "

    try:
        response = requests.get(url)
        response.raise_for_status()
        soup = bs(response.content, 'lxml')

        sidebar = soup.find("ul", {"id": sidebar_id})
        if not sidebar:
            raise ValueError(f"Sidebar with ID '{sidebar_id} not found on the page.")

        links = sidebar.find_all("a", href=True)
        if not links:
            raise ValueError("No links found in the sidebar")

    # Get all the stuff from all the links
        for link_html in links:
            link_url = link_html['href']
            if not link_url.startswith("http"):
                link_url = requests.compat.urljoin(url, link_url)
            
            try:
                link_response = requests.get(link_url)
                link_response.raise_for_status()
                link_soup = bs(link_response.content, 'lxml')
                data += get_data(link_soup)
            except requests.RequestException as e:
                print(f"Failed to fetch or process link: {link_url}. Error {e}")

    except requests.RequestException as e:
        print(f"Failed to fetch main page {url}. Error: {e}")

    return data

def do_export(data_unfiltered, filename):
    os.makedirs("./data", exist_ok=True)

    filepath = os.path.join("./data", f"{filename}.txt")
    with open(filepath, 'w', encoding="utf-8") as txt:
        txt.write(str(data_unfiltered))
    print(f"Data successfully saved to {filepath}")

admissions = get_eps_data('https://www.eastsideprep.org/admissions/', "menu-admissions")
do_export(admissions, 'admissions')