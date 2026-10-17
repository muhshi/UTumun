import os
from unittest.mock import patch
import pytest
import tuton.config as config
from tuton.db import get_db, Database
from tuton.mysql_db import MySQLDatabase


def test_get_db_sqlite_default():
    with patch.object(config, "DB_ENGINE", "sqlite"):
        db = get_db()
        assert isinstance(db, Database)
        assert hasattr(db, "update_submission")
        assert callable(db.update_submission)


def test_get_db_mysql_selection():
    with patch.object(config, "DB_ENGINE", "mysql"):
        db = get_db()
        assert isinstance(db, MySQLDatabase)
        assert hasattr(db, "update_submission")
        assert callable(db.update_submission)
        assert db.host == config.MYSQL_HOST
        assert db.user == config.MYSQL_USER
        assert db.database == config.MYSQL_DATABASE
        assert db.password == config.MYSQL_PASSWORD
