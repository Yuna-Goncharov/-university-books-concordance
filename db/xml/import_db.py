"""
This file handles the importing process of the books database from an XML.
"""

from datetime import datetime
from itertools import count
from xml.etree.ElementTree import ElementTree, Element

from lxml import etree

from db.Documents_db import DocumentDatabase
from utils.constants import XML_DATE_FORMAT

# The XSD schema describing a valid XML file
SCHEMA_FILENAME = r"db\xml\schema.xsd"

# Parser singleton
g_parser = None


def parse_xml(xml_path):  # type: (str) -> ElementTree
    """
    Parse a XML file into an ElementTree object.
    :param xml_path: The path of XML
    :return: The parsed ElementTree
    """
    global g_parser

    if g_parser is None:
        # Create the parser singleton
        schema = etree.XMLSchema(etree.parse(SCHEMA_FILENAME))
        g_parser = etree.XMLParser(schema=schema)

    # Use the parser to parse the XML file
    return etree.ElementTree(file=xml_path, parser=g_parser)


def init_words(db, words_root):  # type: (DocumentDatabase, Element) -> None
    """ Import all the words into the database """
    words = ((word.text, word.get("id")) for word in words_root)

    # Insert all the collected words with ids
    db.insert_many_words_with_id(words)


def init_books(db, books_root):  # type: (DocumentDatabase, Element) -> None
    """ Import all the books into the database """

    # Iterate over each book element
    for book in books_root:
        # Insert a new book to the database
        title = book.find("title").text
        author = book.find("author").text
        path = book.find("path").text
        size = int(book.find("size").text)
        date = datetime.strptime(book.find("date").text, XML_DATE_FORMAT)
        book_id = db.insert_book(title, author, path, size, date)

        # Collect all the word appearances to be inserted
        appearances = []
        word_index_counter = count(1)
        sentence_counter = count(1)
        line_index_counter = count(1)
        curr_line = None

        # Iterate over the paragraphs in the book body
        for paragraph, paragraph_element in enumerate(book.find("body"), start=1):
            # Iterate over the sentences in the paragraph
            for sentence_element in paragraph_element:
                sentence = next(sentence_counter)

                # Iterate over the wordrefs in the sentence
                for sentence_index, wordref in enumerate(sentence_element, start=1):
                    word_id = int(wordref.get("refid"))
                    line, line_offset = (int(n) for n in wordref.text.split(":"))

                    # Increase line if needed
                    if curr_line != line:
                        line_index_counter = count(1)
                    curr_line = line

                    # Add an word appearance
                    appearances.append((book_id,
                                        word_id,
                                        next(word_index_counter),
                                        paragraph,
                                        line,
                                        next(line_index_counter),
                                        line_offset,
                                        sentence,
                                        sentence_index))

        # Insert all of the collected appearances
        db.insert_many_word_id_appearances(appearances)


def init_groups(db, groups_root):  # type: (DocumentDatabase, Element) -> None
    """ Import all the groups into the database """

    # Iterate over each group element
    for group in groups_root:
        # Insert the group the the db
        group_id = db.insert_words_group(group.find("name").text)
        # Insert all of the wordrefs as word ids
        db.insert_many_word_ids_to_group(group_id, (int(wordref.text) for wordref in group.iter("wordref")))


def init_phrases(db, phrases_root):  # type: (DocumentDatabase, Element) -> None
    """ Import all the phrases into the database """

    # Iterate over each phrase element
    for phrase in phrases_root:
        # Insert the phrase the the db
        phrase_id = db.insert_phrase(phrase.find("text").text, len(phrase))
        # Insert all of the wordrefs as word ids
        db.insert_many_word_ids_to_phrase(phrase_id, (int(wordref.text) for wordref in phrase.iter("wordref")))


def import_db(db, xml_path):  # type: (DocumentDatabase, str) -> None
    """
    Import a given XML file into the db.
    :param db: The database to import into
    :param xml_path: The path to the XML to be imported
    """

    # Parse the file into a tree
    try:
        tree = parse_xml(xml_path)
    except etree.XMLSyntaxError as e:
        raise ValueError(e.msg)

    # Start an empty connection database
    db.new_connection()

    # Initialize all the tables
    root = tree.getroot()
    init_words(db, root.find("words"))
    init_books(db, root.find("books"))
    init_groups(db, root.find("groups"))
    init_phrases(db, root.find("phrases"))