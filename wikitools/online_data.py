from wikitools import console
import os
import typing
import sys

try:
    from googleapiclient.discovery import build # type: ignore
    from googleapiclient.errors import HttpError # type: ignore
    GOOGLE_CLIENT_IMPORTED = True
except ImportError as error:
    GOOGLE_CLIENT_IMPORTED = False
    GOOGLE_CLIENT_IMPORT_ERROR = error


API_KEY_ENV = "GOOGLE_SHEETS_API_KEY"
try:
    API_KEY = os.environ[API_KEY_ENV]
except KeyError:
    API_KEY = ""

def list_table_to_dict_table(table: typing.List[typing.List[str]]) -> typing.List[typing.Dict[str, str]]:
    header = table[0]
    new_table = []
    for row in table[1:]:
        new_table.append({ header: value for header, value in zip(header, row) })
    return new_table


def get_spreadsheet_range_unchecked(spreadsheet_id: str, range_name: str) -> typing.List[typing.Dict[str, str]]:
    """
    Retrieves a range of cell values from a Google Sheet.

    Raises HttpError when either authentication or retrieval fails.
    """

    service = build("sheets", "v4", developerKey=API_KEY)

    result = (
        service.spreadsheets()
        .values()
        .get(spreadsheetId=spreadsheet_id, range=range_name)
        .execute()
    )

    rows = result.get("values", [])
    column_count = len(rows[0])

    rows = [row + [""] * (column_count - len(row)) for row in rows]
    return list_table_to_dict_table(rows)


def get_spreadsheet_range(spreadsheet_id, range_name):
    """
    Retrieves a range of cell values from a Google Sheet.

    Exits on failure with error messages.
    """

    if not API_KEY:
        print(f"{console.red('Error:')} Spreadsheet retrieval requires an api key set to the {API_KEY_ENV} environment variable.\n")
        print("See https://support.google.com/googleapi/answer/6158862?hl=en")
        print("and https://console.cloud.google.com/apis/api/sheets.googleapis.com/overview\n")
    if not GOOGLE_CLIENT_IMPORTED:
        print(f"{console.red('Error:')} {GOOGLE_CLIENT_IMPORT_ERROR}. Spreadsheet retrieval requires an optional dependency:\n")
        print("pip install google-api-python-client\n")
    if not API_KEY or not GOOGLE_CLIENT_IMPORTED:
        print("Alternatively, use the --csv-file option (see --help).")
        sys.exit(1)

    try:
        csv = get_spreadsheet_range_unchecked(spreadsheet_id, range_name)
    except HttpError as error:
        print(f"{console.red('Error:')} Spreadsheet retrieval failed: {error.status_code}. Make sure the {API_KEY_ENV} environment variable is correct.")
        sys.exit(1)
    except Exception as error:
        print(f"{console.red('Error:')} Spreadsheet retrieval failed: {error}")
        sys.exit(1)

    print(f"{len(csv)} rows retrieved from online spreadsheet")
    return csv
