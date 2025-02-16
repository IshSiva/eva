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
import unittest
from test.markers import forecast_skip_marker
from test.util import get_evadb_for_testing, shutdown_ray

import pytest

from evadb.configuration.constants import EvaDB_ROOT_DIR
from evadb.server.command_handler import execute_query_fetch_all


@pytest.mark.notparallel
class ModelTrainTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.evadb = get_evadb_for_testing()
        # reset the catalog manager before running each test
        cls.evadb.catalog().reset()

        create_table_query = """
            CREATE TABLE AirData (\
            unique_id TEXT(30),\
            ds TEXT(30),\
            y INTEGER);"""
        execute_query_fetch_all(cls.evadb, create_table_query)

        path = f"{EvaDB_ROOT_DIR}/data/forecasting/air-passengers.csv"
        load_query = f"LOAD CSV '{path}' INTO AirData;"
        execute_query_fetch_all(cls.evadb, load_query)

    @classmethod
    def tearDownClass(cls):
        shutdown_ray()

        # clean up
        execute_query_fetch_all(cls.evadb, "DROP TABLE IF EXISTS HomeRentals;")

    @forecast_skip_marker
    def test_forecast(self):
        create_predict_udf = """
            CREATE FUNCTION Forecast FROM
            (SELECT unique_id, ds, y FROM AirData)
            TYPE Forecasting
            PREDICT 'y';
        """
        execute_query_fetch_all(self.evadb, create_predict_udf)

        predict_query = """
            SELECT Forecast(12) FROM AirData;
        """
        result = execute_query_fetch_all(self.evadb, predict_query)
        self.assertEqual(int(list(result.frames.iloc[:, -1])[-1]), 459)


if __name__ == "__main__":
    unittest.main()
