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

    @web.init()
    def init_registrations(self):
        """ Create integration registry """
        self.integrations = {}
        self.llm_interface = {}
        #
        self.register_llm_interface()  # add None values

    @web.method()
    def register_integration(  # pylint: disable=R0913
            self, integration_name, *,
            #
            ai_check_settings_callback=None,
            ai_get_models_callback=None,
            ai_count_tokens_callback=None,
            #
            llm_invoke_callback=None,
            llm_stream_callback=None,
            #
            chat_model_invoke_callback=None,
            chat_model_stream_callback=None,
            #
            embed_documents_callback=None,
            embed_query_callback=None,
            #
            indexer_config_callback=None,
        ):
        """ Register integration callbacks """
        self.integrations[integration_name] = {
            "ai_check_settings_callback": ai_check_settings_callback,
            "ai_get_models_callback": ai_get_models_callback,
            "ai_count_tokens_callback": ai_count_tokens_callback,
            #
            "llm_invoke_callback": llm_invoke_callback,
            "llm_stream_callback": llm_stream_callback,
            #
            "chat_model_invoke_callback": chat_model_invoke_callback,
            "chat_model_stream_callback": chat_model_stream_callback,
            #
            "embed_documents_callback": embed_documents_callback,
            "embed_query_callback": embed_query_callback,
            #
            "indexer_config_callback": indexer_config_callback,
        }

    @web.method()
    def register_llm_interface(  # pylint: disable=R0913
            self, *,
            #
            ai_check_settings_callback=None,
            ai_get_models_callback=None,
            ai_count_tokens_callback=None,
            #
            llm_invoke_callback=None,
            llm_stream_callback=None,
            #
            chat_model_invoke_callback=None,
            chat_model_stream_callback=None,
            #
            embed_documents_callback=None,
            embed_query_callback=None,
            #
            indexer_config_callback=None,
            #
            supported_integrations=None,
        ):
        """ Register LLM interface callbacks """
        if supported_integrations is None:
            supported_integrations = []
        #
        self.llm_interface = {
            "ai_check_settings_callback": ai_check_settings_callback,
            "ai_get_models_callback": ai_get_models_callback,
            "ai_count_tokens_callback": ai_count_tokens_callback,
            #
            "llm_invoke_callback": llm_invoke_callback,
            "llm_stream_callback": llm_stream_callback,
            #
            "chat_model_invoke_callback": chat_model_invoke_callback,
            "chat_model_stream_callback": chat_model_stream_callback,
            #
            "embed_documents_callback": embed_documents_callback,
            "embed_query_callback": embed_query_callback,
            #
            "indexer_config_callback": indexer_config_callback,
            #
            "supported_integrations": supported_integrations,
        }
