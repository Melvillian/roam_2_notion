# roam_2_notion

A small script for converting any Notion pages that have been imported from Roam
(which uses the literal `[[some category]]` or backlinks) to use theproper
Notion mentions, which use the `@some category` notation. With this script, you
can have pretty much all of the benefits of Roam, but with all of the benefits
of Notion!

## Quickstart

⚠️: This script requires Python v3.6 or greater (v3.6 has those juicy format
strings)

1. Follow all of the steps starting at
   [this section of the Notion Developer Docs](https://developers.notion.com/docs/create-a-notion-integration#getting-started)
   1. In particular, make sure you add your integration _to every top level
      page_ that you want this script to search over for literal `[[...]]`
      values. For me, I simply added the integration to every top level Page in
      my Notion workspace's lefthand navbar.
2. `cp .env.example .env` and replace the dummy Notion API key with the one you
   created in step (1) above.
3. Create and activate a Python virtual env:
   `python3 -m venv /path/to/virtualenvs/roam_2_notion && source //path/to/virtualenvs/roam_2_notion/bin/activate`
4. Install dependencies with: `python3 -m pip install -r requirements.txt`
5. Run the script with: `python roam_2_notion.py`
   1. The script runs for many minutes, depending on how many pages you have. It
      will print out the page title and page id for each page it is currently
      processing.
   2. The Notion API allows a
      [max pagination size](https://developers.notion.com/reference/intro#pagination)
      of 100 Notion pages. If you're hundreds of pages into the script and
      suddenly the script fails, you would have to start from the beginning and
      traverse a bunch of pages needlessly. To protect against that, every time
      a a new 100 pages have been processed, the next cursor gets saved to a
      `./cursor_metadata.json` file. If you run the script again, it will pick
      up where it left off. If you want to from the beginning, simply
      `rm ./cursor_metadata.json` and rerun the script.

## Background

I originally had all of my personal notes in Roam Research, which uses the
`[[some category]]` text to link to other pages. I decuded to switch to Notion
because I liked its design, as well as the ability to make any page a public
webpage. So I exported all of my Roam Research notes into markdown files on my
local machine, and then imported these markdown files into Notion. However, the
re-import did not integrate 100% with Notion; specifically all of my Roam
backlinks were left as literal `[[...]]` text values when really I wanted them
to be Notion's native backlinks (which use the `@` prefix) To fix this, I would
have to manually update all of the (1000's!) of backlinks by hand, something I
wasn't prepared to do.

That's why this script exists. And if you have switched from Roam to Notion, you
should be able to use this script as well

## What this Script Does

1. Loop through all paginated Notion Pages, acquiring each Page's ID
2. For each ID, fetch all of the Page's blocks, check for all instances of
   `[[...]]`, and replace each of those literal `[[...]]` text sections with a
   `@` mention

You can think of Notion being a directed cyclic graph, where each vertex is a
block and each edge is a child block. Each vertex gets colored if it has no
`[[...]]` text contained within it. This script traverses the graph, coloring
each vertex until each vertex has been covered.
