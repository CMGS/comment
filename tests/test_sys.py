#!/usr/bin/python
#coding:utf-8

import json
import config
import falcon
from falcon import testing

from app import app
from tests.base import is_iter


class TestSys(testing.TestBase):

    def test_get(self):
        mock = testing.StartResponseMock()
        response = app(testing.create_environ(path='/sys'), mock)

        self.assertTrue(is_iter(response))
        self.assertEqual(falcon.HTTP_200, mock.status)

        data = json.loads(''.join(response))
        self.assertIsInstance(data, dict)
        self.assertEqual(data['store'], config.STORE)

