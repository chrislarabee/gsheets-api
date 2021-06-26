from __future__ import annotations
from autodrive.interfaces import TwoDRange

from typing import Any, Dict, List, Type, TypeVar, Tuple, Generic
from abc import ABC
import string

from .connection import AuthConfig, SheetsConnection
from . import google_terms as terms
from .dtypes import (
    EffectiveFmt,
    GOOGLE_DTYPES,
    GoogleValueType,
    TYPE_MAP,
    UserEnteredVal,
    EffectiveVal,
    String,
    Formula,
)

T = TypeVar("T", bound="GSheetView")
FT = TypeVar("FT", bound="Formatting")


class NoConnectionError(Exception):
    def __init__(self, ctype: Type[GSheetView], *args: object) -> None:
        msg = f"No SheetsConnection has been established for this {ctype}."
        super().__init__(msg, *args)


class Formatting:
    def __init__(self, parent: Component):
        self._parent = parent


class GSheetView(ABC):
    def __init__(
        self,
        gsheet_id: str,
        *,
        auth_config: AuthConfig = None,
        sheets_conn: SheetsConnection = None,
        autoconnect: bool = True,
    ) -> None:
        super().__init__()
        if not sheets_conn and autoconnect:
            sheets_conn = SheetsConnection(auth_config=auth_config)
        self._conn = sheets_conn
        self._auth = auth_config
        self._gsheet_id = gsheet_id
        self._requests: List[Dict[str, Any]] = []

    @property
    def requests(self) -> List[Dict[str, Any]]:
        return self._requests

    @property
    def conn(self) -> SheetsConnection:
        if not self._conn:
            raise NoConnectionError(type(self))
        return self._conn

    @property
    def auth(self) -> AuthConfig:
        if not self._auth:
            raise NoConnectionError(type(self))
        return self._auth

    @property
    def gsheet_id(self) -> str:
        return self._gsheet_id

    def commit(self) -> Dict[str, Any]:
        if not self._conn:
            raise NoConnectionError(type(self))
        results = self._conn.execute_requests(self._gsheet_id, self._requests)
        self._requests = []
        return results

    @classmethod
    def _parse_row_data(
        cls,
        row_data: List[Dict[str, List[Dict[str, Any]]]],
        value_type: GoogleValueType = EffectiveVal,
    ) -> Tuple[List[List[Any]], List[List[Dict[str, Any]]]]:
        values = []
        formats = []
        for row in row_data:
            value_list = []
            fmt_list = []
            for cell in row.get(terms.VALUES, []):
                raw_value = cell.get(str(value_type))
                fmt = cell.get(str(EffectiveFmt))
                value = raw_value
                if value_type in (UserEnteredVal, EffectiveVal):
                    if raw_value:
                        for dtype in GOOGLE_DTYPES:
                            value = raw_value.get(str(dtype))
                            if value:
                                if value_type == UserEnteredVal:
                                    value = dtype.parse(value)
                                break
                value_list.append(value)
                fmt_list.append(fmt)
            values.append(value_list)
            formats.append(fmt_list)
        return values, formats

    def _get_data(
        self,
        gsheet_id: str,
        rng_str: str,
        value_type: GoogleValueType = EffectiveVal,
    ) -> Tuple[List[List[Any]], List[List[Dict[str, Any]]]]:
        raw = self.conn.get_data(gsheet_id, [rng_str])
        row_data = raw[terms.TABS_PROP][0][terms.DATA][0][terms.ROWDATA]
        return self._parse_row_data(row_data, value_type=value_type)

    def _write_values(self: T, data: List[List[Any]], rng_dict: Dict[str, int]) -> T:
        write_values = [
            [self._gen_cell_write_value(val) for val in row] for row in data
        ]
        request = {
            "updateCells": {
                terms.FIELDS: "*",
                terms.ROWS: [{terms.VALUES: values} for values in write_values],
                terms.RNG: rng_dict,
            }
        }
        self._requests.append(request)
        return self

    @staticmethod
    def _gen_cell_write_value(python_val: Any) -> Dict[str, Any]:
        type_ = type(python_val)
        if (
            isinstance(python_val, str)
            and len(python_val) >= 2
            and python_val[0] == "="
        ):
            dtype = Formula
        else:
            dtype = TYPE_MAP.get(type_, String)
        return {UserEnteredVal.value_key: {dtype.type_key: python_val}}

    # TODO: Delete this?
    @staticmethod
    def gen_alpha_keys(num: int) -> List[str]:
        """
        Generates a list of characters from the Latin alphabet a la gsheet/excel
        headers.

        Args:
            num (int): The desired length of the list.

        Returns:
            List[str]: A list containing as many letters and letter combos as
                desired. Can be used to generate sets up to 676 in length.
        """
        a = string.ascii_uppercase
        result = list()
        x = num // 26
        for i in range(x + 1):
            root = a[i - 1] if i > 0 else ""
            keys = [root + a[j] for j in range(26)]
            for k in keys:
                result.append(k) if len(result) < num else None
        return result


class Component(GSheetView, Generic[FT]):
    def __init__(
        self,
        *,
        gsheet_range: TwoDRange,
        gsheet_id: str,
        grid_formatting: Type[FT],
        text_formatting: Type[FT],
        cell_formatting: Type[FT],
        auth_config: AuthConfig = None,
        sheets_conn: SheetsConnection = None,
        autoconnect: bool = True,
    ) -> None:
        super().__init__(
            gsheet_id,
            auth_config=auth_config,
            sheets_conn=sheets_conn,
            autoconnect=autoconnect,
        )
        self._rng = gsheet_range
        self._values: List[List[Any]] = []
        self._formats: List[List[Dict[str, Any]]] = []
        self._format_grid = grid_formatting(self)
        self._format_text = text_formatting(self)
        self._format_cell = cell_formatting(self)

    @property
    def tab_id(self) -> int:
        return self._rng.tab_id

    @property
    def range_str(self) -> str:
        return str(self._rng)

    @property
    def range(self) -> TwoDRange:
        return self._rng

    @property
    def values(self) -> List[List[Any]]:
        return self._values

    @values.setter
    def values(self, new_values: List[List[Any]]) -> None:
        values_error = "new_values must be a list of lists."
        if not isinstance(new_values, list):
            raise TypeError(values_error)
        else:
            if len(new_values) > 0 and not isinstance(new_values[0], list):
                raise TypeError(values_error)
        self._values = new_values

    @property
    def formats(self) -> List[List[Dict[str, Any]]]:
        return self._formats

    @formats.setter
    def formats(self, new_formats: List[List[Dict[str, Any]]]) -> None:
        formats_error = "new_formats must be a list of lists of dictionaries."
        if not isinstance(new_formats, list):
            raise TypeError(formats_error)
        else:
            if len(new_formats) > 0 and not isinstance(new_formats[0], list):
                raise TypeError(formats_error)
        self._formats = new_formats

    @property
    def data_shape(self) -> Tuple[int, int]:
        width = len(self._values[0]) if self._values else 0
        return len(self._values), width
