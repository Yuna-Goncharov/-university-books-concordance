from enum import Enum, auto
from threading import Timer

import PySimpleGUI as sg

import UI.UI_defaults as sgh
from BL.Documents_db import DocumentDatabase
from UI.document_context_manager import DocumentPreview
from UI.headers.custom_header import CustomHeader


class WordHeader(CustomHeader):
    WORDS_SORT_OPTIONS = {
        "Appearances": DocumentDatabase.APPEARANCES_ORDER,
        "Length": DocumentDatabase.LENGTH_ORDER
    }

    WORDS_SORT_DIRECTION = {
        "Increasing": "asc",
        "Decreasing": "desc",
    }

    DEFAULT_WORDS_SORT_ORDER = "Appearances"
    DEFAULT_WORDS_SORT_DIRECTION = "Decreasing"

    SEARCH_SYNTAX_HELP_TEXT = "You can use this filter to search for specific words.\n" \
                              "\n" \
                              "Use  _  as a wildcard for any character.\n" \
                              "Use  *   as a wildcard for 0 or more characters."

    FILTER_UPDATE_SCHEDULE_TIME = 0.5

    class EventKeys(Enum):
        UPDATE_FILTER = auto()
        SCHEDULE_UPDATE_FILTER = auto()
        CLEAR_FILTER = auto()
        REGEX_HELP = auto()
        WORDS_SORT = auto()
        WORDS_DIRECTION = auto()
        WORDS_LIST = auto()
        APPR_TABLE = auto()

    def __init__(self, db):
        super().__init__(db, "Words Browser", [[]])
        self.db.add_document_insert_callback(self._update_document_dropdown)
        self.db.add_group_insert_callback(self._update_group_dropdown)
        self.db.add_group_word_insert_callback(self._group_word_insertion_callback)
        sg.SetOptions(input_text_color=sgh.get_theme_field("TEXT_INPUT"))

        self.curr_words_order = \
            WordHeader.WORDS_SORT_OPTIONS[WordHeader.DEFAULT_WORDS_SORT_ORDER]
        self.curr_words_direction = \
            WordHeader.WORDS_SORT_DIRECTION[WordHeader.DEFAULT_WORDS_SORT_DIRECTION]

        self.update_filter_timer = None
        self.old_word_appearance_filters = None

        self.words_list = []
        self.document_names_to_id = {}
        self.group_name_to_id = {"All": "%"}
        self.curr_showed_document = None
        self.selected_word_id = None
        self.selected_word_length = None
        self.words_filters = {}
        self.word_appearance_filters = {}

        self.layout([
            [self._create_filter_frame()],
            [self._create_word_list_column(), self._create_word_preview_column()]
        ])

    def _create_filter_frame(self):
        self.letters_filter_input = sg.InputText(
            default_text="",
            size=(30, 1),
            pad=(0, 1),
            enable_events=True,
            text_color=sgh.INPUT_COLOR,
            key=WordHeader.EventKeys.SCHEDULE_UPDATE_FILTER
        )

        self.document_filter_dropdown = sg.Combo(
            values=["All"],
            default_value="All",
            size=(25, 1),
            pad=(0, 1),
            enable_events=True,
            readonly=True,
            text_color=sgh.DROP_DOWN_TEXT_COLOR,
            font=sgh.SMALL_FONT_SIZE,
            background_color=sgh.NO_BG,
            key=WordHeader.EventKeys.UPDATE_FILTER
        )

        self.group_filter_dropdown = sg.Combo(
            values=["None", "All"],
            default_value="None",
            size=(25, 1),
            pad=(0, 1),
            enable_events=True,
            readonly=True,
            text_color=sgh.DROP_DOWN_TEXT_COLOR,
            font=sgh.SMALL_FONT_SIZE,
            background_color=sgh.NO_BG,
            key=WordHeader.EventKeys.UPDATE_FILTER
        )

        info_button = sg.Help("?", size=(3, 1), pad=(10, 1), key=WordHeader.EventKeys.REGEX_HELP)

        def _create_int_input():
            return sg.InputText(
                default_text="",
                size=(10, 1),
                pad=(10, 1),
                enable_events=True,
                background_color=sgh.THEME["INPUT"],
                text_color=sgh.INPUT_COLOR,
                key=WordHeader.EventKeys.SCHEDULE_UPDATE_FILTER
            )

        line_filter = _create_int_input()
        line_index_filer = _create_int_input()
        sentence_filter = _create_int_input()
        word_index_filter = _create_int_input()
        sentence_index_filter = _create_int_input()
        paragraph_filter = _create_int_input()

        self.int_filters = (
            (paragraph_filter, "paragraph"),
            (sentence_filter, "sentence"),
            (line_filter, "line"),
            (word_index_filter, "word_index"),
            (sentence_index_filter, "sentence_index"),
            (line_index_filer, "line_index")
        )

        clear_filter_button = sg.Button(
            button_text="Clear Filter",
            size=(10, 1),
            pad=(30, 0),
            key=WordHeader.EventKeys.CLEAR_FILTER
        )

        col1 = sg.Column(
            layout=[
                [sg.Text("Document:", pad=(0, 5), size=(10, 1)), self.document_filter_dropdown],
                [sg.Text("Group:", pad=(0, 5), size=(10, 1)), self.group_filter_dropdown]
            ]
        )

        col2 = sg.Column(
            layout=[
                [sg.Text("Line:", pad=(0, 5), size=(11, 1)), line_filter],
                [sg.Text("Line Index:", pad=(0, 5), size=(11, 1)), line_index_filer]
            ]
        )

        col3 = sg.Column(
            layout=[
                [sg.Text("Sentence:", pad=(0, 5), size=(13, 1)), sentence_filter],
                [sg.Text("Sentence Index:", pad=(0, 5), size=(13, 1)), sentence_index_filter]
            ]
        )

        col4 = sg.Column(
            layout=[
                [sg.Text("Paragraph:", pad=(0, 5), size=(13, 1)), paragraph_filter],
                [sg.Text("Word Index:", pad=(0, 5), size=(13, 1)), word_index_filter]
            ]
        )

        frame_layout = [
            [col1, col2, col3, col4],
            [info_button, sg.Text("Word:", pad=(10, 5)), self.letters_filter_input, clear_filter_button],
            [sg.Sizer(h_pixels=10000)]
        ]

        frame = sg.Frame(
            title="Words Filter",
            layout=frame_layout,
            size=(10, 100),
            pad=(0, (0, 10)),
            title_location=sg.TITLE_LOCATION_TOP,
            element_justification=sgh.CENTER)

        return frame

    def _create_word_list_column(self):
        self.words_order_dropdown = sg.Combo(
            values=list(WordHeader.WORDS_SORT_OPTIONS.keys()),
            default_value=WordHeader.DEFAULT_WORDS_SORT_ORDER,
            size=(11, 1),
            text_color=sgh.DROP_DOWN_TEXT_COLOR,
            enable_events=True,
            readonly=True,
            background_color=sgh.NO_BG,
            key=WordHeader.EventKeys.WORDS_SORT
        )

        self.words_direction_dropdown = sg.Combo(
            values=list(WordHeader.WORDS_SORT_DIRECTION.keys()),
            default_value=WordHeader.DEFAULT_WORDS_SORT_DIRECTION,
            text_color=sgh.DROP_DOWN_TEXT_COLOR,
            size=(11, 1),
            enable_events=True,
            readonly=True,
            background_color=sgh.NO_BG,
            key=WordHeader.EventKeys.WORDS_DIRECTION
        )

        self.words_counter_text = sg.Text("0 Results.", size=(15, 1), auto_size_text=False)

        self.select_word_list = sg.Listbox(
            values=[""],
            auto_size_text=True,
            size=(20, 100),
            select_mode=sg.SELECT_MODE_SINGLE,
            enable_events=True,
            key=WordHeader.EventKeys.WORDS_LIST
        )

        col = sg.Column(
            layout=[
                [sg.Text("Sort by: ", size=(6, 1)), self.words_order_dropdown],
                [sg.Text("Order: ", size=(6, 1)), self.words_direction_dropdown],
                [self.words_counter_text],
                [self.select_word_list]
            ]
        )

        return col

    def _create_word_preview_column(self):
        headers = [
            ("Document", True),
            ("Document Id", False),
            ("Offset", False),
            ("Index", True),
            ("Paragraph", True),
            ("Line", True),
            ("Line Index", True),
            ("Sentence", True),
            ("Sentence Index", True)
        ]

        col_widths = [max(len(col_name), 9) for col_name, _is_visible in headers]
        col_widths[0] = 30
        self.word_appr_table = sg.Table(
            values=[[''] * len(headers)],
            headings=[col_name for col_name, _is_visible in headers],
            num_rows=10,
            justification=sg.TEXT_LOCATION_CENTER,
            col_widths=col_widths,
            auto_size_columns=False,
            enable_events=True,
            select_mode=sg.SELECT_MODE_BROWSE,
            visible_column_map=[is_visible for _col_name, is_visible in headers],
            key=WordHeader.EventKeys.APPR_TABLE
        )

        document_title = sg.Text(
            text="",
            font=sgh.TITLE_FONT_SIZE,
            justification=sg.TEXT_LOCATION_CENTER,
            auto_size_text=False
        )
        document_context_multiline = sg.Multiline(
            default_text="",
            size=(100, 25),
            text_color=sgh.MULTILINE_TEXT_COLOR,
            background_color=sgh.MULTILINE_BG_COLOR,
            disabled=True
        )

        self.document_preview = DocumentPreview(self.db, document_context_multiline, document_title)

        col = sg.Column(
            layout=[
                [self.word_appr_table],
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
        self._update_document_dropdown()
        self._update_group_dropdown()

        self.words_order_dropdown.update(WordHeader.DEFAULT_WORDS_SORT_ORDER)
        self.words_direction_dropdown.update(WordHeader.DEFAULT_WORDS_SORT_DIRECTION)
        self._update_words_sort_order()
        self._update_words_sort_direction()

        self.document_preview.hide_preview()

        self._clear_filter()

    @property
    def callbacks(self):
        return {
            WordHeader.EventKeys.UPDATE_FILTER: self._update_filter,
            WordHeader.EventKeys.SCHEDULE_UPDATE_FILTER: self._schedule_filter_update,
            WordHeader.EventKeys.CLEAR_FILTER: self._clear_filter,
            WordHeader.EventKeys.REGEX_HELP: self._show_regex_help,
            WordHeader.EventKeys.WORDS_SORT: self._update_words_sort_order,
            WordHeader.EventKeys.WORDS_DIRECTION: self._update_words_sort_direction,
            WordHeader.EventKeys.WORDS_LIST: self._select_word,
            WordHeader.EventKeys.APPR_TABLE: self._select_word_appr
        }

    @staticmethod
    def _show_regex_help():
        sg.popup_ok(
            WordHeader.SEARCH_SYNTAX_HELP_TEXT,
            title="Words Search Syntax",
            font=sgh.FONT,
            non_blocking=False
        )

    def _update_document_dropdown(self):
        documents = self.db.all_documents()
        self.document_names_to_id = {f'{document[1]} by {document[2]}': document[0] for document in documents}

        document_options = ["All"] + list(self.document_names_to_id.keys())
        self.document_filter_dropdown.update(values=document_options, value=self.document_filter_dropdown.get())

        if self.word_appearance_filters.get("document_id") is None:
            self._update_words_list()

    def _update_group_dropdown(self):
        self.group_name_to_id = {"All": "%"}
        groups_list = self.db.all_groups()
        self.group_name_to_id.update({name: group_id for group_id, name in groups_list})

        selected_option = self.group_filter_dropdown.get()
        group_options = ["None"] + list(self.group_name_to_id.keys())
        self.group_filter_dropdown.update(values=group_options, value=selected_option)

        # If we selected "All" we need to update the list with words from the new group
        if selected_option == "All":
            self._update_words_list()

    def _group_word_insertion_callback(self, group_id):
        if self.words_filters["group_id"] in (group_id, "%"):
            self._update_words_list()

    def _cancel_filter_scheduler(self):
        if self.update_filter_timer is not None and self.update_filter_timer.is_alive():
            self.update_filter_timer.cancel()
            self.update_filter_timer = None

    def _trigger_filter_update_event(self):
        window = self.ParentForm
        window.LastButtonClicked = WordHeader.EventKeys.UPDATE_FILTER
        window.FormRemainedOpen = True
        if window.CurrentlyRunningMainloop:
            window.TKroot.quit()

    def _schedule_filter_update(self):
        self._cancel_filter_scheduler()
        self.update_filter_timer = Timer(
            interval=self.FILTER_UPDATE_SCHEDULE_TIME,
            function=self._trigger_filter_update_event
        )
        self.update_filter_timer.start()

        for element, filter_name in self.int_filters:
            self.word_appearance_filters[filter_name] = \
                WordHeader._get_int_input(element, self.words_filters.get(filter_name))

    def _clear_filter(self):
        self.letters_filter_input.update("")
        self.document_filter_dropdown.update("All")
        self.group_filter_dropdown.update("None")

        for element, _filter_name in self.int_filters:
            element.update("", background_color=sgh.GOOD_INPUT_BG_COLOR)
        self.word_appearance_filters = {}

        self._update_filter()

    def _update_filter(self):
        self._cancel_filter_scheduler()
        old_words_filters = self.words_filters.copy()

        selected_group = self.group_filter_dropdown.get()
        self.words_filters["group_id"] = self.group_name_to_id.get(selected_group)

        letters_filter = self.letters_filter_input.get()
        letters_filter = letters_filter.replace("\"", "\"\"")  # Escape all '"'
        letters_filter = letters_filter.replace("\\", "\\\\")  # Escape all '\'
        letters_filter = letters_filter.replace("%", "\\%")  # Escape all '%'
        letters_filter = letters_filter.replace("*", "%")
        self.words_filters["value"] = letters_filter

        selected_document = self.document_filter_dropdown.get()
        self.word_appearance_filters["document_id"] = self.document_names_to_id.get(selected_document)

        if self.words_filters != old_words_filters or \
                self.word_appearance_filters != self.old_word_appearance_filters:
            self._update_words_list()
            self.old_word_appearance_filters = self.word_appearance_filters.copy()

    @staticmethod
    def _get_int_input(input_element, default_value):
        int_input = default_value
        entered_number = input_element.get()
        try:
            int_input = int(entered_number)
            legal_number = True
        except ValueError:
            legal_number = len(entered_number) == 0
            if legal_number:
                int_input = None

        input_element.update(background_color=sgh.GOOD_INPUT_BG_COLOR if legal_number else sgh.BAD_INPUT_BG_COLOR)
        return int_input

    def _update_words_sort_order(self):
        new_order = WordHeader.WORDS_SORT_OPTIONS.get(self.words_order_dropdown.get())
        if new_order is not None:
            old_order = self.curr_words_order
            self.curr_words_order = new_order

            if self.curr_words_order != old_order:
                self._update_words_list()

    def _update_words_sort_direction(self):
        new_dir = WordHeader.WORDS_SORT_DIRECTION.get(self.words_direction_dropdown.get())
        if new_dir is not None:
            old_dir = self.curr_words_direction
            self.curr_words_direction = new_dir

            if self.curr_words_direction != old_dir:
                self._update_words_list()

    def _get_words_filter_tables(self):
        filter_tables = []
        if self.words_filters.get("group_id") is not None:
            filter_tables.append("word_in_group")
        return filter_tables

    def _update_words_list(self):
        self.words_list = self.db.search_word_appearances(
            cols=["word_id", "length", "name", "COUNT(word_index)"],
            tables=set(["word"] + self._get_words_filter_tables()),
            unique_words=True,
            order_by=self.curr_words_order + " " + self.curr_words_direction,
            **self.words_filters,
            **self.word_appearance_filters)

        self.words_counter_text.update(f"{len(self.words_list):,} Result{'s' if len(self.words_list) != 1 else ''}.")
        self.select_word_list.update(values=[f'{word[2]} ({word[3]:,})' for word in self.words_list])
        self._select_word()

    def _select_word(self):
        select_word_list_indexes = self.select_word_list.get_indexes()
        if select_word_list_indexes:
            selected_word_row = select_word_list_indexes[0]
            if selected_word_row < len(self.words_list):
                self.selected_word_id = self.words_list[selected_word_row][0]
                self.selected_word_length = self.words_list[selected_word_row][1]
        else:
            self.selected_word_id = None
            self.selected_word_length = None

        # Update the words list anyways, to show the new words \ hide the old ones
        self._update_word_appr_table()

    def _update_word_appr_table(self):
        if self.selected_word_id:
            appearances = self.db.search_word_appearances(
                cols=["document_id", "line_offset", "word_index", "paragraph", "line", "line_index", "sentence",
                      "sentence_index"],
                tables=["document"],
                word_id=self.selected_word_id,
                **self.word_appearance_filters)

            self.word_appr_table.update(
                values=[(self.db.get_document_title(appr[0])[0],) + appr for appr in appearances]
            )
        else:
            self.word_appr_table.update(values=[])

        if self.word_appr_table.TKTreeview.get_children():
            self.word_appr_table.TKTreeview.selection_set(1)
            self.word_appr_table.SelectedRows = [0]
            self._select_word_appr()
        else:
            self.document_preview.hide_preview()

    def _select_word_appr(self):
        if self.word_appr_table.SelectedRows:
            selected_word_appr_row = self.word_appr_table.SelectedRows[0]
            if selected_word_appr_row < len(self.word_appr_table.Values):
                if self.word_appr_table.Values[selected_word_appr_row]:
                    (_document_name, document_id, line_offset, _word_index, _paragraph, line) = \
                        self.word_appr_table.Values[selected_word_appr_row][0:6]

                    self.document_preview.set_preview(document_id, line, line_offset,
                                                      highlight_length=self.selected_word_length)
