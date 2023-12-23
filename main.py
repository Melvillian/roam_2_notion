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
        dict: a dictionary of search result data, which includes cursor fields as well as a `results` list
        {
            "object": "list",
            "results": [
                {
                    "object": "page",
                    "id": "afb8dbd2-1d10-43da-bc15-87d6f6c682aa",
                    "created_time": "2023-06-22T12:40:00.000Z",
                    "last_edited_time": "2023-12-20T20:39:00.000Z",
                    "created_by": {
                        "object": "user",
                        "id": "5be127e8-c6d7-4a7b-a46d-a0eb3bc9d6af"
                    },
                    "last_edited_by": {
                        "object": "user",
                        "id": "5be127e8-c6d7-4a7b-a46d-a0eb3bc9d6af"
                    },
                    "cover": null,
                    "icon": null,
                    "parent": {
                        "type": "page_id",
                        "page_id": "7b1b3b0c-14cb-45a6-a4b6-d2b48faecccb"
                    },
                    "archived": false,
                    "properties": {
                        "title": {
                            "id": "title",
                            "type": "title",
                            "title": [
                                {
                                    "type": "text",
                                    "text": {
                                        "content": "cyberwizard",
                                        "link": null
                                    },
                                    "annotations": {
                                        "bold": false,
                                        "italic": false,
                                        "strikethrough": false,
                                        "underline": false,
                                        "code": false,
                                        "color": "default"
                                    },
                                    "plain_text": "cyberwizard",
                                    "href": null
                                }
                            ]
                        }
                    },
                    "url": "https://www.notion.so/cyberwizard-afb8dbd21d1043dabc1587d6f6c682aa",
                    "public_url": null
                },
                ...
            ],
            "next_cursor": "3ad0febc-4d86-4fda-882d-ee902cf66fb8",
            "has_more": true,
            "request_id": "a20cf866-9d69-45cf-a62a-f88d9159d7ad"
        }
    """

    # TODO: handle pagination

    search_params = {"filter": {
            "value": "page",
            "property": "object"
        },
        "sort": {
            "direction": "ascending",
            "timestamp": "last_edited_time"
        }
    }

    if search_query:
        # if you don't provide a query, then it will search all pages connected to the Notion integration
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
    PARAGRAPHS.
    
    The important value will be the `paragraph` field, which contains an array of
    objects of type `text` and `mention` (there could also be equation in the original block, but
    we ignore those)

    Returns:
        dict: a dict keyed by block ID, and the value is a dict containing the block's type. For example:
        {
            "blocks": {
                "13b5fa46-4308-4e19-a22b-67d440a017b6": {
                    "has_children": false,
                    "paragraph": {
                        "color": "default",
                        "text": []
                    },
                    "type": "paragraph"
                },
                "407c0a7b-5759-461c-a082-59c52f670bf5": {
                    "has_children": false,
                    "paragraph": {
                        "color": "default",
                        "text": [
                            {
                                "annotations": {
                                    "bold": false,
                                    "code": false,
                                    "color": "default",
                                    "italic": false,
                                    "strikethrough": false,
                                    "underline": false
                                },
                                "href": "https://www.notion.so/8d16c7abf8a74c7a8fee597edc05cafa",
                                "mention": {
                                    "page": {
                                        "id": "8d16c7ab-f8a7-4c7a-8fee-597edc05cafa"
                                    },
                                    "type": "page"
                                },
                                "plain_text": "Capitalist Manifesto",
                                "type": "mention"
                            },
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
                                "plain_text": " is a good book to read on this subject, as well as ",
                                "text": {
                                    "content": " is a good book to read on this subject, as well as ",
                                    "link": null
                                },
                                "type": "text"
                            },
                            {
                                "annotations": {
                                    "bold": false,
                                    "code": false,
                                    "color": "default",
                                    "italic": false,
                                    "strikethrough": false,
                                    "underline": false
                                },
                                "href": "https://www.notion.so/3cdb2c5ad41e4a8d8321d36cf14947a9",
                                "mention": {
                                    "page": {
                                        "id": "3cdb2c5a-d41e-4a8d-8321-d36cf14947a9"
                                    },
                                    "type": "page"
                                },
                                "plain_text": "Karl Marx",
                                "type": "mention"
                            },
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
                                "plain_text": "  since they are opposed to each other, especially now. One more is ",
                                "text": {
                                    "content": "  since they are opposed to each other, especially now. One more is ",
                                    "link": null
                                },
                                "type": "text"
                            },
                            {
                                "annotations": {
                                    "bold": false,
                                    "code": false,
                                    "color": "default",
                                    "italic": false,
                                    "strikethrough": false,
                                    "underline": false
                                },
                                "href": "https://www.notion.so/18c9042fe0b743c8943769c8b668720c",
                                "mention": {
                                    "page": {
                                        "id": "18c9042f-e0b7-43c8-9437-69c8b668720c"
                                    },
                                    "type": "page"
                                },
                                "plain_text": "venture capital",
                                "type": "mention"
                            },
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
                                "plain_text": " ",
                                "text": {
                                    "content": " ",
                                    "link": null
                                },
                                "type": "text"
                            }
                        ]
                    },
                    "type": "paragraph"
                },
                "7ea896f8-6b29-4928-9883-e82625417bf4": {
                    "has_children": false,
                    "paragraph": {
                        "color": "default",
                        "text": []
                    },
                    "type": "paragraph"
                },
                "832edff3-8520-49ee-925f-17f5c5c7175e": {
                    "has_children": false,
                    "paragraph": {
                        "color": "default",
                        "text": [
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
                                "plain_text": "another one ",
                                "text": {
                                    "content": "another one ",
                                    "link": null
                                },
                                "type": "text"
                            }
                        ]
                    },
                    "type": "paragraph"
                }
            },
            "has_more": false,
            "next_cursor": null
        }
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

    return block_children


if __name__ == "__main__":
    # get paginated pages of metadata (TODO: handle pagination),
    # in particular the page ID's
    output = search_for_pages()

    for page in output["results"]:

        # get an arbitrary page and print out useful info
        title_data = page["properties"]["title"]["title"]
        assert len(title_data) == 1, f"only one title allowed per page, but found {len(title_data)} for page:\n{page_name}"
        page_name = title_data[0]["plain_text"]
        assert page_name == title_data[0]["text"]["content"], f"title data is not consistent: {page_name}, {title_data[0]['text']['content']}"
        page_id = page["id"]
        print(f"Page Name: {page_name}")
        print(f"Page ID: {page_id}")

        # process the first-layer children on that page (TODO: recurse through block sub-children to get all data)
        block_children = fetch_block_children(page_id, page_name)
        for block_id, block in block_children["blocks"].items():
            response = update_a_block(block_id, block)