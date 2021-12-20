import tkinter as tk

import PySimpleGUI as sg

#
# Imported constants
#

CENTER = tk.CENTER
LEFT = tk.LEFT

#
# My constants
#

WINDOW_TITLE = "Documents Database"
WINDOW_SIZE = (1400, 900)
SELECTED_THEME = "MyTheme"
FONT = ("Ariel", 14)
SMALL_FONT_SIZE = None, 12
MEDIUM_FONT_SIZE = None, 15
BIG_FONT_SIZE = None, 17
TITLE_FONT_SIZE = BIG_FONT_SIZE
HUGE_FONT_SIZE = None, 20
BORDER_SIZE = 2
NO_BG = "#"

#
# Colors
#

WHITE = '#FFFFFF'
CYAN = "#89DDFF"
PINK = "#FF5370"
LIGHT_GREY = "#C3D3DE"
LIGHT_PURPLE = "#464B5D"
BLUE = '#7D96F7'
DARK_BLUE = "#1F2ACD"
DARKER_BLUE = "#0C2483"
DARKER_PURPLE2 = '#191A21'
BLACK = "#090B10"


#
# Theme Colors
#

INPUT_COLOR = CYAN
ERROR_TEXT_COLOR = PINK
GOOD_INPUT_BG_COLOR = DARKER_BLUE
BAD_INPUT_BG_COLOR = LIGHT_PURPLE
DROP_DOWN_TEXT_COLOR = DARK_BLUE
MULTILINE_TEXT_COLOR = LIGHT_GREY
MULTILINE_BG_COLOR = BLACK
WORD_HIGHLIGHT_TEXT_COLOR = DARK_BLUE
WORD_HIGHLIGHT_BG_COLOR = CYAN

THEME = {
    'BACKGROUND': DARK_BLUE,
    'TEXT': LIGHT_GREY,
    'INPUT': DARKER_BLUE,
    'TEXT_INPUT': BLUE,
    'SCROLL': WHITE,
    'BUTTON': (CYAN, DARKER_PURPLE2),
    'PROGRESS': sg.DEFAULT_PROGRESS_BAR_COLOR,
    'BORDER': BORDER_SIZE,
    'SLIDER_DEPTH': 0,
    'PROGRESS_DEPTH': 0
}


def config_theme():
    """ Set the theme to my own theme. """
    sg.LOOK_AND_FEEL_TABLE[SELECTED_THEME] = THEME
    sg.theme(SELECTED_THEME)
    sg.SetOptions(input_text_color=INPUT_COLOR, font=FONT)


def get_theme_field(field):
    """
    Return the value of a theme field.
    :param field: The field to return
    :return: The field value if it exists, else None
    """
    return THEME.get(field)
