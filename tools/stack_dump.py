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

""" Read-only stack dumps for hung tasks: requester side """

import collections
import ctypes
import sys
import threading
import traceback
import uuid

from pylon.core.tools import log  # pylint: disable=E0611,E0401


# The owning pylon has to signal the child and poll for the write, so this must
# comfortably exceed worker_core's own signal poll budget.
REQUEST_TIMEOUT = 8.0

MAX_DUMP_CHARS = 64 * 1024

# LRU is the only cleanup: nothing signals task completion here, so entries are
# evicted by age. Bounds worst case at this many dumps of MAX_DUMP_CHARS.
MAX_THREAD_HISTORY = 16

_NOISE_PATH_FRAGMENTS = (
    "/multiprocessing/process.py",
    "/multiprocessing/popen_fork.py",
    "/multiprocessing/context.py",
    "/threading.py",
    "/arbiter/tasknode/",
)

# A healthy streaming task parks in a blocking socket read between tokens, so
# two identical samples there mean "waiting on a peer", not "hung".
_IO_WAIT_FUNCTIONS = frozenset({
    "recv", "recv_into", "recvfrom", "recvmsg", "sendall", "sendto", "sendmsg",
    "do_handshake", "connect", "accept", "select", "poll", "_poll", "epoll_wait",
})

# 'read'/'wait'-style names are too generic to judge alone; inside these modules
# they are unambiguously a blocking wait on someone else.
_IO_WAIT_PATHS = (
    "/socket.py", "/ssl.py", "/selectors.py",
    "/httpcore/", "/httpx/", "/urllib3/", "/h11/", "/h2/",
)

_pending = {}
_pending_lock = threading.Lock()
_thread_history = collections.OrderedDict()


def _frame_lines(dump_text):
    """ Just the code positions, for comparing two dumps """
    return [
        line.strip() for line in dump_text.splitlines()
        if line.strip().startswith(("File \"", "  File \""))
    ]


def significant_frames(dump_text):
    """ Frames with runtime scaffolding dropped; falls back to all frames """
    interesting = [
        line for line in _frame_lines(dump_text)
        if not any(fragment in line for fragment in _NOISE_PATH_FRAGMENTS)
    ]
    #
    return interesting if interesting else _frame_lines(dump_text)


def task_section(dump_text):
    """ Just the thread running the task, out of an all-threads dump """
    # faulthandler dumps every thread; idle pool workers churn on their own and
    # would otherwise show up as the task making progress.
    if "Current thread" in dump_text:
        return "Current thread" + dump_text.split("Current thread")[-1]
    #
    return dump_text


def _leaf_frame(dump_text):
    """ Innermost frame of the thread running the task """
    dump_text = task_section(dump_text)
    frames = _frame_lines(dump_text)
    if not frames:
        return ""
    #
    # faulthandler emits leaf-first and says so in its header; format_stack is leaf-last.
    if "most recent call first" in dump_text:
        return frames[0]
    #
    return frames[-1]


def waiting_on_io(dump_text):
    """ True when the innermost frame is a blocking wait on a peer """
    leaf = _leaf_frame(dump_text)
    if not leaf:
        return False
    #
    # 'File "<path>", line N in <func>' — faulthandler and traceback agree here.
    function = leaf.rsplit(" in ", 1)[-1].strip() if " in " in leaf else ""
    path = leaf.split("\"")[1] if leaf.count("\"") >= 2 else ""
    #
    if function in _IO_WAIT_FUNCTIONS:
        return True
    #
    return any(fragment in path for fragment in _IO_WAIT_PATHS)


def compare_dumps(previous, current):
    """ Classify progress between two dumps of the same task """
    if not previous or not current:
        return "unknown"
    #
    previous, current = task_section(previous), task_section(current)
    #
    if _frame_lines(previous) == _frame_lines(current):
        # Same stack parked in a socket read is a slow peer, not a wedged task.
        return "waiting_on_io" if waiting_on_io(current) else "stuck"
    #
    if significant_frames(previous) == significant_frames(current):
        return "stuck_in_library"
    #
    return "spinning"


def remember_thread_dump(task_id, body):
    """ Store this dump and return the one from the previous press """
    previous = _thread_history.pop(task_id, None)
    #
    _thread_history[task_id] = body
    while len(_thread_history) > MAX_THREAD_HISTORY:
        _thread_history.popitem(last=False)
    #
    return previous


def dump_task_thread(thread, greenlet_runtime):
    """ Stack of one task thread, read live out of this interpreter """
    # No signal: signalling would dump every thread in the process. Under gevent
    # the 'thread' is a greenlet, which is absent from _current_frames().
    if thread is None or not thread.is_alive():
        return None, "task thread is not alive"
    #
    frame = None
    #
    if greenlet_runtime:
        try:
            greenlet = ctypes.cast(thread.ident, ctypes.py_object).value
            frame = getattr(greenlet, "gr_frame", None)
        except:  # pylint: disable=W0702
            frame = None
        #
        if frame is None:
            return None, "greenlet is not suspended in Python code"
    else:
        frame = sys._current_frames().get(thread.ident)  # pylint: disable=W0212
        if frame is None:
            return None, "thread has no live Python frame"
    #
    try:
        body = "".join(traceback.format_stack(frame)).strip()
    except:  # pylint: disable=W0702
        return None, "could not format thread stack"
    #
    return body[:MAX_DUMP_CHARS], None


def request_dump(event_node, task_id, timeout=REQUEST_TIMEOUT):
    """ Broadcast a dump request and wait for the owning pylon to answer """
    request_id = str(uuid.uuid4())
    slot = {"event": threading.Event(), "reply": None}
    #
    with _pending_lock:
        _pending[request_id] = slot
    #
    try:
        event_node.emit("task_dump_request", {
            "request_id": request_id,
            "task_id": task_id,
        })
        #
        if not slot["event"].wait(timeout):
            return {
                "ok": False,
                "error": (
                    "no pylon answered within "
                    f"{timeout:g}s — the task may have finished, or the owning "
                    "pylon is itself unresponsive"
                ),
            }
        #
        return slot["reply"]
    finally:
        with _pending_lock:
            _pending.pop(request_id, None)


def deliver_reply(data):
    """ Hand a task_dump_reply to whoever is waiting for it """
    request_id = data.get("request_id")
    if not request_id:
        return
    #
    with _pending_lock:
        slot = _pending.get(request_id)
    #
    if slot is None:
        log.debug("Stack dump reply %s arrived too late, dropping", request_id)
        return
    #
    slot["reply"] = data
    slot["event"].set()
