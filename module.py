#!/usr/bin/python3
# coding=utf-8
# pylint: disable=C0413

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

""" Module """

import os
import threading

from pylon.core.tools import log  # pylint: disable=E0611,E0401
from pylon.core.tools import module  # pylint: disable=E0611,E0401

import arbiter  # pylint: disable=E0401


class Module(module.ModuleModel):  # pylint: disable=R0902
    """ Pylon module """

    def __init__(self, context, descriptor):
        self.context = context
        self.descriptor = descriptor
        #
        self.event_node_config = None
        self.event_node = None
        #
        self.task_node = None
        #
        self.runtime_engine_ready_event = threading.Event()

    def preload(self):
        """ Preload handler """
        if "TIKTOKEN_CACHE_DIR" in os.environ:
            log.info("Preloading Tiktoken bundle")
            #
            tiktoken_cache_dir = os.environ["TIKTOKEN_CACHE_DIR"]
            #
            os.makedirs(tiktoken_cache_dir, exist_ok=True)
            #
            try:
                from tools import this  # pylint: disable=E0401,C0415
                #
                def _install_needed(*_args, **_kwargs):
                    try:
                        dir_entries = [
                            item for item in os.listdir(tiktoken_cache_dir)
                            if not item.startswith(".")
                        ]
                        return len(dir_entries) == 0
                    except:  # pylint: disable=W0702
                        return True
                #
                this.for_module("bootstrap").module.get_bundle(
                    "tiktoken-encodings.tar.gz",
                    install_needed=_install_needed,
                    processing="tar_extract",
                    extract_target=tiktoken_cache_dir,
                    extract_cleanup=False,
                )
                #
                log.info("Preloaded Tiktoken bundle")
            except:  # pylint: disable=W0702
                log.exception("Failed to preload Tiktoken bundle")
        #
        self.descriptor.register_tool("worker_client", self)

    def init(self):
        """ Init module """
        log.info("Initializing module")
        # Init
        self.descriptor.init_all()
        # Bundles
        if "TIKTOKEN_CACHE_DIR" in os.environ:
            tiktoken_cache_dir = os.environ["TIKTOKEN_CACHE_DIR"]
            #
            os.makedirs(tiktoken_cache_dir, exist_ok=True)
            #
            try:
                from tools import this  # pylint: disable=E0401,C0415
                #
                def _install_needed(*_args, **_kwargs):
                    try:
                        dir_entries = [
                            item for item in os.listdir(tiktoken_cache_dir)
                            if not item.startswith(".")
                        ]
                        return len(dir_entries) == 0
                    except:  # pylint: disable=W0702
                        return True
                #
                this.for_module("bootstrap").module.get_bundle(
                    "tiktoken-encodings.tar.gz",
                    install_needed=_install_needed,
                    processing="tar_extract",
                    extract_target=tiktoken_cache_dir,
                    extract_cleanup=False,
                )
                log.info("Using Tiktoken bundle")
            except:  # pylint: disable=W0702
                pass
        # EventNode
        self.event_node_config = self.get_event_node_config()
        self.event_node = arbiter.make_event_node(
            config=self.event_node_config,
        )
        self.event_node.start()
        self.event_node.subscribe(
            "stream_event", self.on_stream_event
        )
        self.event_node.subscribe(
            "bootstrap_runtime_info", self.i2p_bootstrap_runtime_info
        )
        self.event_node.subscribe(
            "bootstrap_runtime_info_prune", self.i2p_bootstrap_runtime_info_prune
        )
        self.event_node.subscribe(
            "runtime_engine_ready", lambda *_args, **_kwargs: self.runtime_engine_ready_event.set()
        )
        # RpcNode
        self.rpc_node = arbiter.RpcNode(
            self.event_node,
            id_prefix="indexer_",
        )
        self.rpc_node.start()
        self.rpc_node.register(
            self.restricted_ping,
            name="restricted_ping",
        )
        self.rpc_node.register(
            self.restricted_get_admin_secret,
            name="restricted_get_admin_secret",
        )
        # TaskNode
        self.task_node = arbiter.TaskNode(
            self.event_node,
            pool="indexer",
            task_limit=0,
            ident_prefix="indexer_",
            multiprocessing_context="threading",
            kill_on_stop=False,
            task_retention_period=3600,
            housekeeping_interval=60,
            start_max_wait=3,
            query_wait=3,
            watcher_max_wait=3,
            stop_node_task_wait=3,
            result_max_wait=3,
        )
        self.task_node.start()
        # Tool
        self.descriptor.register_tool("worker_client", self)
        # Postgres proxy
        postgres_proxy = self.descriptor.config.get("postgres_proxy", None)
        #
        if postgres_proxy:
            from .tools.postgres import start_postgres_proxy
            start_postgres_proxy(
                bind=postgres_proxy.get("bind", "0.0.0.0:5432"),
                remote=postgres_proxy.get("remote"),
                scope=postgres_proxy.get("scope", "https://ossrdbms-aad.database.windows.net/.default"),
            )

    def deinit(self):
        """ De-init module """
        log.info("De-initializing module")
        # Tool
        self.descriptor.unregister_tool("worker_client")
        # TaskNode
        self.task_node.stop()
        # RpcNode
        self.rpc_node.unregister(
            self.restricted_get_admin_secret,
            name="restricted_get_admin_secret",
        )
        self.rpc_node.unregister(
            self.restricted_ping,
            name="restricted_ping",
        )
        self.rpc_node.stop()
        # EventNode
        self.event_node.unsubscribe(
            "bootstrap_runtime_info_prune", self.i2p_bootstrap_runtime_info_prune
        )
        self.event_node.unsubscribe(
            "bootstrap_runtime_info", self.i2p_bootstrap_runtime_info
        )
        self.event_node.unsubscribe(
            "stream_event", self.on_stream_event
        )
        self.event_node.stop()
        # De-init
        self.descriptor.deinit_all()
