#!/usr/bin/python3
# coding=utf-8

#   Copyright 2026 EPAM Systems
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

import os

from pylon.core.tools import log  # pylint: disable=E0611,E0401,W0611
from pylon.core.tools import web  # pylint: disable=E0611,E0401,W0611

from tools import context  # pylint: disable=E0401

from ..tools import stack_dump


# TaskNodes hosted by this pylon. All are threading-mode, so their tasks are
# read out of the live interpreter rather than signalled.
LOCAL_TASK_NODES = [
    ("elitea_core", "task_node"),
    ("worker_client", "task_node"),
    ("admin", "task_node"),
]


class Method:  # pylint: disable=E1101,R0903,W0201
    """
        Method Resource

        self is pointing to current Module instance

        web.method decorator takes zero or one argument: method name
        Note: web.method decorator must be the last decorator (at top)
    """
    @web.method()
    def request_task_dump(self, task_id):
        """ Ask whichever pylon owns this task for its stack """
        return stack_dump.request_dump(self.event_node, task_id)

    @web.method()
    def stack_dump_event_request(self, event, data):
        """ Event: dump the stack of a task this pylon owns """
        # Redis events are broadcast, so this pylon sees its own request; it
        # answers only for tasks in its own running_tasks.
        _ = event
        #
        task_id = data.get("task_id")
        if not task_id:
            return
        #
        located = _find_running_task(self.context.module_manager, task_id)
        if located is None:
            return
        #
        node_label, task_node, thread = located
        #
        log.info("Dumping stack of task %s on %s", task_id, node_label)
        #
        try:
            reply = _collect_thread_dump(task_id, task_node, thread)
        except Exception as exc:  # pylint: disable=W0703
            log.exception("Stack dump failed for task %s", task_id)
            reply = {"ok": False, "error": f"dump failed: {exc}"}
        #
        reply.update({
            "request_id": data.get("request_id"),
            "task_id": task_id,
            "pylon_id": context.id,
            "node": node_label,
        })
        #
        self.event_node.emit("task_dump_reply", reply)

    @web.method()
    def stack_dump_event_reply(self, event, data):
        """ Event """
        _ = event
        stack_dump.deliver_reply(data)


def _find_running_task(module_manager, task_id):
    """ Find which local TaskNode is running this task """
    for plugin_name, node_name in LOCAL_TASK_NODES:
        if plugin_name not in module_manager.modules:
            continue
        #
        plugin = module_manager.modules[plugin_name].module
        if plugin is None:
            continue
        #
        task_node = getattr(plugin, node_name, None)
        if task_node is None or not task_node.started:
            continue
        #
        with task_node.lock:
            task_data = task_node.running_tasks.get(task_id)
            if task_data is None:
                continue
            #
            thread = task_data.get("thread")
        #
        return f"{plugin_name}.{node_name}", task_node, thread
    #
    return None


def _collect_thread_dump(task_id, task_node, thread):
    """ Read the one task thread's frame, no signal """
    body, error = stack_dump.dump_task_thread(thread, task_node.gevent_runtime)
    #
    if error is not None:
        return {"ok": False, "mode": "thread", "error": error}
    #
    previous = stack_dump.remember_thread_dump(task_id, body)
    #
    return {
        "ok": True,
        "mode": "thread",
        "pid": os.getpid(),
        "dump": body,
        "previous_dump": previous,
        "dump_count": 2 if previous else 1,
        "verdict": stack_dump.compare_dumps(previous, body),
    }
