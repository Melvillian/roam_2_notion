# notion_python_fixer

A small throwaway script for converting all of my personal Notion page content that contains literal [[...]] values to use proper Notion backlinks, which use the @ notation.

## How It Works

### Background

I originally had all of my personal notes in Roam Research, which uses the "[[some category]]" text to link to other pages. This was a bit of a pain to maintain, as I would have to manually update all of the links whenever I moved Notion, which uses the "@some category" for backlinks.

### The Process

1. Iterate through all paginated Pages JSON, each item contains a Page's ID
2. For each ID, fetch the Page's first layer block children
    a. If the block is a paragraph, check if it contains a [[...]] value
    b. If it does, replace it with a @ notation link and write that data to the block
    c. If it doesn't, continue to the next block
3. Repeat step 2 for the next layer of children on that page, until there are no more blocks to process

You can think of Notion being a directed cyclic graph, where each vertex is a block and each edge is a child block.
Each vertex gets covered if it has no [[...]] text contained within it. This script traverses the graph, coloring each
vertex until each vertex has been covered.
