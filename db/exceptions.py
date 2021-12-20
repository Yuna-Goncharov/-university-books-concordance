from sqlite3 import IntegrityError


class NonUniqueError(IntegrityError):
    def __init__(self, *args, **kwargs):
        pass


class CheckError(IntegrityError):
    def __init__(self, *args, **kwargs):
        pass


def raise_specific_exception(exception):
    msg = str(exception)

    if msg.startswith("UNIQUE constraint failed"):
        raise NonUniqueError
    if msg.startswith("CHECK constraint failed"):
        raise CheckError

    raise exception
