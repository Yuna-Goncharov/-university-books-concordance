import functools
import os
import re

import db.sql_queries as queries
from db.db_manager import Database
from db.exceptions import CheckError
from db.query_builder import build_query
from utils.book_parser import parse_book
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
        self.book_insert_callbacks = []
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
        self.book_insert_callbacks.append(callback)

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

    def insert_book(self, title, author, path, size, date):
        """
        Insert a book to the database.
        :param title: Title of the book
        :param author: Author of the book
        :param path: The path to the file containing the book text
        :param size: The size of the book file
        :param date: A date related to the book to store (publish / file date)
        :return: The book id of the newly inserted book
        """
        return self.execute(queries.INSERT_BOOK,
                            (self.to_title(title), self.to_title(author), path, size, date)).lastrowid

    def insert_word(self, word):
        """
        Insert a word to the database (if it doesn't exists already).
        :param word: The word string to insert. Assumed to be a valid single word.
        :return: The word id of the newly inserted word
        """
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
            (book_id, name, word_index, paragraph, line, line_index, line_offset, sentence, sentence_index)
            where name is assumed to be an existing word name.
        """
        self.executemany(queries.INSERT_WORD_APPEARANCE, word_appearances)

    def insert_many_word_id_appearances(self, word_id_appearances):
        """
         Insert many word appearances to the database, by using word ids.
        :param word_id_appearances: Iterable of words appearances in the form of:
            (book_id, word_id, word_index, paragraph, line, line_index, line_offset, sentence, sentence_index).
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

    def add_book(self, title, author, path, date):
        """
        Add a new book in the database.
        :param title: Title of the book
        :param author: Author of the book
        :param path: The path to the file containing the book text
        :param date: A date related to the book to store (publish / file date)
        :raises FileNotFoundError: If the path doesn't exists
        :return: The book id of the newly inserted book
        """

        # Make sure the file exists
        if not os.path.exists(path):
            raise FileNotFoundError

        # Insert a new book entry
        size = os.path.getsize(path)
        book_id = self.insert_book(title, author, path, size, date)

        # Iterate the parsed book words, and keep track of the words & appearances which needs to be inserted
        words = set()
        appearances = []
        for appr in parse_book(path):
            word = self.to_single_word(appr[0])
            words.add(word)
            appearances.append((book_id, word) + appr[1:])

        # Insert all the words and their appearances
        self.insert_many_words(words)
        self.insert_many_word_appearances(appearances)

        # Call the book insert callbacks
        self.call_all_callbacks(self.book_insert_callbacks)
        return book_id

    def add_phrase(self, phrase):
        """
        Add a new phrase in the database.
        :param phrase: The phrase text to be inserted
        :return: The phrase id of the newly created phrase
        """

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
        """
        Dynamically build a query, and execute it.
        :param kwargs: Arguments to build_query
        :return: All the matched entries
        """
        return self.execute(build_query(**kwargs)).fetchall()

    def search_books(self, tables=None, **kwargs):
        """
        Search the books table with dynamic filters
        :param tables: Additional tables needed for the search
        :param kwargs: Arguments to build_query
        :return: All the matched book entries
        """
        tables = set(tables) if tables else set()
        tables.add("book")

        return self.build_and_exec(
            cols=["book_id", "title", "author", "file_path", f"STRFTIME('{DATE_FORMAT}', creation_date)", "file_size"],
            tables=tables,
            group_by="book_id",
            **kwargs
        )

    def search_word_appearances(self, cols=None, tables=None, unique_words=False, order_by=None, **kwargs):
        """
        Search the word appearances table with dynamic filters
        :param cols: Iterable of columns to select
        :param tables: Additional tables needed for the search
        :param unique_words: When True, the same word will not be repeated
        :param order_by: String to be used for ORDER BY
        :param kwargs: Additional arguments to build_query
        :return: All the matched appearances
        """

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

    def word_location_to_offset(self, book_id, sentence, sentence_index, word_end_offset=False):
        """
        Search a book for the exact offset of a word in a sentence.
        :param book_id: The book id of the book
        :param sentence: The sentence number
        :param sentence_index: The index of the word in the sentence
        :param word_end_offset: If True, the returned offset is of the end of the word
        :return: The offset as (line, offset) pair
        """
        query = queries.WORD_LOCATION_TO_END_OFFSET if word_end_offset else queries.WORD_LOCATION_TO_OFFSET
        return self.execute(query, (book_id, sentence, sentence_index)).fetchone()

    #
    # Query Database Functions
    #

    def all_words(self):
        """
        Get a list of all the inserted words.
        :return: The list of words
        """
        return self.execute(queries.ALL_WORDS).fetchall()

    def all_documents(self, date_format=DATE_FORMAT):
        """
        Get a list of all the inserted books.
        :param date_format: The date format to use for the book date
        :return: The list of books
        """
        return self.execute(queries.ALL_BOOKS, (date_format,)).fetchall()

    def get_book_title(self, book_id):
        """
        Get the title of a book.
        :param book_id: The book id of the book
        :return: The book title
        """
        return self.execute(queries.BOOK_ID_TO_TITLE, (book_id,)).fetchone()

    def get_book_full_name(self, book_id):
        """
        Get the full name (TITLE by AUTHOR) of a book.
        :param book_id: The book id of the book
        :return: The full name of the book
        """
        return self.execute(queries.BOOK_ID_TO_FULL_NAME, (book_id,)).fetchone()

    def get_book_path(self, book_id):
        """
        Get the file path of a book.
        :param book_id: The book id of the book
        :return: The book file path
        """
        return self.execute(queries.BOOK_ID_TO_PATH, (book_id,)).fetchone()

    def all_book_words(self, book_id):
        """
        Get a list the words in the book, ordered by appearance.
        :param book_id: The book id of the book
        :return: The list of words
        """
        return iter(self.execute(queries.ALL_BOOK_WORDS, (book_id,)))

    def all_groups(self):
        """
        Get a list of all the inserted groups.
        :return: The list of groups
        """
        return self.execute(queries.ALL_GROUPS).fetchall()

    def words_in_group(self, group_id):
        """
        Get a list the words in a group.
        :param group_id: The group id of the group
        :return: The list of words, as pairs of (id, name)
        """
        return self.execute(queries.ALL_WORDS_IN_GROUP, (group_id,)).fetchall()

    def all_phrases(self):
        """
        Get a list of all the inserted phrases.
        :return: The list of phrases, as pairs of (text, id)
        """
        return self.execute(queries.ALL_PHRASES).fetchall()

    def words_in_phrase(self, phrase_id):
        """
        Get a list the words in a phrase, ordered by appearance.
        :param phrase_id: The phrase id of the phrase
        :return: The list of word ids
        """
        return self.execute(queries.ALL_WORDS_IN_PHRASE, (phrase_id,)).fetchall()

    def find_phrase(self, phrase_id):
        """
        Search a phrase for all of his appearances in book.
        :param phrase_id: The phrase id of the phrase
        :return: The list of appearances as (book_id, sentence, start_index, end_index) tuples.
        """
        return self._run_sql_script(DocumentDatabase.SCRIPTS.SEARCH_PHRASE, (phrase_id,)).fetchall()
