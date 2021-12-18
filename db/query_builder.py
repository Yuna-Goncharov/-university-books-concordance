def build_query(cols=None, tables=None, group_by=None, order_by=None, **kwargs):
    """
    Dynamically create a simple SQL query from python.
    :param cols: Iterable of columns to select
    :param tables: Iterable of tables to select from
    :param group_by: String to be used for GROUP BY
    :param order_by: String to be used for ORDER BY
    :param kwargs: Filters to apply in the query
    :return: The built query
    """
    assert len(tables)

    # Create SELECT line
    cols_str = ", ".join(cols) if cols else "*"
    query = f'SELECT {cols_str} FROM '

    # Create FROM line
    # Automatically add bracelets around strings with space inside them. Useful for nested queries.
    query += ' NATURAL JOIN '.join(f'({table})' if ' ' in table else table for table in tables)

    # Apply all filters in the kwargs dict
    constraints = []
    for col_name, value in kwargs.items():
        # Empty filters don't need to be applied
        if value not in (None, ''):
            # Use "LIKE" for strings, and "==" otherwise
            if isinstance(value, str):
                constraints.append(f'{col_name} LIKE "{value}"')
            else:
                constraints.append(f'{col_name} == {value}')

    # Create WHERE line if there are constraints
    if constraints:
        query += ' WHERE ' + ' AND '.join(constraints)

    # Create GROUP BY line if needed
    if group_by:
        query += ' GROUP BY ' + group_by

    # Create ORDER BY line if needed
    if order_by:
        query += ' ORDER BY ' + order_by

    return query
