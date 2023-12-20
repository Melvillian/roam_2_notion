import requests
import os
import json
import sys
from dotenv import load_dotenv
from lib.virtual_text import create_virtual_text

load_dotenv()

NOTION_KEY = os.environ.get("NOTION_KEY")
NOTION_VERSION = "2021-08-16"
NOTION_API_PREFIX = "https://api.notion.com/v1"

headers = {
    "Authorization": f"Bearer {NOTION_KEY}",
    "Content-Type": "application/json",
    "Notion-Version": NOTION_VERSION
}
# TODO: handle non-200 responses everywhere

def fetch_page(page_id):  
    url = f"{NOTION_API_PREFIX}/pages/{page_id}"
    response = requests.get(url, headers=headers)
    page_data = response.json()
    return page_data

def search_for_pages(search_query=None):
    """
    Searches for pages in the user's Notion workspace based on which pages have been shared with the integration

    Based on the Notion API key you're using, return all of the pages' properties (but not their content)
    in the user's workspace. This contains page ID's which can be used to access each page's
    content using the block API

    Args:
        search_query (str): optional page name to search for in the Notion workspace (Example: "liberalism")

    Returns:
        dict: a dictionary of page data, which looks like:
        {
            "archived": false,
            "cover": null,
            "created_by": {
                "id": "5be127e8-c6d7-4a7b-a46d-a0eb3bc9d6af",
                "object": "user"
            },
            "created_time": "2023-05-02T11:47:00.000Z",
            "icon": null,
            "id": "80b278d3-695b-43e7-bd05-e50a5d90dfdc",
            "last_edited_by": {
                "id": "5be127e8-c6d7-4a7b-a46d-a0eb3bc9d6af",
                "object": "user"
            },
            "last_edited_time": "2023-12-19T11:03:00.000Z",
            "object": "page",
            "parent": {
                "page_id": "7b1b3b0c-14cb-45a6-a4b6-d2b48faecccb",
                "type": "page_id"
            },
            "properties": {
                "title": {
                    "id": "title",
                    "title": [
                        {
                            "annotations": {
                                "bold": false,
                                "code": false,
                                "color": "default",
                                "italic": false,
                                "strikethrough": false,
                                "underline": false
                            },
                            "href": null,
                            "plain_text": "liberalism",
                            "text": {
                                "content": "liberalism",
                                "link": null
                            },
                            "type": "text"
                        }
                    ],
                    "type": "title"
                }
            },
            "public_url": null,
            "url": "https://www.notion.so/liberalism-80b278d3695b43e7bd05e50a5d90dfdc"
        }
    """

    # TODO: handle pagination

    search_params = {"filter": {
            "value": "page",
            "property": "object"
        },
        "sort": {
            "direction": "descending",
            "timestamp": "last_edited_time"
        }
    }
    if search_query:
        search_params["query"] = search_query

    search_response = requests.post(
        f'{NOTION_API_PREFIX}/search',
        json=search_params, headers=headers)

    return search_response.json()

def create_mention_section(mention_page_name):
    """
    Create a mention section for the paragraph block.

    This is the real purpose of the script, to create these mention sections for a paragraph
    """

    response = search_for_pages(mention_page_name)

    results = response["results"]
    assert len(results) == 1, f"There should only be one page with this name {mention_page_name}, but instead we found the results: {json.dumps(results, indent=4, sort_keys=True)}"
    page_id = results[0]["id"]
    href = results[0]["url"]

    new_section = {
        "annotations": {
            "bold": False,
            "code": False,
            "color": "default",
            "italic": False,
            "strikethrough": False,
            "underline": False
        },
        "href": href,
        "mention": {
            "page": {
                "id": page_id
            },
            "type": "page"
        },
        "plain_text": mention_page_name,
        "type": "mention"
    }

    return new_section

def create_text_section(section_text):
    """
    Create a text section for the paragraph block.

    This is pretty boring, because it just contains simple plaintext, no mentions
    """
    new_section = {
        "annotations": {
            "bold": False,
            "code": False,
            "color": "default",
            "italic": False,
            "strikethrough": False,
            "underline": False
        },
        "href": None,
        "plain_text": section_text,
        "text": {
            "content": section_text,
            "link": None
        },
        "type": "text"
    }

    return new_section

