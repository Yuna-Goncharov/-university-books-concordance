def build_query(cols=None, tables=None, group_by=None, order_by=None, **kwargs):

    assert len(tables)

    cols_str = ", ".join(cols) if cols else "*"
    query = f'SELECT {cols_str} FROM '
    query += ' NATURAL JOIN '.join(f'({table})' if ' ' in table else table for table in tables)

    # Apply all filters in the kwargs dict
    constraints = []
    for col_name, value in kwargs.items():
        if value not in (None, ''):
            if isinstance(value, str):
                constraints.append(f'{col_name} LIKE "{value}"')
            else:
                constraints.append(f'{col_name} == {value}')

    if constraints:
        query += ' WHERE ' + ' AND '.join(constraints)

    if group_by:
        query += ' GROUP BY ' + group_by

    if order_by:
        query += ' ORDER BY ' + order_by

    return query
