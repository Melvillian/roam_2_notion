import os
import json
import sys
from dotenv import load_dotenv
from lib.virtual_text import create_virtual_text
from lib.request_rate_limiter import get, post, patch

load_dotenv()

NOTION_KEY = os.environ.get("NOTION_KEY")
NOTION_VERSION = "2021-08-16"
NOTION_API_PREFIX = "https://api.notion.com/v1"
CURSOR_METADATA_FILENAME = "cursor_metadata.json"

# TODO: make use of matching via something like:
# https://stackoverflow.com/questions/16258553/how-can-i-define-algebraic-data-types-in-python
# These are all of the Notion block types that we believe contain [[...]]
# literals and we will want to process. You can see the full list here:
# https://developers.notion.com/reference/block#block-type-objects
BLOCK_TYPES_TO_PROCESS = [
    "paragraph",
    "bulleted_list_item",
    "heading_1",
    "heading_2",
    "heading_3",
    "numbered_list_item",
    "toggle",
]

HEADERS = {
    "Authorization": f"Bearer {NOTION_KEY}",
    "Content-Type": "application/json",
    "Notion-Version": NOTION_VERSION,
}
# TODO: handle non-200 responses everywhere


def debug_print(header, message):
    """
    Simple helper function to print debug messages to the console, used for debugging

    Should delete this before deploying to production
    """
    print(f"DEBUG: {header}:\n{message}")