def update_a_block(block_id, block):
    """
    TODO
    """

    # this is the object we'll write to the Notion API to update the block
    new_paragraph_block = {
        "paragraph": {
            "color": None,
            "text": None,
        }
    }
    needs_update = False # update this to True if this block contains any literals [[...]] we need to turn into mentions
    if block["type"] == "paragraph":
        old_paragraph = block["paragraph"]
        if not old_paragraph["text"]:
            # this is a boring empty paragraph, so we do not update anything and simply return
            return
    
        # start building the new paragraph that we'll use to update (i.e. overwrite) the old paragraph block
        new_paragraph_block["paragraph"]["color"] = old_paragraph["color"]
        new_paragraph = []
        for paragraph_section in old_paragraph["text"]:
            virtual_text = create_virtual_text(paragraph_section["plain_text"])

            if not any(tup[1] for tup in virtual_text):
                # this section of paragraph doesn't contain any literal [[...]] text which should be turned
                # into mentions, so we should leave it as is by simply appending the existing old section to
                # the new paragraph's content
                new_paragraph.append(paragraph_section)
                continue
    
            needs_update = True
            # this section of paragraph contains literal [[...]] text which should be turned into mentions
            # so we'll need to build a new section for each mention and for each plaintext, and append it to the new paragraph
            for section in virtual_text:
                section_text = section[0]
                is_mention = section[1]
                new_section = create_mention_section(section_text) if is_mention else create_text_section(section_text) 
                new_paragraph.append(new_section)

        new_paragraph_block["paragraph"]["text"] = new_paragraph
    else:
        print(f"Found a non-paragraph block of type {block['type']} in block {block_id}.")
        print("BLOCK:")
        print(block)
        print("Aborting update")
        sys.exit(0)

    if not needs_update:
        print("No literal [[...]] sections found in this block, so we'll not update it.")
        return None

    print(json.dumps(old_paragraph, indent=4, sort_keys=True))

    url = f'{NOTION_API_PREFIX}/blocks/{block_id}'

    proceed = input(f"{json.dumps(new_paragraph_block, indent=4, sort_keys=True)}\ntype 'y' if you wish to proceed with the above patch update to block id: {block_id}... (y/n)")

    if proceed == "y":
        print('you proceeded')
        response = requests.patch(url, headers=headers, json=new_paragraph_block)
        return response.json()
    
    return None

def fetch_block_children(block_id, page_name):
    """
    Given a Block ID (which might also be a Page ID), return a dict keyed by all of the given
    block's childrens' IDs, and the child's data, THOUGH IT WILL ONLY RETURN CHILDREN THAT ARE
    PARAGRAPHS. The important value will be the `paragraph` field, which contains an array of
    objects of type `text` and `mention` (there could also be equation in the original block, but
    we ignore those)
    """
    # (TODO: need to handle pagination via `page_size`: see https://developers.notion.com/reference/intro#pagination)
    url = f'{NOTION_API_PREFIX}/blocks/{block_id}/children'
    response = requests.get(url, headers=headers)
    response = response.json()

    block_children = {
        "has_more": response["has_more"],
        "next_cursor": response["next_cursor"],
        "blocks": {},
    }

    for block in response["results"]:
        # (TODO: handle non-paragraph types, like: bulleted-list, headings (for their blockren), numbered list item)
        if block["type"] == "paragraph":
            block_children["blocks"][block["id"]] = {
                "has_children": block["has_children"],
                "type": block["type"],
                "paragraph": block["paragraph"],
            }
        else:
            print(f'Skipping non-paragraph block: {block["id"]}')

    if len(block_children["blocks"]) == 0:
        print(f'No children found for block: ID: {block_id} Page Name: {page_name}')


    # print("BLOCK CHILDREN:")
    # print(json.dumps(block_children, indent=4, sort_keys=True))

    return block_children


if __name__ == "__main__":
    # get paginated pages of metadata (TODO: handle pagination),
    # in particular the page ID's
    output = search_for_pages()

    # get an arbitrary page and print out useful info
    page_name = output["results"][0]["properties"]["title"]["title"][0]["plain_text"]
    page_id = output["results"][0]["id"]
    print(f"Page Name: {page_name}")
    print(f"Page ID: {page_id}")

    # print out the first-layer children on that page (TODO: recurse through block sub-children to get all data)
    block_children = fetch_block_children(page_id, page_name)
    for block_id, block in block_children["blocks"].items():
        response = update_a_block(block_id, block)
        print("UPDATE RESPONSE:")
        print(json.dumps(response, indent=4, sort_keys=True))