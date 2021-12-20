from tkinter.scrolledtext import ScrolledText

from UI import UI_defaults as sgh
from utils.utils import cached_read


class DocumentPreview:
    """
    Handles the book preview elements
    """

    def __init__(self, db, multiline_element, title_element):
        self.db = db
        self.multiline = multiline_element
        self.title = title_element
        self.curr_book_id = None

    def initialize(self):
        """ Initialize the highlight tag in the multiline text widget """
        text_widget = self.multiline.TKText  # type: ScrolledText
        text_widget.tag_configure("highlight",
                                  foreground=sgh.WORD_HIGHLIGHT_TEXT_COLOR,
                                  background=sgh.WORD_HIGHLIGHT_BG_COLOR)
        text_widget.mark_set("highlightStart", "0.0")
        text_widget.mark_set("highlightEnd", "0.0")

    def hide_preview(self):
        """ Hide the current preview """
        self.title.update(value="")
        self.multiline.update(value="")
        self.curr_book_id = None

    def _preview_book(self, book_id):
        """
        Switch the preview to the given book.
        :param book_id: The book id of the book to preview
        """

        # Check if the book is already shown
        if self.curr_book_id != book_id:
            # Update the title
            self.title.update(value=self.db.get_document_full_name(book_id)[0])

            # Get the book file
            path = self.db.get_document_path(book_id)
            if not path:
                raise FileNotFoundError

            # Preview the book data
            book_data = cached_read(path[0])
            self.multiline.update(value=book_data)

            self.curr_book_id = book_id

    def _set_multiline_highlight(self, start_line, start_line_offset, end_line, end_line_offset):
        """
        Switch the currently highlighted text.
        :param start_line: The line to start highlighting from
        :param start_line_offset: The line offset to start highlighting from
        :param end_line: The line to end the highlighting at
        :param end_line_offset: The line offset to end the highlighting at
        """
        text_widget = self.multiline.TKText  # type: ScrolledText
        start = "%d.%d" % (start_line, start_line_offset)
        end = "%d.%d" % (end_line, end_line_offset)
        text_widget.tag_remove("highlight", "highlightStart", "highlightEnd")
        text_widget.mark_set("highlightStart", start)
        text_widget.mark_set("highlightEnd", end)
        text_widget.tag_add("highlight", "highlightStart", "highlightEnd")
        text_widget.see("highlightStart")

    def set_preview(self, book_id, start_line, start_line_offset, end_line_offset=None, end_line=None,
                    highlight_length=None):
        """
        Switch the currently shown book and the highlighted text.
        :param book_id: The book id of the book to preview
        :param start_line: The line to start highlighting from
        :param start_line_offset: The line offset to start highlighting from
        :param end_line: If given, the line to end the highlighting at
        :param end_line_offset: If given, the line offset to end the highlighting at
        :param highlight_length: If given, the length of the highlight in the line
        """

        # If only the length is given, calculate the end offset
        if highlight_length is not None and end_line is None and end_line_offset is None:
            end_line = start_line
            end_line_offset = start_line_offset + highlight_length
        else:
            # If the length isn't given, then the end line and offset should be given
            assert end_line and end_line_offset

        # Preview the book
        try:
            self._preview_book(book_id)
        except FileExistsError:
            # If the book couldn't be opened, hide the previously shown book
            self.hide_preview()
            return

        # Set the highlight
        self._set_multiline_highlight(start_line, start_line_offset, end_line, end_line_offset)
