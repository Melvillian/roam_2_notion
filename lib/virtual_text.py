import re

BRACKET_PATTERN = r"\[\[(.*?)\]\]"
LEFT_BRACKET_PATTERN = r"\[\["
RIGHT_BRACKET_PATTERN = r"\]\]"


def create_virtual_text(text):
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
    This virtual representation will be used to generate the new Notion block that
    contains correctly formatted mentions, which is the whole
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
    # to mark each one as either being a mention or just regular plaintext. We
    # know the elements alternate between one and the other, so we just need to
    # determine whether the first element is a mention or a plaintext. We do
    # that by checking the first characters in the input text, and if it starts
    # with 2 left brackets, then the first element in the list is a mention,
    # otherwise it's plaintext.
    first_element_is_mention = text.startswith("[[")
    virtual_text = []
    current_text_is_mention = first_element_is_mention
    for mention_or_plaintext in raw_virtual_text:
        virtual_text.append((mention_or_plaintext, current_text_is_mention))
        current_text_is_mention = not current_text_is_mention

    return virtual_text
