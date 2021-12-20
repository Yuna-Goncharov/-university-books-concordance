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
    """
    Books database manager class.
    It is the python interface to perform actions on the books database.
    """

    # Cache size for get_word_id
    WORD_IDS_CACHE_SIZE = 1000

    VALID_MULTIPLE_WORDS = rf"{VALID_WORD_REGEX}(\W+{VALID_WORD_REGEX})*"
    INVALID_GROUP_NAMES = ["None", "All"]  # These names can't be used as a group name

    # Different arguments to order_by of word when building a dynamic query
    ALPHABET_ORDER = "name"
    APPEARANCES_ORDER = "COUNT(word_index)"
    LENGTH_ORDER = "length"

    # Script names
    class SCRIPTS:
        INITIALIZE_SCHEMA = "initialize_schema"
        SEARCH_PHRASE = "search_phrase"

    #
    # Initializations Functions
    #

    def __init__(self, **kargs):
        super().__init__(**kargs)
        self.document_insert_callbacks = []
        self.group_insert_callbacks = []
        self.group_word_insert_callbacks = []
        self.phrase_insert_callbacks = []

    def _initialize_schema(self):
        """ Initialize the db with the books schema. """
        self._run_sql_script(DocumentDatabase.SCRIPTS.INITIALIZE_SCHEMA, multiple_statements=True)

    def new_connection(self, always_create=False, new_path=None, commit=True):
        if not super().new_connection(always_create, new_path, commit):
            # Only if a new connection was created
            self._initialize_schema()
        self.get_word_id.cache_clear()

    #
    # Callbacks Functions
    #

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
        """
        Call of the callbacks in the given list with the given arguments.
        :param callbacks: The callbacks list
        :param args: The arguments to pass
        """
        for callback in callbacks:
            callback(*args)

    #
    # String Functions
    #

    @staticmethod
    def assert_valid_word(word):
        if not re.fullmatch(VALID_WORD_REGEX, word):
            raise CheckError

    @staticmethod
    def to_single_word(word):
        """
        Convert a string to a stripped lower case.
        :param word: The word to convert.
        :raises CheckError: If the string isn't a valid single word
        :return: The string as a string word
        """
        single_word = word.lower().strip()
        DocumentDatabase.assert_valid_word(single_word)
        return single_word

    @staticmethod
    def assert_valid_title(words):
        valid = re.fullmatch(DocumentDatabase.VALID_MULTIPLE_WORDS, words) and \
                words == words.title()

        if not valid:
            raise CheckError

    @staticmethod
    def to_title(words):
        """
        Convert a string to a stripped title case.
        :param words: The word to convert.
        :raises CheckError: If the string isn't a valid title
        :return: The string as a title
        """
        title = words.title().strip()
        DocumentDatabase.assert_valid_title(title)
        return title

    #
    # Database Insertion Functions
    #

    def insert_document(self, title, author, path, size, date):

        return self.execute(queries.INSERT_DOCUMENT,
                            (self.to_title(title), self.to_title(author), path, size, date)).lastrowid

    def insert_word(self, word):

        return self.execute(queries.INSERT_WORD, (word, len(word))).lastrowid

    def insert_many_words(self, words):
        """
        Insert many words to the database (only those who doesn't exists already).
        :param words: Iterable of words to be inserted
        """
        self.executemany(queries.INSERT_WORD, ((word, len(word)) for word in words))

    def insert_many_words_with_id(self, words_with_ids):
        """
        Insert many words to the database, with the given word ids.
        :param words_with_ids: Iterable of words and their ids to be inserted
        """
        self.executemany(queries.INSERT_WORD_WITH_ID,
                         ((word_id, self.to_single_word(word)) for word, word_id in words_with_ids))

    # Will be used a lot for the same words, so caching the result can improve performance
    @functools.lru_cache(WORD_IDS_CACHE_SIZE)
    def get_word_id(self, word):
        """
        Return the word_id of a word.
        If that word doesn't have and id, it will be added to the db.
        :param word: The word to search for
        :return: The word id of the word
        """

        word = self.to_single_word(word)

        # Most of the words we'll search for will already be inserted.
        # So we should first search for the word, and only try to insert it if it doesn't exists,
        # and not the other way around.
        search_result = self.execute(queries.WORD_NAME_TO_ID, (word,)).fetchone()

        return self.insert_word(word) if search_result is None else search_result[0]

    def insert_many_word_appearances(self, word_appearances):
        """
         Insert many word appearances to the database, by using the word string.
        :param word_appearances: Iterable of words appearances in the form of:
            (document_id, name, word_index, paragraph, line, line_index, line_offset, sentence, sentence_index)
            where name is assumed to be an existing word name.
        """
        self.executemany(queries.INSERT_WORD_APPEARANCE, word_appearances)

    def insert_many_word_id_appearances(self, word_id_appearances):
        """
         Insert many word appearances to the database, by using word ids.
        :param word_id_appearances: Iterable of words appearances in the form of:
            (document_id, word_id, word_index, paragraph, line, line_index, line_offset, sentence, sentence_index).
        """
        self.executemany(queries.INSERT_WORD_ID_APPEARANCE, word_id_appearances)

    def insert_words_group(self, name):
        """
        Insert a group to the database.
        :param name: The name of the group
        :raises CheckError: If the name isn't a valid group name
        :return: The group id of the newly inserted group
        """
        name = self.to_title(name)
        if name in DocumentDatabase.INVALID_GROUP_NAMES:
            raise CheckError

        group_id = self.execute(queries.INSERT_WORDS_GROUP, (name,)).lastrowid

        # Call the group insert callbacks
        self.call_all_callbacks(self.group_insert_callbacks)
        return group_id

    def insert_word_to_group(self, group_id, word):
        """
        Insert a word to a group with a given id.
        :param group_id: The group id of to group to insert the word into
        :param word: The word to insert, assumed to be an existing word name.
        :return: The rowid of the inserted table entry
        """
        rowid = self.execute(queries.INSERT_WORD_TO_GROUP, (group_id, self.get_word_id(word))).lastrowid

        # Call the group word insert callbacks with the id of the group
        self.call_all_callbacks(self.group_word_insert_callbacks, group_id)
        return rowid

    def insert_many_word_ids_to_group(self, group_id, word_ids):
        """
        Insert many word ids to a group with a given id.
        :param group_id: The group id of to group to insert the word into
        :param word_ids: Iterable of the word ids to insert.
        """
        self.executemany(queries.INSERT_WORD_TO_GROUP, ((group_id, word_id) for word_id in word_ids))
        # no need for callbacks here

    def insert_phrase(self, phrase, words_count):
        """
        Insert a phrase to the database.
        :param phrase: The text of the phrase
        :param words_count: The number of words in the phrase
        :return: The phrase id of the newly inserted phrase
        """
        return self.execute(queries.INSERT_PHRASE, (phrase, words_count,)).lastrowid

    def insert_many_words_to_phrase(self, words_in_phrase):
        """
        Insert many words to phrases.
        :param words_in_phrase: Iterable of words in phrase in the form of:
            (phrase_id, name, phrase_index)
            where name is assumed to be an existing word name.
        """
        self.executemany(queries.INSERT_WORD_TO_PHRASE, words_in_phrase)

    def insert_many_word_ids_to_phrase(self, phrase_id, word_ids):
        """
        Insert many word ids to a group with a given phrase id.
        :param phrase_id: The phrase id to insert to words into
        :param word_ids: Iterable of the word ids to insert
        """
        self.executemany(queries.INSERT_WORD_ID_TO_PHRASE,
                         ((phrase_id, word_id, index) for index, word_id in enumerate(word_ids)))

    #
    # Advanced Insertion Functions
    #

    def add_document(self, title, author, path, date):
        if not os.path.exists(path):
            raise FileNotFoundError

        # Insert a new book entry
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

        # Call the book insert callbacks
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

    #
    # Dynamic Database Queries Functions
    #

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

    #
    # Query Database Functions
    #

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
