import functools
import os
import re

import db.sql_queries as queries
from db.db_manager import Database
from db.exceptions import CheckError
from db.query_builder import build_query
from utils.book_parser import parse_document
from utils.constants import VALID_WORD_REGEX, DATE_FORMAT


class DocumentDatabase(Database):

    WORD_IDS_CACHE_SIZE = 1000

    VALID_MULTIPLE_WORDS = rf"{VALID_WORD_REGEX}(\W+{VALID_WORD_REGEX})*"
    INVALID_GROUP_NAMES = ["None", "All"]  # These names can't be used as a group name

    APPEARANCES_ORDER = "COUNT(word_index)"
    LENGTH_ORDER = "length"

    class SCRIPTS:
        INITIALIZE_SCHEMA = "initialize_schema"
        SEARCH_PHRASE = "search_phrase"

    def __init__(self, **kargs):
        super().__init__(**kargs)
        self.document_insert_callbacks = []
        self.group_insert_callbacks = []
        self.group_word_insert_callbacks = []
        self.phrase_insert_callbacks = []

    def _initialize_schema(self):
        self._run_sql_script(DocumentDatabase.SCRIPTS.INITIALIZE_SCHEMA, multiple_statements=True)

    def new_connection(self, always_create=False, new_path=None, commit=True):
        if not super().new_connection(always_create, new_path, commit):
            self._initialize_schema()
        self.get_word_id.cache_clear()

    def add_document_insert_callback(self, callback):
        self.document_insert_callbacks.append(callback)

    def add_group_insert_callback(self, callback):
        self.group_insert_callbacks.append(callback)

    def add_group_word_insert_callback(self, callback):
        self.group_word_insert_callbacks.append(callback)

    def add_phrase_insert_callback(self, callback):
        self.phrase_insert_callbacks.append(callback)

    @staticmethod
    def call_all_callbacks(callbacks, *args):
        for callback in callbacks:
            callback(*args)

    @staticmethod
    def assert_valid_word(word):
        if not re.fullmatch(VALID_WORD_REGEX, word):
            raise CheckError

    @staticmethod
    def to_single_word(word):
        single_word = word.lower().strip()
        DocumentDatabase.assert_valid_word(single_word)
        return single_word

    @staticmethod
    def assert_valid_name(words):
        valid = re.fullmatch(DocumentDatabase.VALID_MULTIPLE_WORDS, words) and \
                words == words.title()

        if not valid:
            raise CheckError

    @staticmethod
    def to_title(words):
        name = words.title().strip()
        DocumentDatabase.assert_valid_name(name)
        return name

    def insert_document(self, name, author, path, size, date):

        return self.execute(queries.INSERT_DOCUMENT,
                            (self.to_title(name), self.to_title(author), path, size, date)).lastrowid

    def insert_word(self, word):

        return self.execute(queries.INSERT_WORD, (word, len(word))).lastrowid

    def insert_many_words(self, words):
        self.executemany(queries.INSERT_WORD, ((word, len(word)) for word in words))

    def insert_many_words_with_id(self, words_with_ids):
        self.executemany(queries.INSERT_WORD_WITH_ID,
                         ((word_id, self.to_single_word(word)) for word, word_id in words_with_ids))

    # Will be used a lot for the same words, so caching the result can improve performance
    @functools.lru_cache(WORD_IDS_CACHE_SIZE)
    def get_word_id(self, word):
        word = self.to_single_word(word)
        search_result = self.execute(queries.WORD_NAME_TO_ID, (word,)).fetchone()

        return self.insert_word(word) if search_result is None else search_result[0]

    def insert_many_word_appearances(self, word_appearances):
        self.executemany(queries.INSERT_WORD_APPEARANCE, word_appearances)

    def insert_many_word_id_appearances(self, word_id_appearances):
        self.executemany(queries.INSERT_WORD_ID_APPEARANCE, word_id_appearances)

    def insert_words_group(self, name):
        name = self.to_title(name)
        if name in DocumentDatabase.INVALID_GROUP_NAMES:
            raise CheckError

        group_id = self.execute(queries.INSERT_WORDS_GROUP, (name,)).lastrowid

        # Call the group insert callbacks
        self.call_all_callbacks(self.group_insert_callbacks)
        return group_id

    def insert_word_to_group(self, group_id, word):
        rowid = self.execute(queries.INSERT_WORD_TO_GROUP, (group_id, self.get_word_id(word))).lastrowid

        # Call the group word insert callbacks with the id of the group
        self.call_all_callbacks(self.group_word_insert_callbacks, group_id)
        return rowid

    def insert_many_word_ids_to_group(self, group_id, word_ids):
        self.executemany(queries.INSERT_WORD_TO_GROUP, ((group_id, word_id) for word_id in word_ids))

    def insert_phrase(self, phrase, words_count):
        return self.execute(queries.INSERT_PHRASE, (phrase, words_count,)).lastrowid

    def insert_many_words_to_phrase(self, words_in_phrase):
        self.executemany(queries.INSERT_WORD_TO_PHRASE, words_in_phrase)

    def insert_many_word_ids_to_phrase(self, phrase_id, word_ids):
        self.executemany(queries.INSERT_WORD_ID_TO_PHRASE,
                         ((phrase_id, word_id, index) for index, word_id in enumerate(word_ids)))

    def add_document(self, title, author, path, date):
        if not os.path.exists(path):
            raise FileNotFoundError

        # Insert a new document entry
        size = os.path.getsize(path)
        document_id = self.insert_document(title, author, path, size, date)

        words = set()
        appearances = []
        for appr in parse_document(path):
            word = self.to_single_word(appr[0])
            words.add(word)
            appearances.append((document_id, word) + appr[1:])

        # Insert all the words and their appearances
        self.insert_many_words(words)
        self.insert_many_word_appearances(appearances)

        # Call the document insert callbacks
        self.call_all_callbacks(self.document_insert_callbacks)
        return document_id

    def add_phrase(self, phrase):
        # Split to single valid words
        words = [self.to_single_word(match[0]) for match in re.finditer(VALID_WORD_REGEX, phrase)]

        # Insert the phrase
        phrase_id = self.insert_phrase(phrase, len(words))

        # Insert the words in the phrase that don't exists already
        self.insert_many_words(words)

        # Insert the words of the phrase to the phrase
        words_in_phrase = ((phrase_id, word, index) for index, word in enumerate(words, start=1))
        self.insert_many_words_to_phrase(words_in_phrase)

        # Call the phrase insert callbacks
        self.call_all_callbacks(self.phrase_insert_callbacks)
        return phrase_id

    def build_and_exec(self, **kwargs):
        return self.execute(build_query(**kwargs)).fetchall()

    def search_documents(self, tables=None, **kwargs):

        tables = set(tables) if tables else set()
        tables.add("document")

        return self.build_and_exec(
            cols=["document_id", "title", "author", "file_path", f"STRFTIME('{DATE_FORMAT}', creation_date)", "file_size"],
            tables=tables,
            group_by="document_id",
            **kwargs
        )

    def search_word_appearances(self, cols=None, tables=None, unique_words=False, order_by=None, **kwargs):

        tables = set(tables) if tables else set()
        tables.add("word_appearance")

        if unique_words:
            kwargs["group_by"] = "word_id"

        return self.build_and_exec(
            cols=cols,
            tables=tables,
            order_by=order_by,
            **kwargs
        )

    def word_location_to_offset(self, document_id, sentence, sentence_index, word_end_offset=False):

        query = queries.WORD_LOCATION_TO_END_OFFSET if word_end_offset else queries.WORD_LOCATION_TO_OFFSET
        return self.execute(query, (document_id, sentence, sentence_index)).fetchone()

    def all_words(self):

        return self.execute(queries.ALL_WORDS).fetchall()

    def all_documents(self, date_format=DATE_FORMAT):

        return self.execute(queries.ALL_DOCUMENTS, (date_format,)).fetchall()

    def get_document_title(self, document_id):
        return self.execute(queries.DOCUMENT_ID_TO_TITLE, (document_id,)).fetchone()

    def get_document_full_name(self, document_id):

        return self.execute(queries.DOCUMENT_ID_TO_FULL_NAME, (document_id,)).fetchone()

    def get_document_path(self, document_id):
        return self.execute(queries.DOCUMENT_ID_TO_PATH, (document_id,)).fetchone()

    def all_document_words(self, document_id):

        return iter(self.execute(queries.ALL_DOCUMENT_WORDS, (document_id,)))

    def all_groups(self):
        return self.execute(queries.ALL_GROUPS).fetchall()

    def words_in_group(self, group_id):
        return self.execute(queries.ALL_WORDS_IN_GROUP, (group_id,)).fetchall()

    def all_phrases(self):
        return self.execute(queries.ALL_PHRASES).fetchall()

    def words_in_phrase(self, phrase_id):
        return self.execute(queries.ALL_WORDS_IN_PHRASE, (phrase_id,)).fetchall()

    def find_phrase(self, phrase_id):
        return self._run_sql_script(DocumentDatabase.SCRIPTS.SEARCH_PHRASE, (phrase_id,)).fetchall()
