from __future__ import annotations

from typing import Any, List

from .connection import SheetsConnection
from ._view import Component
from .formatting.format_rng import (
    RangeCellFormatting,
    RangeGridFormatting,
    RangeTextFormatting,
)
from .interfaces import AuthConfig, TwoDRange


class Range(Component[RangeCellFormatting, RangeGridFormatting, RangeTextFormatting]):
    """
    Provides a connection to the data in a specific range in a Google Sheet Tab.
    """

    def __init__(
        self,
        gsheet_range: TwoDRange,
        gsheet_id: str,
        tab_title: str,
        *,
        auth_config: AuthConfig | None = None,
        sheets_conn: SheetsConnection | None = None,
        autoconnect: bool = True,
    ) -> None:
        """

        Args:
            gsheet_range (TwoDRange): The range (i.e. A5:C10) to associate with
                this Range.
            gsheet_id (str): The id string of the target Google Sheet that the
                Range resides in; can be found in the Google Sheet url.
            tab_title (str): The name of the Tab this Range is within.
            auth_config (AuthConfig, optional): Optional custom AuthConfig,
                defaults to None.
            sheets_conn (SheetsConnection, optional): Optional manually created
                SheetsConnection, defaults to None.
            autoconnect (bool, optional): If you want to instantiate a Range
                without immediately checking your authentication credentials and
                connection to the Google Sheets api, set this to False, defaults
                to True.
        """
        self._tab_title = tab_title
        gsheet_range.tab_title = tab_title
        self._rng = gsheet_range
        super().__init__(
            gsheet_id=gsheet_id,
            gsheet_range=gsheet_range,
            grid_formatting=RangeGridFormatting,
            text_formatting=RangeTextFormatting,
            cell_formatting=RangeCellFormatting,
            auth_config=auth_config,
            sheets_conn=sheets_conn,
            autoconnect=autoconnect,
        )

    @property
    def format_grid(self) -> RangeGridFormatting:
        """
        Returns:
          RangeGridFormatting: An object with grid formatting methods.

        """
        return self._format_grid

    @property
    def format_text(self) -> RangeTextFormatting:
        """
        Returns:
          RangeTextFormatting: An object with text formatting methods.

        """
        return self._format_text

    @property
    def format_cell(self) -> RangeCellFormatting:
        """
        Returns:
          RangeCellFormatting: An object with cell formatting methods.

        """
        return self._format_cell

    def get_data(self) -> Range:
        """
        Gets the data from the cells of this Range.

        Returns:
          Range: This Range.

        """
        self._values, self._formats = self._get_data(self._gsheet_id, str(self._rng))
        return self

    def write_values(self, data: List[List[Any]]) -> Range:
        """
        Adds a request to write data. Range.commit () to commit the requests.

        Args:
          data (List[List[Any]]): The data to write. Each list in the passed data
            list is a row, with each value in that sublist being a column.

        Returns:
          Range: This Tab.

        """
        self._write_values(data, self._rng.to_dict())
        return self
