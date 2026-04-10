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

import uuid
import queue

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
    def init_streams(self):
        """ Create streams registry """
        self.streams = {}

    @web.method()
    def add_stream(self):
        """ Create stream ID """
        while True:
            stream_id = str(uuid.uuid4())
            if stream_id not in self.streams:
                break
        #
        self.streams[stream_id] = queue.Queue()
        #
        return stream_id

    @web.method()
    def remove_stream(self, stream_id):
        """ Forget stream by ID """
        self.streams.pop(stream_id, None)

    @web.method()
    def on_stream_event(self, _, payload):
        """ Process stream event """
        event = payload.copy()
        #
        stream_id = event.pop("stream_id", None)
        #
        if stream_id not in self.streams:
            return
        #
        self.streams[stream_id].put(event)

    @web.method()
    def llm_stream(  # pylint: disable=R0913
            self, integration_name, settings, text,
        ):
        """ Stream model """
        use_legacy_llm_mode = self.descriptor.config.get("use_legacy_llm_mode", False)
        llm_interface_callback = self.llm_interface["llm_stream_callback"]
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
            callback = self.integrations[integration_name]["llm_stream_callback"]
            #
            if callback is None:
                raise RuntimeError("Action is not supported")
            #
            stream_id = self.add_stream()
            #
            try:
                invoke_kwargs = {
                    "routing_key": None,
                }
                #
                invoke_kwargs.update(callback(settings, text, stream_id))
                #
                self.task_node.start_task(
                    name="invoke_model",
                    kwargs=invoke_kwargs,
                    pool="indexer",
                )
                #
                while True:
                    event = self.streams[stream_id].get()  # TODO: timeouts
                    #
                    event_type = event.get("type", None)
                    event_data = event.get("data", None)
                    #
                    if event_type == "stream_end":
                        break
                    #
                    if event_type == "stream_chunk":
                        yield event_data
                    #
                    if event_type == "stream_exception":
                        raise RuntimeError(event_data)
                #
            finally:
                log.debug("Stream ended: %s", stream_id)
                #
                self.remove_stream(stream_id)
        else:
            #
            # LLM interface
            #
            # if llm_interface_callback is None:
            #     raise RuntimeError("LLM action is not supported")
            #
            yield from llm_interface_callback(integration_name, settings, text)

    @web.method()
    def chat_model_stream(  # pylint: disable=R0913
            self, integration_name, settings, messages,
        ):
        """ Stream model """
        use_legacy_llm_mode = self.descriptor.config.get("use_legacy_llm_mode", False)
        llm_interface_callback = self.llm_interface["chat_model_stream_callback"]
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
            callback = self.integrations[integration_name]["chat_model_stream_callback"]
            #
            if callback is None:
                raise RuntimeError("Action is not supported")
            #
            stream_id = self.add_stream()
            #
            try:
                invoke_kwargs = {
                    "routing_key": None,
                }
                #
                invoke_kwargs.update(callback(settings, messages, stream_id))
                #
                self.task_node.start_task(
                    name="invoke_model",
                    kwargs=invoke_kwargs,
                    pool="indexer",
                )
                #
                while True:
                    event = self.streams[stream_id].get()  # TODO: timeouts
                    #
                    event_type = event.get("type", None)
                    event_data = event.get("data", None)
                    #
                    if event_type == "stream_end":
                        break
                    #
                    if event_type == "stream_chunk":
                        yield event_data
                    #
                    if event_type == "stream_exception":
                        raise RuntimeError(event_data)
            finally:
                log.debug("Stream ended: %s", stream_id)
                #
                self.remove_stream(stream_id)
        else:
            #
            # LLM interface
            #
            # if llm_interface_callback is None:
            #     raise RuntimeError("LLM action is not supported")
            #
            yield from llm_interface_callback(integration_name, settings, messages)
