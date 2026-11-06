import os

import mysql.connector
from dotenv import load_dotenv


DATABASE = "paises_7A"
TABLE = "paises"


def quote_identifier(identifier):
    return "`" + identifier.replace("`", "``") + "`"


def get_connection_config():
    load_dotenv()
    user = os.getenv("MYSQL_USER")
    if not user:
        raise ValueError("Configura MYSQL_USER en el archivo .env.")

    return {
        "host": os.getenv("MYSQL_HOST", "localhost"),
        "port": int(os.getenv("MYSQL_PORT", "3306")),
        "user": user,
        "password": os.getenv("MYSQL_PASSWORD", ""),
        "database": DATABASE,
    }


def get_table_columns(cursor):
    cursor.execute(f"SHOW COLUMNS FROM {quote_identifier(TABLE)}")
    columns = cursor.fetchall()
    primary_keys = [column["Field"] for column in columns if column["Key"] == "PRI"]
    if not primary_keys:
        raise ValueError(
            f"La tabla {TABLE} necesita una clave primaria para editar o borrar registros."
        )
    if len(primary_keys) > 1:
        raise ValueError("Este CRUD requiere que la tabla tenga una sola columna como clave primaria.")
    return columns, primary_keys[0]


def ask_for_record_id(primary_key):
    return input(f"Ingresa el valor de {primary_key}: ").strip()


def list_records(cursor):
    cursor.execute(f"SELECT * FROM {quote_identifier(TABLE)}")
    rows = cursor.fetchall()
    if not rows:
        print("No hay países registrados.")
        return
    for row in rows:
        print(row)


def insert_record(cursor, columns):
    insert_columns = []
    values = []
    for column in columns:
        extra = column["Extra"].lower()
        if "auto_increment" in extra or "generated" in extra:
            continue

        name = column["Field"]
        if column["Default"] is not None:
            value = input(f"{name} (Enter para valor predeterminado): ")
            if value == "":
                continue
        elif column["Null"] == "YES":
            value = input(f"{name} (Enter para NULL): ")
            value = value if value else None
        else:
            value = input(f"{name}: ")
            while value == "":
                print("Este campo es obligatorio.")
                value = input(f"{name}: ")

        insert_columns.append(quote_identifier(name))
        values.append(value)

    if insert_columns:
        placeholders = ", ".join(["%s"] * len(values))
        names = ", ".join(insert_columns)
        query = f"INSERT INTO {quote_identifier(TABLE)} ({names}) VALUES ({placeholders})"
        cursor.execute(query, values)
    else:
        cursor.execute(f"INSERT INTO {quote_identifier(TABLE)} () VALUES ()")
    print(f"País agregado. ID: {cursor.lastrowid}")


def find_record(cursor, primary_key, record_id):
    query = (
        f"SELECT * FROM {quote_identifier(TABLE)} "
        f"WHERE {quote_identifier(primary_key)} = %s"
    )
    cursor.execute(query, (record_id,))
    return cursor.fetchone()


def update_record(cursor, columns, primary_key):
    record_id = ask_for_record_id(primary_key)
    record = find_record(cursor, primary_key, record_id)
    if record is None:
        print("No se encontró ese país.")
        return
    print("Registro actual:", record)

    editable = [
        column
        for column in columns
        if column["Field"] != primary_key
        and "generated" not in column["Extra"].lower()
    ]
    for index, column in enumerate(editable, start=1):
        print(f"{index}. {column['Field']}")
    try:
        choice = int(input("Número del campo que quieres cambiar: "))
        column = editable[choice - 1]
    except (ValueError, IndexError):
        print("Opción de campo no válida.")
        return

    value = input(f"Nuevo valor para {column['Field']}: ")
    if value == "" and column["Null"] == "YES":
        value = None
    elif value == "":
        print("El campo no puede quedar vacío.")
        return

    query = (
        f"UPDATE {quote_identifier(TABLE)} "
        f"SET {quote_identifier(column['Field'])} = %s "
        f"WHERE {quote_identifier(primary_key)} = %s"
    )
    cursor.execute(query, (value, record_id))
    print("País actualizado.")


def delete_record(cursor, primary_key):
    record_id = ask_for_record_id(primary_key)
    record = find_record(cursor, primary_key, record_id)
    if record is None:
        print("No se encontró ese país.")
        return
    print("Registro:", record)
    if input("¿Confirmas que quieres borrarlo? (s/N): ").strip().lower() != "s":
        print("Borrado cancelado.")
        return

    query = (
        f"DELETE FROM {quote_identifier(TABLE)} "
        f"WHERE {quote_identifier(primary_key)} = %s"
    )
    cursor.execute(query, (record_id,))
    print("País eliminado.")


def main():
    connection = None
    try:
        connection = mysql.connector.connect(**get_connection_config())
        cursor = connection.cursor(dictionary=True)
        columns, primary_key = get_table_columns(cursor)
        print(f"Conectado a {DATABASE}.{TABLE}; clave primaria: {primary_key}.")

        while True:
            print("\nCRUD de países")
            print("1. Listar países")
            print("2. Agregar país")
            print("3. Actualizar país")
            print("4. Eliminar país")
            print("5. Salir")
            option = input("Elige una opción: ").strip()

            if option == "1":
                list_records(cursor)
            elif option == "2":
                insert_record(cursor, columns)
                connection.commit()
            elif option == "3":
                update_record(cursor, columns, primary_key)
                connection.commit()
            elif option == "4":
                delete_record(cursor, primary_key)
                connection.commit()
            elif option == "5":
                break
            else:
                print("Opción no válida.")

        cursor.close()
    except (mysql.connector.Error, ValueError) as error:
        print(f"Error: {error}")
    finally:
        if connection is not None and connection.is_connected():
            connection.close()


if __name__ == "__main__":
    main()