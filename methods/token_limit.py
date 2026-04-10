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
    def limit_tokens(  # pylint: disable=R0913
            self,
            data,
            token_limit=None,
            max_tokens=None,
        ):
        """ Limit data tokens """
        #
        # input_tokens + max_new_tokens > token_limit:
        # - system message - always keep / check first, error on too big
        # - non-system: remove pairs (human/ai) until in limit
        # - check user input - how to return warnings / errors?
        #
        if not isinstance(data, list):
            log.debug("Not supported data type: %s", type(data))
            #
            return data  # FIXME: truncate text data too?
        #
        if token_limit is None:
            log.debug("Token limit not provided")
            #
            return data
        #
        if max_tokens is None:
            max_new_tokens = 0  # FIXME: just check input tokens?
        else:
            max_new_tokens = max_tokens
        #
        input_tokens = self.limit_count_tokens(data)
        #
        log.debug(f"[Original] Tokens: {input_tokens=}, {max_new_tokens=}, {token_limit=}")
        #
        if input_tokens + max_new_tokens <= token_limit:
            return data
        #
        while True:
            data, removed = self.limit_remove_non_system_messages(data, 2)
            #
            if removed == 0:  # FIXME: raise some error?
                break
            #
            input_tokens = self.limit_count_tokens(data)
            #
            if input_tokens + max_new_tokens <= token_limit:
                break
        #
        log.debug(f"[Limited] Tokens: {input_tokens=}, {max_new_tokens=}, {token_limit=}")
        #
        return data

    @web.method()
    def limit_count_tokens(  # pylint: disable=R0913
            self, data,
        ):
        """ Count data tokens """
        import tiktoken  # pylint: disable=E0401,C0415
        encoding = tiktoken.get_encoding("cl100k_base")
        #
        result = 0
        #
        if isinstance(data, list):
            for item in data:
                result += len(encoding.encode(item["content"]))
        else:
            result += len(encoding.encode(data))
        #
        return result

    @web.method()
    def limit_remove_non_system_messages(  # pylint: disable=R0913
            self, data, count,
        ):
        """ Remove messages """
        result = []
        removed = 0
        #
        for item in data:
            if item["role"] == "system":
                result.append(item)
                continue
            #
            if removed == count:
                result.append(item)
                continue
            #
            removed += 1
        #
        return result, removed
