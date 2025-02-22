# -*- coding: utf-8 -*-
# Copyright CERN since 2015
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from rucio.api import permission
from rucio.common import exception
from rucio.core import heartbeat


def list_heartbeats(issuer=None, vo='def'):
    """
    Return a list of tuples of all heartbeats.

    :param issuer: The issuer account.
    :param vo: the VO for the issuer.
    :returns: List of tuples [('Executable', 'Hostname', ...), ...]
    """

    kwargs = {'issuer': issuer}
    if not permission.has_permission(issuer=issuer, vo=vo, action='list_heartbeats', kwargs=kwargs):
        raise exception.AccessDenied('%s cannot list heartbeats' % issuer)
    return heartbeat.list_heartbeats()


def create_heartbeat(executable, hostname, pid, thread, older_than, payload, issuer=None, vo='def'):
    """
    Creates a heartbeat.
    :param issuer: The issuer account.
    :param vo: the VO for the issuer.
    :param executable: Executable name as a string, e.g., conveyor-submitter.
    :param hostname: Hostname as a string, e.g., rucio-daemon-prod-01.cern.ch.
    :param pid: UNIX Process ID as a number, e.g., 1234.
    :param thread: Python Thread Object.
    :param older_than: Ignore specified heartbeats older than specified nr of seconds.
    :param payload: Payload identifier which can be further used to identify the work a certain thread is executing.

    """
    kwargs = {'issuer': issuer}
    if not permission.has_permission(issuer=issuer, vo=vo, action='send_heartbeats', kwargs=kwargs):
        raise exception.AccessDenied('%s cannot send heartbeats' % issuer)
    heartbeat.live(executable=executable, hostname=hostname, pid=pid, thread=thread, older_than=older_than, payload=payload)
