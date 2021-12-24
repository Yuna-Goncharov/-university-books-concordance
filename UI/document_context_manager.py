from tkinter.scrolledtext import ScrolledText

from UI import UI_defaults as sgh
from utils.utils import cached_read


class DocumentPreview:

    def __init__(self, db, multiline_element, name_element):
        self.db = db
        self.multiline = multiline_element
        self.name = name_element
        self.curr_document_id = None

    def initialize(self):
        text_widget = self.multiline.TKText
        text_widget.tag_configure("highlight",
                                  foreground=sgh.WORD_HIGHLIGHT_TEXT_COLOR,
                                  background=sgh.WORD_HIGHLIGHT_BG_COLOR)
        text_widget.mark_set("highlightStart", "0.0")
        text_widget.mark_set("highlightEnd", "0.0")

    def hide_preview(self):
        self.name.update(value="")
        self.multiline.update(value="")
        self.curr_document_id = None

    def _preview_document(self, document_id):

        if self.curr_document_id != document_id:
            self.name.update(value=self.db.get_document_full_name(document_id)[0])

            path = self.db.get_document_path(document_id)
            if not path:
                raise FileNotFoundError

            document_data = cached_read(path[0])
            self.multiline.update(value=document_data)

            self.curr_document_id = document_id

    def _set_multiline_highlight(self, start_line, start_line_offset, end_line, end_line_offset):
        text_widget = self.multiline.TKText
        start = "%d.%d" % (start_line, start_line_offset)
        end = "%d.%d" % (end_line, end_line_offset)
        text_widget.tag_remove("highlight", "highlightStart", "highlightEnd")
        text_widget.mark_set("highlightStart", start)
        text_widget.mark_set("highlightEnd", end)
        text_widget.tag_add("highlight", "highlightStart", "highlightEnd")
        text_widget.see("highlightStart")

    def set_preview(self, document_id, start_line, start_line_offset, end_line_offset=None, end_line=None,
                    highlight_length=None):

        if highlight_length is not None and end_line is None and end_line_offset is None:
            end_line = start_line
            end_line_offset = start_line_offset + highlight_length
        else:
            assert end_line and end_line_offset

        try:
            self._preview_document(document_id)
        except FileExistsError:
            self.hide_preview()
            return

        self._set_multiline_highlight(start_line, start_line_offset, end_line, end_line_offset)
