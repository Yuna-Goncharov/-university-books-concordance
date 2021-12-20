-- This file contains the schema definition for the books database

CREATE TABLE IF NOT EXISTS document (
    document_id INTEGER NOT NULL PRIMARY KEY,
    title TEXT NOT NULL,
    author TEXT NOT NULL,
    file_path TEXT NOT NULL UNIQUE,
    file_size INTEGER NOT NULL,
    creation_date DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(title, author),
    CHECK(title <> ''),
    CHECK(author <> ''),
    CHECK(file_path <> '')
);

CREATE TABLE IF NOT EXISTS word (
    word_id INTEGER NOT NULL PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    length INTEGER DEFAULT 0,
    CHECK(name <> '')
);

CREATE TRIGGER IF NOT EXISTS word_length_insertion
   AFTER INSERT
   ON word
   FOR EACH ROW
BEGIN
   UPDATE word SET length = LENGTH(name) WHERE word_id = new.word_id;
END;

CREATE TABLE IF NOT EXISTS word_appearance (
    word_index INTEGER NOT NULL,
    document_id INTEGER NOT NULL,
    word_id INTEGER NOT NULL,
    paragraph INTEGER NOT NULL,
    line INTEGER NOT NULL,
    line_index INTEGER NOT NULL,
    line_offset INTEGER NOT NULL,
    sentence INTEGER NOT NULL,
    sentence_index INTEGER NOT NULL,
    PRIMARY KEY(word_index, document_id, word_id),
    FOREIGN KEY(document_id) REFERENCES document,
    FOREIGN KEY(word_id) REFERENCES word
);

CREATE TABLE IF NOT EXISTS words_group (
    group_id INTEGER NOT NULL PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    CHECK(name <> '')
);

CREATE TABLE IF NOT EXISTS word_in_group (
    group_id INTEGER NOT NULL,
    word_id INTEGER NOT NULL,
    PRIMARY KEY(group_id, word_id),
    FOREIGN KEY(group_id) REFERENCES words_group,
    FOREIGN KEY(word_id) REFERENCES word
);

CREATE TABLE IF NOT EXISTS phrase (
    phrase_id INTEGER NOT NULL PRIMARY KEY,
    phrase_text TEXT NOT NULL,
    words_count INTEGER NOT NULL CHECK(words_count > 1)
);

CREATE TABLE IF NOT EXISTS word_in_phrase (
    phrase_id INTEGER NOT NULL,
    word_id INTEGER NOT NULL,
    phrase_index INTEGER NOT NULL,
    PRIMARY KEY(phrase_id, word_id, phrase_index),
    FOREIGN KEY(phrase_id) REFERENCES phrase,
    FOREIGN KEY(word_id) REFERENCES word
);