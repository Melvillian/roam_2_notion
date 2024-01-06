import time
import sys
import json
from requests import HTTPError, JSONDecodeError
from lib.notion_api import (
    search_for_pages,
    fetch_block_children,
    extract_page_name_and_id,
    check_for_and_update_block,
    CURSOR_METADATA_FILENAME,
    NoPageFoundException,
)

# sometimes we fail for some reason on Notion's end,
# and it is a transitory failure. So we retry a few times
# but after a certain number of failed tries we abort
SLEEP_TIME_FAILURE_SECS = 10
MAX_FAILURE_TRIES = 100

if __name__ == "__main__":
    """
    Iterate through all of my Notion pages updating the page's Blocks
    to use mentions where now there are literal [[...]] markers leftover
    from the Roam Research migration
    """

    num_retries = 0
    has_more_pages = True
    while has_more_pages:
        # we wrap the main loop code in a try/except block
        # because I've noticed the Notion API sporadically returns
        # JSONDecodeErrors, but they are transitory, unimportant errors.
        # So we can simply back off for 10 seconds, and then continue
        # from the last cursor checkpoint
        try:
            # get paginated pages of metadata,
            # specifically the particular the pages' IDs
            response = search_for_pages()
            for page in response["results"]:
                page_name, page_id = extract_page_name_and_id(page)
                print(f"Page Name: {page_name}, Page ID: {page_id}")

                # process all of the page's blocks (including child blocks)
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
        except (JSONDecodeError, NoPageFoundException, HTTPError) as e:
            print(f"Transitory error found while processing:\n{e}")
            time.sleep(SLEEP_TIME_FAILURE_SECS)
            num_retries += 1
            if num_retries > MAX_FAILURE_TRIES:
                print(
                    f"failed {MAX_FAILURE_TRIES} times, giving up",
                    file=sys.stderr,
                )
                sys.exit(0)

    print(f"Done! Don't forget to delete the ./{CURSOR_METADATA_FILENAME} file")
