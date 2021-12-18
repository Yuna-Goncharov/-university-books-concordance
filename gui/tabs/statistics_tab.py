from enum import Enum, auto

import PySimpleGUI as sg

import db.sql_queries as queries
import gui.simple_gui_helper as sgh
from gui.tabs.custom_tab import CustomTab
from utils.utils import float_to_str, file_size_to_str

ALL_BOOKS_FILTER = "> 0"


class StatisticsTab(CustomTab):
    """
    Calculate statistical information about the inserted data.
    """

    # General statistics about the amount of stuff inserted
    GENERAL_STATISTICS = (
        ("Total Books", queries.BOOKS_COUNT),
        ("Total Books Size", queries.TOTAL_SIZE),
        ("Total Groups", queries.GROUPS_COUNT),
        ("Average Words in Group", queries.AVG_WORDS_PER_GROUP),
        ("Total Phrases", queries.PHRASES_COUNT),
        ("Average Words in Phrase", queries.AVG_WORDS_PER_PHRASE)
    )

    # Specific statistics about a book (or all books)
    SPECIFIC_STATISTICS = (
        ("Total Words", queries.TOTAL_WORDS),
        ("Total Unique Words", queries.TOTAL_UNIQUE_WORDS),
        ("Total Letters", queries.TOTAL_LETTERS),
        ("Average Letters in Word", queries.AVG_LETTERS_PER_WORD)
    )

    # Specific statistics template to be replaced with a column name
    SPECIFIC_STATISTICS_TEMPLATE = (
        ("Total {count_column}s", queries.TOTAL_COLUMN_COUNT),
        ("Average Words in {count_column}", queries.WORDS_COUNT),
        ("Average Letters in {count_column}", queries.LETTERS_COUNT)
    )

    # Event keys
    class EventKeys(Enum):
        SELECT_BOOK = auto()

    def __init__(self, db):
        super().__init__(db, "Statistics", [[]])
        self.db.add_book_insert_callback(self._update_book_dropdown)
        self.db.add_group_insert_callback(self._refresh_general_statistics)
        self.db.add_group_word_insert_callback(self._refresh_general_statistics)
        self.db.add_phrase_insert_callback(self._refresh_general_statistics)

        self.selected_book_id = None
        self.book_names_to_id = {}
        self.layout(
            [
                [sg.Sizer(v_pixels=20)],
                [self._create_general_statistics_frame()],
                [sg.Sizer(v_pixels=20)],
                [self._create_book_specific_statistics_frame()]
            ]
        )

    @staticmethod
    def _create_elements(elements_list, title, query, font=sgh.MEDIUM_FONT_SIZE):
        result_text = sg.Text(text="0", size=(10, 1), pad=(0, 5), font=font, text_color=sgh.INPUT_COLOR)
        title_text = sg.Text(text=title + ": ", size=(25, 1), font=font)
        elements_list.append((title, result_text, query))
        return title_text, result_text

    def _create_general_statistics_frame(self):
        self.general_statistics = []

        statistic_lines = []
        for title, query in StatisticsTab.GENERAL_STATISTICS:
            title, result_text = self._create_elements(self.general_statistics, title, query, sgh.BIG_FONT_SIZE)
            statistic_lines.append([title, result_text])

        frame = sg.Frame(
            title="General Statistics",
            layout=statistic_lines
        )

        return frame

    def _create_book_specific_statistics_frame(self):
        search_book_txt = sg.Text(
            text="Select Book:",
            font=sgh.BIG_FONT_SIZE
        )

        self.books_dropdown = sg.Combo(
            values=["All"],
            default_value="All",
            readonly=True,
            size=(40, 1),
            font=sgh.BIG_FONT_SIZE,
            text_color=sgh.DROP_DOWN_TEXT_COLOR,
            background_color=sgh.NO_BG,
            enable_events=True,
            key=StatisticsTab.EventKeys.SELECT_BOOK
        )

        self.specific_statistics = []
        first_rows = []
        for rows_counter, (title, query) in enumerate(StatisticsTab.SPECIFIC_STATISTICS):
            title_text, result_text = self._create_elements(self.specific_statistics, title, query, sgh.BIG_FONT_SIZE)

            first_rows.append([title_text, result_text])
            if rows_counter % 2 == 1:
                first_rows.append([sg.Sizer(v_pixels=20)])

        second_cols = []
        for column in "paragraph", "line", "sentence":
            col_rows = []
            for title, query in StatisticsTab.SPECIFIC_STATISTICS_TEMPLATE:
                title_text, result_text = self._create_elements(self.specific_statistics,
                                                                title.format(count_column=column.title()),
                                                                query.format(count_column=column))

                col_rows.append([title_text, result_text])
            second_cols.append(sg.Column(layout=col_rows))

        frame = sg.Frame(
            title="Book Statistics",
            layout=
            [
                [search_book_txt, self.books_dropdown],
                [sg.Sizer(v_pixels=30)]
            ] +
            first_rows +
            [
                [sg.Sizer(v_pixels=30)],
                sum([[col, sg.VerticalSeparator()] for col in second_cols], [])[:-1],
            ],
            element_justification=sgh.CENTER
        )

        return frame

    def initialize(self):
        self.reload()

    def reload(self):
        self.selected_book_id = None
        self._update_book_dropdown()
        self.books_dropdown.update(value="All")

    @property
    def callbacks(self):
        return {
            StatisticsTab.EventKeys.SELECT_BOOK: self._select_book,
        }

    def _update_book_dropdown(self):
        """ Update the list of available books """
        books = self.db.all_books()
        self.book_names_to_id = {f'{book[1]} by {book[2]}': book[0] for book in books}

        book_options = ["All"] + list(self.book_names_to_id.keys())
        self.books_dropdown.update(values=book_options, value=self.books_dropdown.get())

        # If the list of books was updated, the general statistics also needs to be updated
        self._refresh_general_statistics()

        # Update the specific statistics if "All" are selected
        if self.selected_book_id is None:
            self._refresh_specific_statistics()

    def _select_book(self):
        """ Select a book from the list """
        old_id = self.selected_book_id
        self.selected_book_id = self.book_names_to_id.get(self.books_dropdown.get())

        # Don't refresh if there is only 1 book, or the same book is selected
        if len(self.book_names_to_id) > 1 and self.selected_book_id != old_id:
            self._refresh_specific_statistics()

    @staticmethod
    def _single_result_to_str(cursor):
        # Fetch one result from the cursor and select the first column
        result = cursor.fetchone()[0]
        return float_to_str(result, ndigits=3)

    def _refresh_general_statistics(self, _updated_group=None):
        """ Re-calculate all the general statistics """
        for _text, element, query in self.general_statistics:
            result = self.db.execute(query)
            if query == queries.TOTAL_SIZE:
                element.update(value=file_size_to_str(result.fetchone()[0]))
            else:
                element.update(value=self._single_result_to_str(result))

    def _refresh_specific_statistics(self):
        """ Re-calculate all the specific statistics about the currently selected book """
        book_id_filter = ALL_BOOKS_FILTER if self.selected_book_id is None else f"== {self.selected_book_id}"

        for _text, element, query in self.specific_statistics:
            result = self.db.execute(query.format(book_id_filter=book_id_filter))
            element.update(value=self._single_result_to_str(result))
