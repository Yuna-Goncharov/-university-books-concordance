import os
import sqlite3

from db.exceptions import raise_specific_exception
from utils.utils import cached_read


def raise_specific_exception_wrapper(func):
    """
    Decorator that catch sqlite3 errors and tries to raise a more specific exception instead.
    :param func: The func to decorate
    :return: The decorated function
    """

    def _inner(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except sqlite3.Error as error:
            raise_specific_exception(error)

    return _inner


class Database:
    """
    Database manager class.
    It handles the whole connections.
    Can be used as a context manager as well.
    """

    # The directory with the script files
    SCRIPTS_DIR = r"scripts"

    def __init__(self, db_path=None, always_create=False):
        self._curr_path = None
        self._conn = None  # type: sqlite3.Connection
        self._cursor = None  # type: sqlite3.Cursor
        self.new_connection(always_create, db_path)

    def save_to_file(self, db_path, switch_to_new=False):
        """
        Dump the current db to disk
        :param db_path: Path to save the db at
        :param switch_to_new: If true, the current connection will be switched to the saved file
        """

        # If we already use db_path there's nothing to be done
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
        """
        Switch to a new connection.
        :param always_create: Override existing db at path
        :param new_path: The path to connect to. Keep as None for in memory db.
        :param commit: Should the current connection be committed before close
        :return: If new connection is to an already existing db
        """

        # Close the current connection
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

        # Return if a new db was created
        return already_exists and not always_create

    @raise_specific_exception_wrapper
    def execute(self, *args, **kwargs):
        """ Execute a SQL statement. """
        if len(args) == 3:
            raise ValueError

        return self._cursor.execute(*args, **kwargs)

    @raise_specific_exception_wrapper
    def executemany(self, *args, **kwargs):
        """ Repeatedly execute a SQL statement. """
        return self._cursor.executemany(*args, **kwargs)

    @raise_specific_exception_wrapper
    def executescript(self, *args, **kwargs):
        """ Execute multiple SQL statements at once. """
        return self._cursor.executescript(*args, **kwargs)

    @staticmethod
    def _read_script_file(script_name):
        """
        Read the content of a script file from the scripts directory.
        :param script_name: The name of the script
        :return: The script
        """
        return cached_read(os.path.join(Database.SCRIPTS_DIR, script_name + '.sql'))

    def _run_sql_script(self, script_name, args=(), multiple_statements=False):
        """
        Run a script from the scripts directory.
        :param script_name: The name of the script
        :param args: The args to the script
        :param multiple_statements: Does the file contains multiple statements
        """
        script = Database._read_script_file(script_name)
        if multiple_statements:
            return self.executescript(script)
        else:
            return self.execute(script, args)

    def commit(self):
        """ Commit the current connection. """
        self._conn.commit()

    def close(self, commit=True):
        """
        Close the current connection.
        :param commit: Should the connection be committed before closing
        """
        if commit:
            self.commit()

        if self._cursor:
            self._cursor.close()

        if self._conn:
            self._conn.close()

    def __enter__(self):
        """
        On enter, do nothing.
        :return: The database object
        """
        return self

    def __exit__(self, _exc_type, _exc_val, _exc_tb):
        """ On exit, close the database. """
        self.close()
