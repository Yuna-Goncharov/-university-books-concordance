from enum import Enum, auto

import PySimpleGUI as sg

import db.sql_queries as queries
import UI.UI_defaults as sgh
from UI.headers.custom_header import CustomHeader
from utils.utils import float_to_str, file_size_to_str

ALL_DOCUMENTS_FILTER = "> 0"


class StatisticsHeader(CustomHeader):

    GENERAL_STATISTICS = (
        ("Total Documents", queries.DOCUMENTS_COUNT),
        ("Total Groups", queries.GROUPS_COUNT),
        ("Average Words in Group", queries.AVG_WORDS_PER_GROUP),
        ("Total Phrases", queries.PHRASES_COUNT),
        ("Average Words in Phrase", queries.AVG_WORDS_PER_PHRASE)
    )

    class EventKeys(Enum):
        SELECT_DOCUMENT = auto()

    def __init__(self, db):
        super().__init__(db, "Statistics Browser", [[]])
        self.db.add_document_insert_callback(self._update_document_dropdown)
        self.db.add_group_insert_callback(self._refresh_general_statistics)
        self.db.add_group_word_insert_callback(self._refresh_general_statistics)
        self.db.add_phrase_insert_callback(self._refresh_general_statistics)

        self.selected_document_id = None
        self.document_names_to_id = {}
        self.layout(
            [
                [sg.Sizer(v_pixels=20)],
                [self._create_general_statistics_frame()]
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
        for title, query in StatisticsHeader.GENERAL_STATISTICS:
            title, result_text = self._create_elements(self.general_statistics, title, query, sgh.BIG_FONT_SIZE)
            statistic_lines.append([title, result_text])

        frame = sg.Frame(
            title="Statistics: ",
            font=sgh.BIG_FONT_SIZE,
            layout=statistic_lines,
            size=(1000, 250),
            title_location=sg.TITLE_LOCATION_TOP,
            element_justification=sgh.LEFT
        )

        return frame

    def initialize(self):
        self.reload()

    def reload(self):
        self.selected_document_id = None

    @property
    def callbacks(self):
        return {
            StatisticsHeader.EventKeys.SELECT_DOCUMENT: self._select_document,
        }

    def _update_document_dropdown(self):
        documents = self.db.all_documents()
        self.document_names_to_id = {f'{document[1]} by {document[2]}': document[0] for document in documents}

        document_options = ["All"] + list(self.document_names_to_id.keys())

        self._refresh_general_statistics()

    def _select_document(self):
        old_id = self.selected_document_id

    @staticmethod
    def _single_result_to_str(cursor):
        result = cursor.fetchone()[0]
        return float_to_str(result, ndigits=3)

    def _refresh_general_statistics(self, _updated_group=None):
        for _text, element, query in self.general_statistics:
            result = self.db.execute(query)
            if query == queries.TOTAL_SIZE:
                element.update(value=file_size_to_str(result.fetchone()[0]))
            else:
                element.update(value=self._single_result_to_str(result))


