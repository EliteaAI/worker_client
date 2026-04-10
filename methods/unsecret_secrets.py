#!/usr/bin/python3
# coding=utf-8

#   Copyright 2024 EPAM Systems
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

""" Method """

from pylon.core.tools import log  # pylint: disable=E0611,E0401,W0611
from pylon.core.tools import web  # pylint: disable=E0611,E0401,W0611


class Method:  # pylint: disable=E1101,R0903,W0201
    """
        Method Resource

        self is pointing to current Module instance

        web.method decorator takes zero or one argument: method name
        Note: web.method decorator must be the last decorator (at top)
    """

    @web.method()
    def unsecret_data(self, secret_data, project_id=None):
        """ Unsecret data """
        data = secret_data
        #
        try:
            data = data.get_secret_value()
        except AttributeError:
            pass
        #
        try:
            data = data.unsecret(project_id)
        except AttributeError:
            pass
        #
        try:
            from tools import SecretString  # pylint: disable=E0401,C0415
            data = SecretString(data).unsecret(project_id)
        except:  # pylint: disable=W0702
            pass
        #
        try:
            from tools import VaultClient  # pylint: disable=E0401,C0415
            data = VaultClient(project_id).unsecret(data)
        except:  # pylint: disable=W0702
            pass
        #
        return data
