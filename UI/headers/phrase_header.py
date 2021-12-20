from enum import Enum, auto

import PySimpleGUI as sg

import UI.UI_defaults as sgh
from db.exceptions import CheckError
from UI.book_context_manager import DocumentPreview
from UI.headers.custom_header import CustomHeader


class PhraseHeader(CustomHeader):
    # Event keys
    class EventKeys(Enum):
        PHRASE_INPUT = auto()
        ADD_PHRASE = auto()
        PHRASE_SELECTION = auto()
        PHRASE_APPR_TABLE = auto()

    def __init__(self, db):
        super().__init__(db, "Phrases Browser", [[]])
        self.db.add_document_insert_callback(self._search_phrase)

        self.phrases = {}
        self.selected_phrase_id = None
        self.curr_showed_book = None

        self.layout(
            [
                [sg.Sizer(v_pixels=20)],
                [sg.Sizer(h_pixels=12), self._create_phrase_insertion_column()],
                [sg.Sizer(v_pixels=20)],
                [sg.Sizer(h_pixels=12), self._create_phrase_preview_column()]
            ]
        )

    def _create_phrase_insertion_column(self):
        enter_phrase_txt = sg.Text(
            text="Insert a phrase:",
            size=(20, 1),
            font=sgh.BIG_FONT_SIZE
        )

        self.phrase_input = sg.InputText(
            default_text="",
            size=(41, 1),
            font=sgh.BIG_FONT_SIZE,
            text_color=sgh.INPUT_COLOR,
            enable_events=True,
            key=PhraseHeader.EventKeys.PHRASE_INPUT
        )
        add_phrase_button = sg.Ok("Insert", pad=(20, 1), size=(10, 1), key=PhraseHeader.EventKeys.ADD_PHRASE)

        search_phrase_txt = sg.Text(
            text="Phrase to be searched:",
            size=(20, 1),
            font=sgh.BIG_FONT_SIZE
        )

        self.phrase_dropdown = sg.Combo(
            values=[],
            default_value="",
            readonly=True,
            size=(40, 1),
            font=sgh.BIG_FONT_SIZE,
            text_color=sgh.DROP_DOWN_TEXT_COLOR,
            background_color=sgh.NO_BG,
            enable_events=True,
            key=PhraseHeader.EventKeys.PHRASE_SELECTION
        )

        self.phrase_input_error = sg.Text(
            text="",
            font=sgh.BIG_FONT_SIZE,
            text_color=sgh.ERROR_TEXT_COLOR,
            auto_size_text=False
        )

        col = sg.Column(
            layout=[
                [enter_phrase_txt, self.phrase_input, add_phrase_button, self.phrase_input_error],
                [search_phrase_txt, self.phrase_dropdown]
            ]
        )

        return col

    def _create_phrase_preview_column(self):
        self.appearances_count_text = sg.Text(
            text="Number of Appearances: None",
            font=sgh.BIG_FONT_SIZE,
            justification=sg.TEXT_LOCATION_CENTER,
            auto_size_text=False,
        )

        # header_name, is_visible
        headers = [
            ("Document Id", False),
            ("Document", True),
            ("Sentence", True),
            ("Start Sentence Index", True),
            ("Start Line", False),
            ("Start Line Offset", False),
            ("End Sentence Index", True),
            ("End Line", False),
            ("End Line Offset", False)
        ]
        col_widths = [max(len(col_name), 20) for col_name, _is_visible in headers]
        col_widths[1] = 50
        self.phrase_appr_table = sg.Table(
            values=[[''] * len(headers)],
            headings=[col_name for col_name, _is_visible in headers],
            num_rows=10,
            justification=sg.TEXT_LOCATION_CENTER,
            col_widths=col_widths,
            auto_size_columns=False,
            enable_events=True,
            select_mode=sg.SELECT_MODE_BROWSE,
            visible_column_map=[is_visible for _col_name, is_visible in headers],
            key=PhraseHeader.EventKeys.PHRASE_APPR_TABLE
        )

        document_title = sg.Text(
            text="",
            font=sgh.TITLE_FONT_SIZE,
            justification=sg.TEXT_LOCATION_CENTER,
            auto_size_text=False,
        )

        document_context_multiline = sg.Multiline(
            default_text="",
            size=(110, 25),
            text_color=sgh.MULTILINE_TEXT_COLOR,
            background_color=sgh.MULTILINE_BG_COLOR,
            disabled=True
        )

        self.document_preview = DocumentPreview(self.db, document_context_multiline, document_title)

        col = sg.Column(
            layout=[
                [self.appearances_count_text],
                [self.phrase_appr_table],
                [document_title],
                [document_context_multiline]
            ],
            element_justification=sgh.CENTER
        )

        return col

    def initialize(self):
        self.document_preview.initialize()
        self.reload()

    def reload(self):
        self.phrases = dict(self.db.all_phrases())
        self.phrase_input.update("")
        self.document_preview.hide_preview()
        self._update_phrase_dropdown()

    @property
    def callbacks(self):
        return {
            PhraseHeader.EventKeys.PHRASE_INPUT: self._clear_phrase_error,
            PhraseHeader.EventKeys.ADD_PHRASE: self._add_phrase,
            PhraseHeader.EventKeys.PHRASE_SELECTION: self._search_phrase,
            PhraseHeader.EventKeys.PHRASE_APPR_TABLE: self._select_phrase_appr
        }

    def handle_enter(self, focused_element):
        if focused_element == self.phrase_input:
            self._add_phrase()

    def _clear_phrase_error(self):
        """ Clear the phrase error text """
        self.phrase_input_error.update("")

    def _add_phrase(self):
        """ Insert the entered phrase to the database """
        phrase = self.phrase_input.get()
        if phrase not in self.phrases:
            try:
                self.phrases[phrase] = self.db.add_phrase(phrase)
                self.phrase_input.update("")
                self._update_phrase_dropdown(curr_value=phrase)
            except CheckError:
                self.phrase_input_error.update("Illegal phrase.", text_color=sgh.ERROR_TEXT_COLOR)
        else:
            self.phrase_input_error.update("Phrase already inserted.", text_color=sgh.ERROR_TEXT_COLOR)

    def _update_phrase_dropdown(self, curr_value=""):
        """ Update the list of available phrases for search """
        self.phrase_dropdown.update(values=list(self.phrases.keys()), value=curr_value)
        self._search_phrase()

    def _search_phrase(self):
        """ Search the selected phrase for all of his appearances """
        selected_phrase = self.phrase_dropdown.get()
        self.selected_phrase_id = self.phrases.get(selected_phrase)
        self._update_phrase_appr_table()

    def _update_phrase_appr_table(self):
        """ Update the appearances table with all the found appearances of the phrase """

        # Check if there is a selected phrase
        if self.selected_phrase_id:
            appearances = self.db.find_phrase(self.selected_phrase_id)

            # Iterate over the found phrases and convert them to the wanted table columns
            phrases_appr_table_values = []
            for document_id, sentence, start_index, end_index in appearances:
                start_line, start_line_offset = self.db.word_location_to_offset(document_id, sentence, start_index)
                end_line, end_line_offset = self.db.word_location_to_offset(document_id, sentence, end_index, True)

                phrases_appr_table_values.append((document_id, self.db.get_document_title(document_id)[0],
                                                  sentence,
                                                  start_index, start_line, start_line_offset,
                                                  end_index, end_line, end_line_offset))

            self.appearances_count_text.update(value=f"Number of Appearances: {len(phrases_appr_table_values)}")
            self.phrase_appr_table.update(values=phrases_appr_table_values)
        else:
            # No phrase was selected
            self.appearances_count_text.update(value=f"Number of Appearances: None")
            self.phrase_appr_table.update(values=[])

        # Check if there where any appearances found
        if self.phrase_appr_table.TKTreeview.get_children():
            # Manually select the first appearance to be shown
            self.phrase_appr_table.TKTreeview.selection_set(1)  # This updates the GUI widget
            self.phrase_appr_table.SelectedRows = [0]  # This updates PySimpleGUI's rows logic
            self._select_phrase_appr()
        else:
            self.document_preview.hide_preview()

    def _select_phrase_appr(self):
        if self.phrase_appr_table.SelectedRows:
            selected_word_appr_row = self.phrase_appr_table.SelectedRows[0]
            if selected_word_appr_row < len(self.phrase_appr_table.Values):
                if self.phrase_appr_table.Values[selected_word_appr_row]:
                    (document_id, document_title,
                     sentence,
                     start_index, start_line, start_line_offset,
                     end_index, end_line, end_line_offset) = self.phrase_appr_table.Values[selected_word_appr_row]

                    self.document_preview.set_preview(document_id, start_line, start_line_offset, end_line_offset, end_line)
