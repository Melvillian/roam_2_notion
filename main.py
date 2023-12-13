import requests
import os

NOTION_KEY = os.environ.get("NOTION_KEY")
NOTION_VERSION = "2021-08-16"
NOTION_API_PREFIX = "https://api.notion.com/v1"

headers = {
    "Authorization": f"Bearer {NOTION_KEY}",
    "Content-Type": "application/json",
    "Notion-Version": NOTION_VERSION
}

def fetch_page(page_id):
    url = f"{NOTION_API_PREFIX}/pages/{page_id}"
    response = requests.get(url, headers=headers)
    page_data = response.json()
    return page_data

def update_page(page_id, properties):
    url = f"{NOTION_API_PREFIX}/pages/{page_id}"
    data = {
        "properties": properties
    }
    response = requests.patch(url, headers=headers, json=data)
    updated_page_data = response.json()
    return updated_page_data

def search_for_pages():
    search_params = {"filter": {"value": "page", "property": "object"}}
    search_response = requests.post(
        f'{NOTION_API_PREFIX}/search', 
        json=search_params, headers=headers)

    print(search_response.json())

search_for_pages()