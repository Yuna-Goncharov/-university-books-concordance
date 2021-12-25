
from xml.dom import minidom
from xml.etree.ElementTree import ElementTree, Element, Comment, SubElement, tostring

from db.Documents_db import DocumentDatabase
from utils.constants import XML_DATE_FORMAT


def prettify(elem):
    rough_string = tostring(elem, 'utf-8')
    return minidom.parseString(rough_string).toprettyxml(indent="  ")


def export_words(db):  # type: (DocumentDatabase) -> Element
    words = Element('words')

    for word_id, name in db.all_words():
        SubElement(words, "word", {"id": str(word_id)}).text = name

    return words


def export_documents(db):  # type: (DocumentDatabase) -> Element
    documents = Element('documents')

    for document_id, name, author, path, size, date in db.all_documents(date_format=XML_DATE_FORMAT):
        document = SubElement(documents, "document")
        SubElement(document, "name").text = name
        SubElement(document, "author").text = author
        SubElement(document, "path").text = path
        SubElement(document, "size").text = str(size)
        SubElement(document, "date").text = date
        body = SubElement(document, "body")

        curr_paragraph = None
        curr_paragraph_element = None
        curr_sentence = None
        curr_sentence_element = None
        for word_appr in db.all_document_words(document_id):
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

    return documents


def export_groups(db):  # type: (DocumentDatabase) -> Element
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
    root = Element('tables')

    comment = Comment('Document Database')
    root.append(comment)

    root.append(export_words(db))
    root.append(export_documents(db))
    root.append(export_groups(db))
    root.append(export_phrases(db))

    return ElementTree(root)


def export_db(db, xml_path, prettify=False):
    tree = build_xml(db)

    with open(xml_path, "wb") as xml_output:
        if prettify:
            xml_output.write(bytes(minidom.parseString(tostring(tree.getroot())).toprettyxml(indent=" " * 4), 'utf-8'))
        else:
            tree.write(xml_output, encoding='utf-8', xml_declaration=True)