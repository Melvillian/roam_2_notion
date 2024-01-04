import re

BRACKET_PATTERN = r"\[\[(.*?)\]\]"


def create_virtual_text(text: str) -> list[tuple[str, bool]]:
    """
    Given some Notion paragraph with square bracket mentions in it i.e.:

    "Hello [[name]]! My na[[blah]]me is [[Cody]].."

    return a "virtual" representation of this text as a list of tuples, where
    each tuple is a tuple of (text, is_mention), and the
    text is either the plaintext or the mention.

    For example: the input sentence above would be output as: [
        ('"Hello ', False), ('name', True), ('! My na', False), ('blah', True),
        ('me is ', False), ('Cody', True), ('..', False)
    ]
    This virtual representation will be used to generate the new Notion block
    that contains correctly formatted mentions, which is the whole
    purpose of this project.

    Args:
        text (str): the Notion paragraph with square bracket mentions in it

    Returns:
        list: a list of tuples, where each tuple is a tuple of
        (text, is_mention), and the text is either the plaintext or the mention.
    """

    raw_virtual_text = re.split(BRACKET_PATTERN, text)
    # remove any empty strings, which are artifacts of 're.split' finding
    # matches at the end or beginning of the string (i.e.
    # "[[Hi]] There" would return ["", "Hi", " There"])
    raw_virtual_text = list(filter(lambda x: x != "", raw_virtual_text))

    # now we have a list of strings split by the [[...]] mentions, but we need
    # to mark each one as either being a mention or just regular plaintext.

    virtual_text = []
    all_mentions = re.findall(BRACKET_PATTERN, text)
    for t in raw_virtual_text:
        is_mention = True if t in all_mentions else False
        virtual_text.append((t, is_mention))

    return virtual_text
