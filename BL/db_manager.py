import os
import sqlite3

from BL.exceptions import raise_specific_exception
from Helpers.utils import cached_read


def raise_specific_exception_wrapper(func):

    def _inner(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except sqlite3.Error as error:
            raise_specific_exception(error)

    return _inner


class Database:

    SCRIPTS_DIR = r"scripts"

    def __init__(self, db_path=None, always_create=False):
        self._curr_path = None
        self._conn = None  # type: sqlite3.Connection
        self._cursor = None  # type: sqlite3.Cursor
        self.new_connection(always_create, db_path)

    def save_to_file(self, db_path, switch_to_new=False):

        if db_path == self._curr_path:
            return

        disk_conn = sqlite3.connect(db_path)
        self.commit()
        self._conn.backup(disk_conn)

        if switch_to_new:
            self.close(commit=False)
            self._conn = disk_conn
            self._cursor = self._conn.cursor()

    def new_connection(self, always_create=True, new_path=None, commit=True):

        if self._conn:
            self.close(commit=commit)

        if new_path:
            # Check if the path already exists
            already_exists = os.path.exists(new_path)

            # Delete if always_create
            if always_create and already_exists:
                os.remove(new_path)
        else:
            already_exists = False

        # Connect to the new path
        self._conn = sqlite3.connect(new_path if new_path else ':memory:')
        self._cursor = self._conn.cursor()
        self._curr_path = new_path

        return already_exists and not always_create

    @raise_specific_exception_wrapper
    def execute(self, *args, **kwargs):

        if len(args) == 3:
            raise ValueError

        return self._cursor.execute(*args, **kwargs)

    @raise_specific_exception_wrapper
    def executemany(self, *args, **kwargs):
        return self._cursor.executemany(*args, **kwargs)

    @raise_specific_exception_wrapper
    def executescript(self, *args, **kwargs):
        return self._cursor.executescript(*args, **kwargs)

    @staticmethod
    def _read_script_file(script_name):
        return cached_read(os.path.join(Database.SCRIPTS_DIR, script_name + '.sql'))

    def _run_sql_script(self, script_name, args=(), multiple_statements=False):
        script = Database._read_script_file(script_name)
        if multiple_statements:
            return self.executescript(script)
        else:
            return self.execute(script, args)

    def commit(self):
        self._conn.commit()

    def close(self, commit=True):
        if commit:
            self.commit()

        if self._cursor:
            self._cursor.close()

        if self._conn:
            self._conn.close()

    def __enter__(self):
        return self

    def __exit__(self, _exc_type, _exc_val, _exc_tb):
        self.close()
