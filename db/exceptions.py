from sqlite3 import IntegrityError


class NonUniqueError(IntegrityError):
    def __init__(self, *args, **kwargs):
        pass


class CheckError(IntegrityError):
    def __init__(self, *args, **kwargs):
        pass


def raise_specific_exception(exception):
    """
    Try to raise a more specific exception.
    :param exception: An IntegrityError exception
    :raise: NonUniqueError: If the exception is due to UNIQUE constraint
    :raise: CheckError: If the exception is due to CHECK constraint
    :raise: IntegrityError: Otherwise
    """
    msg = str(exception)

    if msg.startswith("UNIQUE constraint failed"):
        raise NonUniqueError
    if msg.startswith("CHECK constraint failed"):
        raise CheckError

    raise exception
