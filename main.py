import requests
import os
import json
from dotenv import load_dotenv

load_dotenv()

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

# def update_page(page_id, properties):
#     url = f"{NOTION_API_PREFIX}/pages/{page_id}"
#     data = {
#         "properties": properties
#     }
#     response = requests.patch(url, headers=headers, json=data)
#     updated_page_data = response.json()
#     return updated_page_data

def search_for_pages():
    """
    Searches for pages in the user's Notion workspace based on the workspace they're using

    Based on the Notion API key you're using, return all of the pages (but not their content)
    in the user's workspace. This contains page ID's which can be used to access each page's
    content using the block API
    """

    search_params = {"filter": {
            "value": "page",
            "property": "object"
        },
        "sort": {
            "direction": "descending",
            "timestamp": "last_edited_time"
        }
    }
    search_response = requests.post(
        f'{NOTION_API_PREFIX}/search',
        json=search_params, headers=headers)

    return search_response.json()



def fetch_block_children(block_id):
    url = f"{NOTION_API_PREFIX}/blocks/{block_id}/children"
    response = requests.get(url, headers=headers)
    response = response.json()

    has_more = response["has_more"]
    next_cursor = response["next_cursor"]

    print("RESPONSE:")
    print(json.dumps(response, indent=4, sort_keys=True))

    children_data = {
        "has_more": has_more,
        "next_cursor": next_cursor,
    }

    for child in response["results"]:
        children_data[child["id"]] = {
            "has_children": child["has_children"],
            "type": child["type"]
        }
    
    return children_data

if __name__ == "__main__":
    # get paginated pages of metadata (TODO: handle pagination),
    # in particular the page ID's
    output = search_for_pages()

    # debug: beautify and print json output
    print(json.dumps(output["results"][0], indent=4, sort_keys=True))

    # get an arbitrary page and print out the first-layer children on that page (TODO: recurse through block children to get all data)
    page_id = output["results"][0]["id"]
    print(f"Page ID: {page_id}")
    block_children = fetch_block_children(page_id)
    print(json.dumps(block_children, indent=4, sort_keys=True))