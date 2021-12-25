
from datetime import datetime
from itertools import count
from xml.etree.ElementTree import ElementTree, Element

from lxml import etree

from db.Documents_db import DocumentDatabase
from utils.constants import XML_DATE_FORMAT

SCHEMA_FILENAME = r"db\xml\schema.xsd"

g_parser = None


def parse_xml(xml_path):  # type: (str) -> ElementTree
    global g_parser

    if g_parser is None:
        schema = etree.XMLSchema(etree.parse(SCHEMA_FILENAME))
        g_parser = etree.XMLParser(schema=schema)

    return etree.ElementTree(file=xml_path, parser=g_parser)


def init_words(db, words_root):  # type: (DocumentDatabase, Element) -> None
    words = ((word.text, word.get("id")) for word in words_root)

    db.insert_many_words_with_id(words)


def init_documents(db, documents_root):  # type: (DocumentDatabase, Element) -> None

    for document in documents_root:
        title = document.find("title").text
        author = document.find("author").text
        path = document.find("path").text
        size = int(document.find("size").text)
        date = datetime.strptime(document.find("date").text, XML_DATE_FORMAT)
        document_id = db.insert_document(title, author, path, size, date)

        appearances = []
        word_index_counter = count(1)
        sentence_counter = count(1)
        line_index_counter = count(1)
        curr_line = None

        for paragraph, paragraph_element in enumerate(document.find("body"), start=1):
            for sentence_element in paragraph_element:
                sentence = next(sentence_counter)

                for sentence_index, wordref in enumerate(sentence_element, start=1):
                    word_id = int(wordref.get("refid"))
                    line, line_offset = (int(n) for n in wordref.text.split(":"))

                    if curr_line != line:
                        line_index_counter = count(1)
                    curr_line = line

                    appearances.append((document_id,
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

    # Iterate over each group element
    for group in groups_root:
        # Insert the group the the db
        group_id = db.insert_words_group(group.find("name").text)
        # Insert all of the wordrefs as word ids
        db.insert_many_word_ids_to_group(group_id, (int(wordref.text) for wordref in group.iter("wordref")))


def init_phrases(db, phrases_root):  # type: (DocumentDatabase, Element) -> None

    for phrase in phrases_root:
        phrase_id = db.insert_phrase(phrase.find("text").text, len(phrase))
        db.insert_many_word_ids_to_phrase(phrase_id, (int(wordref.text) for wordref in phrase.iter("wordref")))


def import_db(db, xml_path):  # type: (DocumentDatabase, str) -> None

    try:
        tree = parse_xml(xml_path)
    except etree.XMLSyntaxError as e:
        raise ValueError(e.msg)

    db.new_connection()

    root = tree.getroot()
    init_words(db, root.find("words"))
    init_documents(db, root.find("documents"))
    init_groups(db, root.find("groups"))
    init_phrases(db, root.find("phrases"))