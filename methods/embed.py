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
    def embed_documents(  # pylint: disable=R0913
            self, integration_name, settings, texts,
        ):
        """ Make embeddings """
        use_legacy_llm_mode = self.descriptor.config.get("use_legacy_llm_mode", False)
        llm_interface_callback = self.llm_interface["embed_documents_callback"]
        #
        if integration_name not in self.llm_interface["supported_integrations"]:
            use_legacy_llm_mode = True
        #
        # Integration
        #
        if use_legacy_llm_mode or llm_interface_callback is None:
            if integration_name not in self.integrations:
                raise RuntimeError("Unknown integration")
            #
            callback = self.integrations[integration_name]["embed_documents_callback"]
            #
            if callback is None:
                raise RuntimeError("Action is not supported")
            #
            invoke_kwargs = {
                "routing_key": None,
            }
            #
            invoke_kwargs.update(callback(settings, texts))
            #
            task_id = self.task_node.start_task(
                name="invoke_model",
                kwargs=invoke_kwargs,
                pool="indexer",
            )
            #
            return self.task_node.join_task(task_id)
        #
        # LLM interface
        #
        # if llm_interface_callback is None:
        #     raise RuntimeError("LLM action is not supported")
        #
        return llm_interface_callback(integration_name, settings, texts)

    @web.method()
    def embed_query(  # pylint: disable=R0913
            self, integration_name, settings, text,
        ):
        """ Make embedding """
        use_legacy_llm_mode = self.descriptor.config.get("use_legacy_llm_mode", False)
        llm_interface_callback = self.llm_interface["embed_query_callback"]
        #
        if integration_name not in self.llm_interface["supported_integrations"]:
            use_legacy_llm_mode = True
        #
        # Integration
        #
        if use_legacy_llm_mode or llm_interface_callback is None:
            if integration_name not in self.integrations:
                raise RuntimeError("Unknown integration")
            #
            callback = self.integrations[integration_name]["embed_query_callback"]
            #
            if callback is None:
                raise RuntimeError("Action is not supported")
            #
            invoke_kwargs = {
                "routing_key": None,
            }
            #
            invoke_kwargs.update(callback(settings, text))
            #
            task_id = self.task_node.start_task(
                name="invoke_model",
                kwargs=invoke_kwargs,
                pool="indexer",
            )
            #
            return self.task_node.join_task(task_id)
        #
        # LLM interface
        #
        # if llm_interface_callback is None:
        #     raise RuntimeError("LLM action is not supported")
        #
        return llm_interface_callback(integration_name, settings, text)
