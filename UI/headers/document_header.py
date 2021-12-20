from datetime import datetime
from enum import Enum, auto
from os.path import splitext, split
from subprocess import Popen

import PySimpleGUI as sg

import UI.UI_defaults as sgh
from db.exceptions import NonUniqueError, CheckError
from UI.headers.custom_header import CustomHeader
from utils.book_parser import parse_book_file
from utils.constants import DATE_FORMAT
from utils.utils import file_size_to_str


class DocumentHeader(CustomHeader):

    class EventKeys(Enum):
        FILE_INPUT = auto()
        INSERT_DOCUMENT = auto()
        UPDATE_FILTER = auto()
        DOCUMENTS_TABLE = auto()
        OPEN_DOCUMENT = auto()

    def __init__(self, db):
        super().__init__(db, "Document Browser", [[]])
        self.db.add_document_insert_callback(self._update_documents_table)

        self.filters = {}
        self.selected_document_id = None

        self.layout([
            [sg.Text("Insert New Document", font=sgh.HUGE_FONT_SIZE)],
            [self._create_document_form_frame()],
            [sg.Sizer(v_pixels=20)],
            [sg.Text("Inserted Documents", font=sgh.HUGE_FONT_SIZE)],
            [self._create_documents_explorer_frame()]
        ])

    def _create_document_form_frame(self):
        self.file_input = sg.InputText(enable_events=True, key=DocumentHeader.EventKeys.FILE_INPUT)
        browse_button = sg.FileBrowse(file_types=(("Text files", "*.txt"), ("All Files", "*")))
        self.name_input = sg.InputText()
        self.author_input = sg.InputText()
        self.date_input = sg.InputText()

        insert_document_button = sg.Ok("Insert Document", key=DocumentHeader.EventKeys.INSERT_DOCUMENT, size=(20, 0))
        self.error_text = sg.Text("", text_color=sgh.ERROR_TEXT_COLOR, auto_size_text=False)

        frame = sg.Frame(
            title="",
            layout=[
                [sg.Text("Doc Path:", size=(8, 1)), self.file_input, browse_button],
                [sg.Text("Name:", size=(8, 1)), self.name_input],
                [sg.Text("Author:", size=(8, 1)), self.author_input],
                [sg.Text("Date:", size=(8, 1)), self.date_input],
                [insert_document_button, self.error_text],
            ]
        )

        return frame

    def _create_documents_filter_row(self):
        def _create_filter_input():
            return sg.InputText(
                default_text="",
                size=(20, 1),
                enable_events=True,
                key=DocumentHeader.EventKeys.UPDATE_FILTER
            )

        row = []
        self.str_filters = []
        for text, filter_name in ("Document Name", "title"), ("Author", "author"), ("Word Appearance", "value"):
            element = _create_filter_input()
            row += [sg.Text(f"{text}: ", pad=((20, 5), 10)), element]
            self.str_filters.append((filter_name, element))

        return row

    def _create_documents_explorer_frame(self):
        self.books_table = sg.Table(
            values=[],
            headings=["Book ID", "Name", "Author", "Doc Path", "Created Date"],
            num_rows=13,
            justification=sg.TEXT_LOCATION_LEFT,
            col_widths=[0, 30, 20, 40, 13],
            auto_size_columns=False,
            enable_events=True,
            visible_column_map=[False, True, True, True, True],
            key=DocumentHeader.EventKeys.DOCUMENTS_TABLE
        )

        open_document_button = sg.Button("Open Selected Document", key=DocumentHeader.EventKeys.OPEN_DOCUMENT)

        frame = sg.Frame(
            title="",
            layout=[
                [sg.Sizer(v_pixels=20)],
                self._create_documents_filter_row(),
                [sg.Sizer(v_pixels=10)],
                [self.books_table],
                [sg.Sizer(v_pixels=70, h_pixels=1000), open_document_button],
                [sg.Sizer(v_pixels=30)]
            ],
            element_justification=sgh.CENTER, pad=(10, 10)
        )

        return frame

    def initialize(self):
        self._update_books_filter()

    def reload(self):
        self._clear_book_insert_frame()

        for _filter_name, element in self.str_filters:
            element.update("")
        self._update_books_filter()

        self._update_documents_table()

    @property
    def callbacks(self):
        return {
            DocumentHeader.EventKeys.FILE_INPUT: self._load_file_input,
            DocumentHeader.EventKeys.INSERT_DOCUMENT: self._insert_book,
            DocumentHeader.EventKeys.UPDATE_FILTER: self._update_books_filter,
            DocumentHeader.EventKeys.DOCUMENTS_TABLE: self._select_book,
            DocumentHeader.EventKeys.OPEN_DOCUMENT: self._open_book_file
        }

    def _load_file_input(self):
        """ Try to load the input file as it is being typed """

        path = self.file_input.get()
        # The default book name is the filename
        book_name = splitext(split(path)[-1])[0].replace('_', ' ').title()

        # Parse the book file
        try:
            name, author, date, size = parse_book_file(path)
            size_str = file_size_to_str(size)
            if name:
                book_name = name
            if not author:
                author = "Unknown"
        except (OSError, FileNotFoundError):
            size_str = "None"
            author = None
            date = None

        # Update the different inputs
        if date:
            self.date_input.update(datetime.fromtimestamp(date).strftime(DATE_FORMAT))

        self.name_input.update(book_name)
        self.author_input.update(author)
        self.error_text.update("")

    def _clear_book_insert_frame(self):
        """ Clear the insertion frame inputs """
        self.file_input.update("")
        self.name_input.update("")
        self.author_input.update("")
        self.date_input.update("")
        self.error_text.update("")

    def _insert_book(self):
        """ Insert the book to the database """
        error_msg = ""
        try:
            date = datetime.strptime(self.date_input.get(), DATE_FORMAT)
            self.db.add_book(self.name_input.get(),
                             self.author_input.get(),
                             self.file_input.get(),
                             date)
            self._update_documents_table()
            self._clear_book_insert_frame()
        except FileNotFoundError:
            error_msg = "Failed to open the file."
        except ValueError:
            error_msg = "Bad date format."
        except NonUniqueError:
            error_msg = "Book already exists."
        except CheckError:
            error_msg = "Illegal input."

        self.error_text.update(error_msg)

    def _update_books_filter(self):
        """ Update the dynamic filters for the books list"""
        for filter_name, element in self.str_filters:
            letters_filter = element.get()
            if letters_filter:
                letters_filter = letters_filter.replace("\"", "\"\"")  # Escape all '"'
                letters_filter = letters_filter.replace("\\", "\\\\")  # Escape all '\'
                letters_filter = letters_filter.replace("%", "\\%")  # Escape all '%'
                letters_filter = letters_filter.replace("_", "\\_")  # Escape all '_'
                self.filters[filter_name] = f"%{letters_filter}%"
            else:
                self.filters[filter_name] = None

        self._update_documents_table()

    def _get_books_filter_tables(self):
        """ Return the additional tables needed for the current filters"""
        filter_tables = []
        if self.filters["value"]:
            filter_tables += ["word", "word_appearance"]
        return filter_tables

    def _update_documents_table(self):
        """ Update the books list shown """
        books = self.db.search_books(tables=self._get_books_filter_tables(), **self.filters)
        self.books_table.update(values=[book[:5] + (file_size_to_str(book[5]),) for book in books])

    def _select_book(self):
        """ Select a book from the books list """
        if self.books_table.SelectedRows:
            selected_book_row = self.books_table.SelectedRows[0]
            if selected_book_row < len(self.books_table.Values):
                self.selected_document_id = self.books_table.Values[selected_book_row][0]

    def _open_book_file(self):
        """ Open the selected book with the default editing program """
        if self.books_table.SelectedRows:
            selected_book_row = self.books_table.SelectedRows[0]
            if selected_book_row < len(self.books_table.Values):
                selected_book_path = self.books_table.Values[selected_book_row][3]
                Popen(f'"{selected_book_path}"', shell=True)
