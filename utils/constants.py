"""
This file contains general constants that are used in multiple places
"""

VALID_WORD_LETTERS = r"[^\W_]"
VALID_WORD_REGEX = rf"{VALID_WORD_LETTERS}+(({VALID_WORD_LETTERS}|')*{VALID_WORD_LETTERS}+)?"
DATE_FORMAT = "%d/%m/%Y"
XML_DATE_FORMAT = '%Y-%m-%d'
