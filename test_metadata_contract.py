import unittest
import os
from unittest.mock import patch

from backend.db import PAPER_COLUMNS, QUESTION_COLUMNS, _database_config, get_connection
from backend.upload_service import _required_metadata


class MetadataContractTests(unittest.TestCase):
    def test_upload_metadata_requires_semester_and_paper_code(self):
        metadata = _required_metadata(
            {
                "subject": "Data Structures",
                "academic_year": "Second Year",
                "semester": "Semester 3",
                "exam_year": "2025",
                "term": "End Term",
                "paper_code": "TCS302",
            }
        )

        self.assertEqual(metadata["semester"], "Semester 3")
        self.assertEqual(metadata["paper_code"], "TCS302")
        self.assertEqual(metadata["exam_year"], 2025)

    def test_paper_queries_expose_metadata_columns(self):
        self.assertIn("semester", PAPER_COLUMNS)
        self.assertIn("paper_code", PAPER_COLUMNS)
        self.assertIn("qp.semester AS paper_semester", QUESTION_COLUMNS)
        self.assertIn("qp.paper_code AS paper_code", QUESTION_COLUMNS)


class DatabaseSslConfigurationTests(unittest.TestCase):
    @patch.dict(os.environ, {"MYSQL_PASSWORD": "local-password"}, clear=True)
    def test_local_mysql_configuration_omits_ssl_options(self):
        config = _database_config()

        self.assertEqual(config["host"], "localhost")
        self.assertEqual(config["port"], 3306)
        self.assertNotIn("ssl_ca", config)
        self.assertNotIn("ssl_verify_cert", config)
        self.assertNotIn("ssl_verify_identity", config)

    @patch("backend.db.mysql.connector.connect")
    @patch.dict(
        os.environ,
        {
            "MYSQL_HOST": "gateway01.eu-central-1.prod.aws.tidbcloud.com",
            "MYSQL_PORT": "4000",
            "MYSQL_DATABASE": "smart_pyq_db",
            "MYSQL_USER": "app-user",
            "MYSQL_PASSWORD": "tidb-password",
            "MYSQL_SSL_CA": "/etc/secrets/tidb-ca.pem",
        },
        clear=True,
    )
    def test_tidb_configuration_enables_verified_ssl(self, connect):
        connect.return_value = object()

        get_connection()

        connect.assert_called_once_with(
            host="gateway01.eu-central-1.prod.aws.tidbcloud.com",
            port=4000,
            database="smart_pyq_db",
            user="app-user",
            password="tidb-password",
            connection_timeout=5,
            ssl_ca="/etc/secrets/tidb-ca.pem",
            ssl_verify_cert=True,
            ssl_verify_identity=True,
        )


if __name__ == "__main__":
    unittest.main()
