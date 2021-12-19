from enum import Enum, auto

import PySimpleGUI as sg

import UI.UI_defaults as sgh
from db.exceptions import NonUniqueError, CheckError
from UI.headers.custom_header import CustomHeader

INVALID_GROUP_NAMES = ["none", "all"]


class GroupHeader(CustomHeader):
    """
    Insert new groups, and fill them with words.
    """

    class EventKeys(Enum):
        GROUP_INPUT = auto()
        WORD_INPUT = auto()
        INSERT_GROUP = auto()
        INSERT_WORD = auto()
        GROUPS_LIST = auto()
        WORDS_LIST = auto()

    def __init__(self, db):
        super().__init__(db, "Word Groups Pairs Browser", [[]])

        # Add callbacks
        self.db.add_group_insert_callback(self._update_groups_list)
        self.db.add_group_word_insert_callback(self._group_word_insertion_callback)

        self.groups_list = []
        self.selected_group_id = None

        self.layout([
            [sg.Sizer(h_pixels=5), self._create_group_column(), sg.VerticalSeparator(), self._create_word_column()]
        ])

    def _create_group_column(self):
        self.group_input = sg.InputText(
            size=(30, 1),
            font=sgh.MEDIUM_FONT_SIZE,
            enable_events=True,
            text_color=sgh.INPUT_COLOR,
            key=GroupHeader.EventKeys.GROUP_INPUT
        )
        insert_group_button = sg.Ok(
            button_text="Insert Group",
            key=GroupHeader.EventKeys.INSERT_GROUP, size=(10, 1)
        )

        create_group_title = sg.Text(
            text="Create New Words Group",
            justification=sg.TEXT_LOCATION_CENTER,
            font=sgh.TITLE_FONT_SIZE
        )
        self.group_error_text = sg.Text(
            text="",
            text_color=sgh.ERROR_TEXT_COLOR,
            auto_size_text=False
        )

        self.select_group_list = sg.Listbox(
            values=[""],
            auto_size_text=True,
            font=sgh.BIG_FONT_SIZE,
            size=(45, 100),
            pad=(0, (0, 30)),
            select_mode=sg.SELECT_MODE_SINGLE,
            enable_events=True,
            key=GroupHeader.EventKeys.GROUPS_LIST
        )

        col = sg.Column(
            layout=[
                [create_group_title],
                [self.group_input, insert_group_button],
                [self.group_error_text],
                [self.select_group_list]
            ],
            element_justification=sgh.CENTER
        )

        return col

    def _create_word_column(self):
        self.word_input = sg.InputText(
            size=(30, 1),
            font=sgh.MEDIUM_FONT_SIZE,
            enable_events=True,
            text_color=sgh.INPUT_COLOR,
            key=GroupHeader.EventKeys.WORD_INPUT
        )

        insert_word_button = sg.Ok(
            button_text="Insert Word",
            key=GroupHeader.EventKeys.INSERT_WORD,
            size=(10, 1)
        )

        self.add_words_title = sg.Text(
            text=f"Add Words to Group",
            auto_size_text=False,
            justification=sg.TEXT_LOCATION_CENTER,
            font=sgh.TITLE_FONT_SIZE
        )

        self.words_error_text = sg.Text(
            text="",
            text_color=sgh.ERROR_TEXT_COLOR,
            auto_size_text=False
        )

        self.words_list = sg.Listbox(
            values=[""],
            auto_size_text=True,
            font=sgh.BIG_FONT_SIZE,
            size=(45, 100),
            pad=(0, (0, 30)),
            select_mode=sg.SELECT_MODE_SINGLE,
            enable_events=True,
            key=GroupHeader.EventKeys.WORDS_LIST
        )

        col = sg.Column(
            layout=[
                [self.add_words_title],
                [self.word_input, insert_word_button],
                [self.words_error_text],
                [self.words_list]
            ],
            element_justification=sgh.CENTER
        )

        return col

    def reload(self):
        self.group_input.update("")
        self._clear_group_error()

        self.word_input.update("")
        self._clear_word_error()

        self._update_groups_list()

        self.add_words_title.update(value=f"Add Words to Group")
        self._update_words_list()

    @property
    def callbacks(self):
        return {
            GroupHeader.EventKeys.GROUP_INPUT: self._clear_group_error,
            GroupHeader.EventKeys.WORD_INPUT: self._clear_word_error,
            GroupHeader.EventKeys.INSERT_GROUP: self._insert_group,
            GroupHeader.EventKeys.GROUPS_LIST: self._select_group,
            GroupHeader.EventKeys.INSERT_WORD: self._insert_word
        }

    def handle_enter(self, focused_element):
        if focused_element == self.group_input:
            self._insert_group()
        elif focused_element == self.word_input:
            self._insert_word()

    def _clear_group_error(self):
        """ Clear the group error text """
        self.group_error_text.update("")

    def _insert_group(self):
        """ Insert the entered group to the database """
        try:
            self.db.insert_words_group(self.group_input.get())
            self.group_input.update("")

            # Select the newly added group
            self.select_group_list.update(set_to_index=len(self.groups_list) - 1)
            self._select_group()
        except NonUniqueError:
            self.group_error_text.update("Group already exists.")
        except CheckError:
            self.group_error_text.update("Invalid group name.")

    def _update_groups_list(self):
        """ Update the list of groups """
        self.groups_list = self.db.all_groups()
        self.select_group_list.update(values=[group[1] for group in self.groups_list])

        # If we only have 1 item in the list, we should select it manually
        if len(self.groups_list) == 1:
            self.select_group_list.update(set_to_index=0)
            self._select_group()

    def _select_group(self):
        """ Select a group to insert words into """
        select_group_list_indexes = self.select_group_list.get_indexes()
        if select_group_list_indexes:
            selected_group_row = select_group_list_indexes[0]
            if selected_group_row < len(self.groups_list):
                self.selected_group_id, selected_group_name = self.groups_list[selected_group_row]
                self.add_words_title.update(value=f"Add Words to {selected_group_name}")
                self._update_words_list()

    def _clear_word_error(self):
        """ Clear the word insert error text """
        self.words_error_text.update("")

    def _insert_word(self):
        """ Insert the entered word into the currently selected group """
        if self.selected_group_id is not None:
            try:
                self.db.insert_word_to_group(self.selected_group_id, self.word_input.get())
                self.word_input.update("")
            except NonUniqueError:
                self.words_error_text.update("Word already exists.")
            except CheckError:
                self.words_error_text.update("Invalid word.")
        else:
            self.words_error_text.update("No group was selected.")

    def _group_word_insertion_callback(self, group_id):
        """ Update the words list if the currently selected group was updated"""
        if self.selected_group_id == group_id:
            self._update_words_list()

    def _update_words_list(self):
        """ Update the words list with the words from the currently selected group """
        self.words_list.update(values=[name for word_id, name in self.db.words_in_group(self.selected_group_id)])
