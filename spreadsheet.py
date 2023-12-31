"""Module that contains a class for handling googlesheets spreadsheets."""

import logging as log
from time import sleep

import gspread
from gspread.exceptions import APIError
from google.auth.exceptions import RefreshError
from requests.exceptions import ConnectionError
from oauth2client.service_account import ServiceAccountCredentials


# TODO apply PEP8 class naming convention
# TODO add annotations and docstrings to methods
class Spread:
    """Class that handles the connection, opening, reading and modification of
    any googlesheets spreadsheet.
    """

    def __init__(self, spreadSheet):
        scope = [
            'https://spreadsheets.google.com/feeds',
            'https://www.googleapis.com/auth/spreadsheets',
            'https://www.googleapis.com/auth/drive.file',
            'https://www.googleapis.com/auth/drive'
        ]

        # NOTE should add a try except in case "creds.json" is not
        # found?
        # Assign credentials and path of style sheet
        creds = ServiceAccountCredentials.from_json_keyfile_name('creds.json', scope)

        # NOTE should add a retry limit?
        while True:
            try:
                self.client = gspread.authorize(creds)

                break
            except (RefreshError, APIError, ConnectionError):
                log.info(
                    'Couldn\'t authorize credentials, retrying in 10 minutes'
                )

                sleep(600)

        # NOTE should add a exception catch in case of spreadSheet not
        # found?
        while True:
            try:
                self.sheet = self.client.open(spreadSheet)

                break
            except (APIError, ConnectionError) as error:
                log.info(
                    'Couldn\'t open googlesheet, retrying in 10 minutes'
                )
                log.debug('Error details: %s', str(error))

                sleep(600)

    def setSheet(self, worksheetName: str) -> None:
        """Selects a worksheet inside the stored google sheet with the given
        name.
        """

        try:
            self.worksheet = self.sheet.worksheet(worksheetName)
        except (APIError, ConnectionError) as error:
            log.info(
                'Couldn\'t to googlesheets, retrying in 10 minutes'
            )
            log.debug('Error details: %s', str(error))

            sleep(600)

            self.setSheet(worksheetName)

    def get_prop(self) -> tuple[int, int]:
        """Gets length of all cells in the first column and row."""

        try:
            row = self.get_row(1)
            col = self.get_col(1)
        except (APIError, ConnectionError) as error:
            log.info(
                'Couldn\'t to googlesheets, retrying in 10 minutes'
            )
            log.debug('Error details: %s', str(error))

            sleep(600)

            return self.get_prop()

        return len(col), len(row)

    def get_cell(self, row: int, col: int) -> str:
        """Get the value of a cell in the given row and column position
        (starting from 1).
        """

        try:
            cell = self.worksheet.cell(row, col).value
        except (APIError, ConnectionError):
            log.error(
                'Couldn\'t connect to googlesheets, retrying in 5 minutes'
            )

            sleep(300)

            cell = self.get_cell(row, col)

        return cell

    def set_cell(
            self, row: int, col: int, val: str) -> dict[str, str | int] | None:
        """Updates the cell in the given row and column position with the
        given value.
        """

        try:
            cell = self.worksheet.update_cell(row, col, val)
        except (APIError, ConnectionError) as err:
            if 'exceeds grid limits' in str(err):
                log.error(
                    'Grid limits exceeded, couldn\'t set the specified cell'
                )

                cell = None
            else:
                log.error(
                    'Couldn\'t connect to googlesheets, retrying in 5 minutes'
                )

                sleep(300)

                cell = self.set_cell(row, col, val)

        return cell

    def get_row(self, row: int) -> list[str]:
        """Gets all the values from the given row position starting from 1."""

        try:
            row_values = self.worksheet.row_values(row)
        except (APIError, ConnectionError):
            log.error(
                'Couldn\'t connect to googlesheets, retrying in 5 minutes'
            )

            sleep(300)

            row_values = self.get_row(row)

        return row_values

    def get_col(self, col: int) -> list[str]:
        """Gets all the values from the given column position starting from
        1.
        """

        try:
            col_values = self.worksheet.col_values(col)
        except (APIError, ConnectionError):
            log.error(
                'Couldn\'t connect to googlesheets, retrying in 5 minutes'
            )

            sleep(300)

            col_values = self.get_col(col)

        return col_values

    def get_all(self) -> list[list[str]]:
        """Gets all values inside a worksheet as a list of lists."""

        try:
            all_values = self.worksheet.get_all_values()
        except (APIError, ConnectionError):
            log.error(
                'Couldn\'t connect to googlesheets, retrying in 5 minutes'
            )

            sleep(300)

            all_values = self.get_all()

        return all_values

    def search_cell(self, text: str) -> tuple[int, int]:
        """Searches for a cell with the exact same value as 'text'."""

        try:
            cell = self.worksheet.find(text)
        except (APIError, ConnectionError):
            log.error(
                'Couldn\'t connect to googlesheets, retrying in 5 minutes'
            )

            sleep(300)

            cell = self.search_cell(text)

        return cell.row, cell.col

    def clear_grid(self, start: str, end: str) -> None:
        """Clear a given A1 notation cell range."""

        try:
            self.worksheet.batch_clear([f'{start}:{end}'])
        except (APIError, ConnectionError):
            log.info(
                'Couldn\'t to googlesheets, retrying in 5 minutes'
            )

            sleep(300)

            self.clear_grid(start, end)

    def set_grid(self, start: str, end: str, values: list[str]) -> None:
        """Apply values to a given A1 notation range."""

        try:
            self.worksheet.update(f'{start}:{end}', values)
        except (APIError, ConnectionError):
            log.info(
                'Couldn\'t to googlesheets, retrying in 5 minutes'
            )

            sleep(300)

            self.set_grid(start, end, values)