def search_for_pages(search_query=None):
    """
    Searches for pages in the user's Notion workspace

    Based on the Notion API key you're using and the pages that have been
    shared with the key's integration, return all of the pages' properties
    (but not their content) in the user's workspace. This contains page ID's
    which can be used to access each page's content using the block API

    Args:
        search_query (str): Page name to search for. If None, for search all Pages

    Returns:
        dict: a dictionary of search results and cursor data
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

    search_params = {
        "filter": {"value": "page", "property": "object"},
        "sort": {"direction": "ascending", "timestamp": "last_edited_time"},
    }

    if search_query:
        # if you don't provide a query, then it will search all pages
        # connected to the Notion integration
        search_params["query"] = search_query
    else:
        # we must be searching through all the pages, so this is the cursor
        # that will be used to fetch the next page of results
        next_cursor = None
        # we store the cursor data in a file in case the script fails partway
        # and we need to start from where we left off
        if os.path.isfile(CURSOR_METADATA_FILENAME):
            with open(CURSOR_METADATA_FILENAME) as f:
                cursor_metadata = json.load(f)
                next_cursor = cursor_metadata["next_cursor"]
        if next_cursor:
            debug_print("next_cursor", next_cursor)
            search_params["start_cursor"] = next_cursor

    search_response = post(
        f"{NOTION_API_PREFIX}/search", json=search_params, headers=HEADERS
    )

    return search_response.json()


def generate_mention_section(mention_page_name):
    """
    Create a mention section for the block.

    This is the real purpose of the script, to create these mention sections
    for sections of text that currently contain mentions to other pages, but
    using the literal [[...]] syntax from Roam Research
    """

    print(f"Creating mention section for {mention_page_name}")

    response = search_for_pages(mention_page_name)

    results = response["results"]
    # sometimes there exist page names that are substrings of other page
    # names, for instance when searching "HackerDAO" brings up 2 pages:
    # 'HackerDAO' and 'HackerDAO TODO'. In all these cases we know we
    # want the page with the exact name match `HackerDAO`, so we'll filter
    # down to just that one page
    matched_results = list(
        filter(
            lambda result: result["properties"]["title"]["title"][0]["plain_text"]
            == mention_page_name,
            response["results"],
        )
    )
    assert len(matched_results) == 1, (
        f"There should only be one page with this name {mention_page_name}, "
        f"but instead we found the results: "
        f"{json.dumps(results, indent=4, sort_keys=True)}"
    )
    page_id = matched_results[0]["id"]
    href = matched_results[0]["url"]

    new_section = {
        "annotations": {
            "bold": False,
            "code": False,
            "color": "default",
            "italic": False,
            "strikethrough": False,
            "underline": False,
        },
        "href": href,
        "mention": {"page": {"id": page_id}, "type": "page"},
        "plain_text": mention_page_name,
        "type": "mention",
    }

    return new_section


def generate_text_section(section_text):
    """
    Create a text section for the block.

    This is pretty boring, because it just contains simple plaintext,
    no mentions
    """
    new_section = {
        "annotations": {
            "bold": False,
            "code": False,
            "color": "default",
            "italic": False,
            "strikethrough": False,
            "underline": False,
        },
        "href": None,
        "plain_text": section_text,
        "text": {"content": section_text, "link": None},
        "type": "text",
    }

    return new_section


def check_for_and_update_block(block_id, block):
    """
    Check if a block contains any [[...]] literals, and if so,
    update the block in Notion so that all literal [[...]] are replaced with
    mentions.

    Replaces block data that looks like this:

    ```json
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
        "plain_text": "[[Capital Manifesto]] is a good book to read on this subject, as well as ",
        "text": {
            "content": "[[Capital Manifesto]] is a good book to read on this subject, as well as ",
            "link": null
        },
        "type": "text"
    },
    ```

    with this, where the [[...]] has been removed and replaced with a mention
    section:

    ```json
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
    }
    ```
    """

    old_content = block["content"]
    if not old_content["text"]:
        # this is a boring empty block, so we do not update
        # anything and simply return
        return

    # update this to True if this block contains any
    # literals [[...]] we need to turn into mentions
    needs_update = False

    # start building the new block content that we'll use to overwrite
    # (i.e. overwrite) the old block contents
    new_content = []
    for content_section in old_content["text"]:
        virtual_text = create_virtual_text(content_section["plain_text"])

        if not any(tup[1] for tup in virtual_text):
            # this section of the block doesn't contain any literal [[...]]
            # text which should be turned into mentions, so we should leave
            # it as is by simply appending the existing old section to the
            # new block's content
            new_content.append(content_section)
            continue

        needs_update = True
        # this section of block contains literal [[...]] text
        # which should be turned into mentions so we'll need to
        # build a new section for each mention and for each plaintext,
        # and append it to the new block
        for section in virtual_text:
            section_text = section[0]
            is_mention = section[1]
            new_section = (
                generate_mention_section(section_text)
                if is_mention
                else generate_text_section(section_text)
            )
            new_content.append(new_section)

    if not needs_update:
        print(
            (
                "No literal [[...]] sections found in this block,"
                " so we'll not update it."
            )
        )
        return

    # this is the object we'll write to the Notion API to update the block
    block_type = block["type"]
    new_content_block = {
        block_type: {
            "color": old_content["color"],
            "text": new_content,
        }
    }

    debug_print("OLD CONTENT", json.dumps(old_content, indent=4, sort_keys=True))

    proceed = input(
        (
            f"{json.dumps(new_content_block, indent=4, sort_keys=True)}\n"
            "type 'y' if you wish to proceed with the above patch update to"
            f"block id: {block_id}... (y/n)"
        )
    )

    if proceed == "y":
        url = f"{NOTION_API_PREFIX}/blocks/{block_id}"
        patch(url, headers=HEADERS, json=new_content_block)


def fetch_block_children(page_id):
    """
    Given a Page ID , return a dict keyed by
    all of the given page's block childrens' IDs, and the child's data

    The important value will be the `content` field, which contains an
    array of objects of type `text` and `mention` (there could also be equation
    in the original block, but we ignore those)

    Returns:
        dict: a dict keyed by block ID, and the value is a dict containing the
        block's type. For example:
        ```json
        {
            "13b5fa46-4308-4e19-a22b-67d440a017b6": {
                "has_children": false,
                "content": {
                    "color": "default",
                    "text": []
                },
                "type": "paragraph"
            },
            "407c0a7b-5759-461c-a082-59c52f670bf5": {
                "has_children": false,
                "content": {
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
                "content": {
                    "color": "default",
                    "text": []
                },
                "type": "paragraph"
            },
            "832edff3-8520-49ee-925f-17f5c5c7175e": {
                "has_children": false,
                "content": {
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
        }
        ```
    """

    has_more = True
    next_cursor = None
    block_children = {}
    base_url = f"{NOTION_API_PREFIX}/blocks/{page_id}/children"

    while has_more:
        url = base_url
        if next_cursor:
            print(f"using block pagination start_cursor: {next_cursor}")
            url += f"?start_cursor={next_cursor}"
        response = get(url, headers=HEADERS)
        response = response.json()

        debug_print("BLOCK RESPONSE", json.dumps(response, indent=4, sort_keys=True))

        for block in response["results"]:
            if block["type"] in BLOCK_TYPES_TO_PROCESS:
                block_type = block["type"]
                block_children[block["id"]] = {
                    "has_children": block["has_children"],
                    "type": block_type,
                    "content": block[block_type],
                }
                if block["has_children"]:
                    debug_print(
                        "NON PARAGRAPH WITH CHILDREN",
                        json.dumps(response, indent=4, sort_keys=True),
                    )
                    sys.exit(0)

        has_more = response["has_more"]
        next_cursor = response["next_cursor"]

    return block_children


def extract_page_name_and_id(page):
    """
    Helper function to extract the page name and ID from a page object.
    """
    title_data = page["properties"]["title"]["title"]
    assert len(title_data) == 1, (
        f"only one title allowed per page, but found {len(title_data)}"
        f"for page:\n{title_data[0]['plain_text']}"
    )
    page_name = title_data[0]["plain_text"]
    assert page_name == title_data[0]["text"]["content"], (
        f"title data is not consistent: "
        f"{page_name}, {title_data[0]['text']['content']}"
    )
    page_id = page["id"]
    return page_name, page_id


if __name__ == "__main__":
    """
    Iterate through all of my Notion pages and their first-layer children,
    updating the page's Blocks to use mentions where now there are literal
    [[...]] markers leftover from the Roam Research migration
    """

    has_more_pages = True
    while has_more_pages:
        # get paginated pages of metadata,
        # specifically the particular the page ID's
        response = search_for_pages()

        for page in response["results"]:
            page_name, page_id = extract_page_name_and_id(page)
            print(f"Page Name: {page_name}")
            print(f"Page ID: {page_id}")

            # process the first-layer children on that page
            # (TODO: recurse through block sub-children to get all data)
            block_children = fetch_block_children(page_id)
            for block_id, block in block_children.items():
                check_for_and_update_block(block_id, block)

        if response["has_more"]:
            # save the cursor data in case the script fails partway
            # and we need to resume from where we left off
            with open(CURSOR_METADATA_FILENAME, "w") as f:
                cursor_data = {"next_cursor": response["next_cursor"]}
                json.dump(cursor_data, f)

        has_more_pages = response["has_more"]
