import itertools
import os
import re

from utils.constants import VALID_WORD_REGEX
from utils.utils import cached_read

AUTHOR_REGEX = r"Author: (.+)$"
TITLE_REGEX = r"Title: (.+)$"
END_OF_SENTENCE_REGEX = r"[\.?!]"


def parse_book_file(path):
    """
    Parse a file of a book.
    Try to find the title & the author in the text.
    Get the creation date & size of the file.
    :param path: The file path
    :return: The title, author, date, and size
    """
    title_match = None
    author_match = None

    # Iterate over the lines and search for the title and author
    for line in cached_read(path).splitlines():
        if not title_match:
            title_match = re.search(TITLE_REGEX, line)
        if not author_match:
            author_match = re.search(AUTHOR_REGEX, line)

        if title_match and author_match:
            # Both were found
            break

    title = title_match.group(1) if title_match else None
    author = author_match.group(1) if author_match else None
    date = os.path.getctime(path)
    size = os.path.getsize(path)
    return title, author, date, size


def parse_document(path):
    """
    Generator of word appearances in the path file.
    This yields appearances in the form of tuples containing:
        word: The word string
        word_index: The index of the word in the book
        paragraph: The paragraph number
        line: The line number
        line_index: The index of the word in its line
        line_offset: The characters offset of the word in the line
        sentence: The sentence number
        sentence_index: The index of the word in its sentence

    :param path: The path of the file to parse
    """
    words_counter = itertools.count(1)
    paragraph_counter = 0
    sentence_counter = 0
    words_in_sentence = 0
    previous_line = None

    # Go over the lines in the file
    raw = cached_read(path)
    for line_counter, line in enumerate(raw.splitlines(), 1):
        # Split each line to the different sentences
        words_in_line_counter = itertools.count(1)
        sentence_offset_in_line = 0

        # The filter remove empty sentences
        for sentence_number, sentence in enumerate(filter(None, re.split(END_OF_SENTENCE_REGEX, line))):
            if sentence_number > 0:
                # If its not the first sentence we parse in the line, start a new sentence
                words_in_sentence = 0
                sentence_counter += 1

            # Get the list of the words matches
            words_match = list(re.finditer(VALID_WORD_REGEX, sentence))

            # Check if there are words in this line
            if words_match:
                # If the last line with words wasn't the previous line
                if previous_line is None or previous_line < line_counter - 1:
                    paragraph_counter += 1

                    # If the last sentence wasn't ended by a dot '.', we should start a new sentence manually
                    if words_in_sentence > 0:
                        words_in_sentence = 0
                        sentence_counter += 1

                previous_line = line_counter

                # Go over the matched words and insert them to the database
                for word_match in words_match:
                    word = word_match[0]
                    words_in_sentence += 1
                    line_offset = sentence_offset_in_line + word_match.start()

                    yield (word,
                           next(words_counter),
                           paragraph_counter,
                           line_counter,
                           next(words_in_line_counter),
                           line_offset,
                           sentence_counter,
                           words_in_sentence)

            # Add the length of the line to the total offset counter
            sentence_offset_in_line += len(sentence) + 1
