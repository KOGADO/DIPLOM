def _table_has_column(schema_editor, table_name, column_name):
    introspection = schema_editor.connection.introspection
    existing_tables = introspection.table_names(schema_editor.connection.cursor())
    if table_name not in existing_tables:
        return False

    with schema_editor.connection.cursor() as cursor:
        description = introspection.get_table_description(cursor, table_name)

    existing_columns = set()
    for col in description:
        if hasattr(col, 'name'):
            existing_columns.add(col.name)
        elif isinstance(col, (list, tuple)) and col:
            existing_columns.add(col[0])

    return column_name in existing_columns


def add_column_if_missing(schema_editor, table_name, column_name, sql_type='INTEGER'):
    if _table_has_column(schema_editor, table_name, column_name):
        return False

    quoted_table = schema_editor.quote_name(table_name)
    quoted_column = schema_editor.quote_name(column_name)
    schema_editor.execute(f'ALTER TABLE {quoted_table} ADD COLUMN {quoted_column} {sql_type} NULL')
    return True
