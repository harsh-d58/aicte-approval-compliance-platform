from io import BytesIO
import json
from unittest import TestCase
from xml.etree import ElementTree
from zipfile import ZipFile

from backend.app.report_catalog import snapshot_digest, validate_rows
from backend.app.report_exports import export_report


class ReportExportTests(TestCase):
    def test_csv_neutralizes_formulas_and_preserves_quote_newline_values(self):
        body, mime = export_report([{"Name": '=HYPERLINK("bad")', "Notes": 'a,"b"\nc'}], ["Name", "Notes"], {"report_code": "test"}, "csv")
        self.assertEqual(mime, "text/csv")
        self.assertIn("'=HYPERLINK", body.decode("utf-8-sig"))
        self.assertIn('"a,""b""\nc"', body.decode("utf-8-sig"))

    def test_xlsx_is_a_valid_zip_with_typed_text_not_formulas(self):
        body, mime = export_report([{"Name": "=1+1"}], ["Name"], {"row_count": 1}, "xlsx")
        with ZipFile(BytesIO(body)) as archive:
            self.assertIsNotNone(ElementTree.fromstring(archive.read("xl/workbook.xml")))
            sheet = archive.read("xl/worksheets/sheet1.xml")
            self.assertIn(b"=1+1", sheet)
            self.assertNotIn(b"<f>", sheet)
            self.assertIn("xl/worksheets/sheet2.xml", archive.namelist())

    def test_json_includes_the_frozen_manifest(self):
        body, _ = export_report([], ["Name"], {"sha256": "abc"}, "json")
        self.assertEqual(json.loads(body)["manifest"]["sha256"], "abc")

    def test_manifest_hash_changes_if_data_or_period_changes(self):
        args = {"columns": ["Name"], "period": {"from": "2026-01-01"}, "code": "application-pendency"}
        self.assertNotEqual(snapshot_digest([{"Name": "one"}], **args), snapshot_digest([{"Name": "two"}], **args))

    def test_unknown_or_missing_report_columns_cannot_publish(self):
        with self.assertRaises(ValueError):
            validate_rows("document-validity", [{"wrong": "value"}])
