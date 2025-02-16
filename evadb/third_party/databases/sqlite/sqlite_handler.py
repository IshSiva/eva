# coding=utf-8
# Copyright 2018-2023 EvaDB
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import sqlite3

import pandas as pd

from evadb.third_party.databases.types import (
    DBHandler,
    DBHandlerResponse,
    DBHandlerStatus,
)


class SQLiteHandler(DBHandler):
    def __init__(self, name: str, **kwargs):
        """
        Initialize the handler.
        Args:
            name (str): name of the DB handler instance
            **kwargs: arbitrary keyword arguments for establishing the connection.
        """
        super().__init__(name)
        self.database = kwargs.get("database")
        self.connection = None

    def connect(self):
        """
        Set up the connection required by the handler.
        Returns:
            DBHandlerStatus
        """
        try:
            self.connection = sqlite3.connect(
                database=self.database, isolation_level=None  # Autocommit mode.
            )
            return DBHandlerStatus(status=True)
        except sqlite3.Error as e:
            return DBHandlerStatus(status=False, error=str(e))

    def disconnect(self):
        """
        Close any existing connections.
        """
        if self.connection:
            self.connection.close()

    def check_connection(self) -> DBHandlerStatus:
        """
        Check connection to the handler.
        Returns:
            DBHandlerStatus
        """
        if self.connection:
            return DBHandlerStatus(status=True)
        else:
            return DBHandlerStatus(status=False, error="Not connected to the database.")

    def get_tables(self) -> DBHandlerResponse:
        """
        Return the list of tables in the database.
        Returns:
            DBHandlerResponse
        """
        if not self.connection:
            return DBHandlerResponse(data=None, error="Not connected to the database.")

        try:
            query = "SELECT name AS table_name FROM sqlite_master WHERE type = 'table'"
            tables_df = pd.read_sql_query(query, self.connection)
            return DBHandlerResponse(data=tables_df)
        except sqlite3.Error as e:
            return DBHandlerResponse(data=None, error=str(e))

    def get_columns(self, table_name: str) -> DBHandlerResponse:
        """
        Returns the list of columns for the given table.
        Args:
            table_name (str): name of the table whose columns are to be retrieved.
        Returns:
            DBHandlerResponse
        """
        if not self.connection:
            return DBHandlerResponse(data=None, error="Not connected to the database.")
        """
        SQLite does not provide an in-built way to get the column names using a SELECT statement.
        Hence we have to use the PRAGMA command and filter the required columns.
        """
        try:
            query = f"PRAGMA table_info('{table_name}')"
            pragma_df = pd.read_sql_query(query, self.connection)
            columns_df = pragma_df[["name", "type"]].copy()
            columns_df.rename(columns={"type": "dtype"}, inplace=True)
            return DBHandlerResponse(data=columns_df)
        except sqlite3.Error as e:
            return DBHandlerResponse(data=None, error=str(e))

    def _fetch_results_as_df(self, cursor):
        try:
            res = cursor.fetchall()
            res_df = pd.DataFrame(
                res,
                columns=[desc[0] for desc in cursor.description]
                if cursor.description
                else [],
            )
            return res_df
        except sqlite3.ProgrammingError as e:
            if str(e) == "no results to fetch":
                return pd.DataFrame({"status": ["success"]})
            raise e

    def execute_native_query(self, query_string: str) -> DBHandlerResponse:
        """
        Executes the native query on the database.
        Args:
            query_string (str): query in native format
        Returns:
            DBHandlerResponse
        """
        if not self.connection:
            return DBHandlerResponse(data=None, error="Not connected to the database.")
        try:
            cursor = self.connection.cursor()
            cursor.execute(query_string)
            return DBHandlerResponse(data=self._fetch_results_as_df(cursor))
        except sqlite3.Error as e:
            return DBHandlerResponse(data=None, error=str(e))
