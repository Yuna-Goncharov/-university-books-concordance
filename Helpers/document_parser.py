import itertools
import os
import re

from Helpers.constants import VALID_WORD_REGEX
from Helpers.utils import cached_read

AUTHOR_REGEX = r"Author: (.+)$"
TITLE_REGEX = r"Title: (.+)$"
END_OF_SENTENCE_REGEX = r"[\.?!]"


def parse_document_file(path):
    name_match = None
    author_match = None

    for line in cached_read(path).splitlines():
        if not name_match:
            name_match = re.search(TITLE_REGEX, line)
        if not author_match:
            author_match = re.search(AUTHOR_REGEX, line)

        if name_match and author_match:
            break

    name = name_match.group(1) if name_match else None
    author = author_match.group(1) if author_match else None
    date = os.path.getctime(path)
    size = os.path.getsize(path)
    return name, author, date, size


def parse_document(path):
    words_counter = itertools.count(1)
    paragraph_counter = 0
    sentence_counter = 0
    words_in_sentence = 0
    previous_line = None

    raw = cached_read(path)
    for line_counter, line in enumerate(raw.splitlines(), 1):
        words_in_line_counter = itertools.count(1)
        sentence_offset_in_line = 0

        for sentence_number, sentence in enumerate(filter(None, re.split(END_OF_SENTENCE_REGEX, line))):
            if sentence_number > 0:
                words_in_sentence = 0
                sentence_counter += 1

            words_match = list(re.finditer(VALID_WORD_REGEX, sentence))

            if words_match:
                if previous_line is None or previous_line < line_counter - 1:
                    paragraph_counter += 1

                    if words_in_sentence > 0:
                        words_in_sentence = 0
                        sentence_counter += 1

                previous_line = line_counter

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

            sentence_offset_in_line += len(sentence) + 1
