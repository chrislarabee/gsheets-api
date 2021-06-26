from autodrive.tab import Tab
from autodrive.interfaces import Color, TextFormat


class TestTabFormatting:
    def test_formatting_applications(self, test_gsheet, sheets_conn):
        tab = Tab(
            test_gsheet.gsheet_id,
            tab_title="tab_format",
            tab_id=11,
            tab_idx=3,
            column_count=10,
            row_count=500,
            sheets_conn=sheets_conn,
        )
        tab.create()
        tab.format_cell.add_alternating_row_background(Color(1.0, 0.5))
        tab.format_text.apply_format(TextFormat(font_size=14, bold=True))
        tab.commit()
        tab.get_data()
        cell1 = tab.formats[0][0]
        assert cell1["backgroundColor"]["red"] == 1
        assert cell1["backgroundColor"]["green"] == 0.49803922
        assert cell1["textFormat"]["bold"]
        assert cell1["textFormat"]["fontSize"] == 14
