"""
This file handles the exporting process of the books database to an XML.
"""

from xml.dom import minidom
from xml.etree.ElementTree import ElementTree, Element, Comment, SubElement, tostring

from db.Documents_db import DocumentDatabase
from utils.constants import XML_DATE_FORMAT


def prettify(elem):
    """
    Convert an Element to a prettified string.
    :param elem: The element to convert
    :return: A prettified string of the element.
    """
    rough_string = tostring(elem, 'utf-8')
    return minidom.parseString(rough_string).toprettyxml(indent="  ")


def export_words(db):  # type: (DocumentDatabase) -> Element
    """ Create the words element, with all the words in the database """
    words = Element('words')

    # Iterate over all the words
    for word_id, name in db.all_words():
        # Create a word element
        SubElement(words, "word", {"id": str(word_id)}).text = name

    return words


def export_books(db):  # type: (DocumentDatabase) -> Element
    """ Create the books element, with all the books in the database """
    books = Element('books')

    # Iterate over all the books
    for book_id, title, author, path, size, date in db.all_books(date_format=XML_DATE_FORMAT):
        # Crete a book element
        book = SubElement(books, "book")
        SubElement(book, "title").text = title
        SubElement(book, "author").text = author
        SubElement(book, "path").text = path
        SubElement(book, "size").text = str(size)
        SubElement(book, "date").text = date
        body = SubElement(book, "body")

        # Iterate over all the words appearances and insert them
        curr_paragraph = None
        curr_paragraph_element = None
        curr_sentence = None
        curr_sentence_element = None
        for word_appr in db.all_book_words(book_id):
            word_id, paragraph, sentence, line, line_offset = word_appr

            # Create a new paragraph
            if curr_paragraph is None or curr_paragraph < paragraph:
                curr_paragraph_element = SubElement(body, "paragraph")
            curr_paragraph = paragraph

            # Create a new sentence
            if curr_sentence is None or curr_sentence < sentence:
                curr_sentence_element = SubElement(curr_paragraph_element, "sentence")
            curr_sentence = sentence

            # Create an appearance element
            SubElement(curr_sentence_element, "appr", {"refid": str(word_id)}).text = f"{line}:{line_offset}"

    return books


def export_groups(db):  # type: (DocumentDatabase) -> Element
    """ Create the groups element, with all the groups in the database """
    groups = Element('groups')

    # Iterate over all the groups
    for group_id, name in db.all_groups():
        # Create a group element
        group = SubElement(groups, "group")
        SubElement(group, "name").text = name

        # Iterate over all the words in the group and insert them
        for word_id, _name in db.words_in_group(group_id):
            # Create a wordref element
            SubElement(group, "wordref").text = str(word_id)

    return groups


def export_phrases(db):  # type: (DocumentDatabase) -> Element
    """ Create the phrases element, with all the phrases in the database """
    phrases = Element('phrases')

    # Iterate over all the phrases
    for phrase_text, phrase_id in db.all_phrases():
        # Create a phrase element
        phrase = SubElement(phrases, "phrase")
        SubElement(phrase, "text").text = phrase_text

        # Iterate over all the words in the phrase and insert them
        for word_id, in db.words_in_phrase(phrase_id):
            # Create a wordref element
            SubElement(phrase, "wordref").text = str(word_id)

    return phrases


def build_xml(db):  # type: (DocumentDatabase) -> ElementTree
    """
    Create an ElementTree representation of the given books database.
    :param db: The books database
    :return: ElementTree representation of the database.
    """
    root = Element('tables')

    comment = Comment('Books Database by Lotem Ben Yaakov')
    root.append(comment)

    root.append(export_words(db))
    root.append(export_books(db))
    root.append(export_groups(db))
    root.append(export_phrases(db))

    return ElementTree(root)


def export_db(db, xml_path, prettify=False):
    """
    Export a given db to a XML file.
    :param db: The database to export
    :param xml_path: The path to the XML to be written to
    :param prettify: Should the XML string be prettified. Effects performance.
    """
    tree = build_xml(db)

    with open(xml_path, "wb") as xml_output:
        if prettify:
            xml_output.write(bytes(minidom.parseString(tostring(tree.getroot())).toprettyxml(indent=" " * 4), 'utf-8'))
        else:
            tree.write(xml_output, encoding='utf-8', xml_declaration=True)