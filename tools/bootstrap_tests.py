#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright CERN since 2013
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

import os.path
import sys
import time

base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(base_path)
os.chdir(base_path)

from rucio.api.vo import add_vo  # noqa: E402
from rucio.client import Client  # noqa: E402
from rucio.common.config import config_get, config_get_bool  # noqa: E402
from rucio.common.exception import Duplicate, RucioException  # noqa: E402
from rucio.core.account import add_account_attribute  # noqa: E402
from rucio.core.vo import map_vo  # noqa: E402
from rucio.common.types import InternalAccount  # noqa: E402
from rucio.tests.common_server import reset_config_table  # noqa: E402


if __name__ == '__main__':
    # Create config table including the long VO mappings
    reset_config_table()
    if config_get_bool('common', 'multi_vo', raise_exception=False, default=False):
        vo = {'vo': map_vo(config_get('client', 'vo', raise_exception=False, default='tst'))}
        try:
            add_vo(new_vo=vo['vo'], issuer='super_root', description='A VO to test multi-vo features', email='N/A', vo='def')
        except Duplicate:
            print('VO {} already added'.format(vo['vo']) % locals())
    else:
        vo = {}

    try:
        c = Client()
    except RucioException as e:
        error_msg = str(e)
        print('Creating client failed:', error_msg)
        if 'Internal Server Error' in error_msg:
            server_log = '/var/log/rucio/httpd_error_log'
            if os.path.exists(server_log):
                # wait for the server to write the error to log
                time.sleep(5)
                with open(server_log, 'r') as fhandle:
                    print(fhandle.readlines()[-200:], file=sys.stderr)
        raise

    try:
        c.add_account('jdoe', 'SERVICE', 'jdoe@email.com')
    except Duplicate:
        print('Account jdoe already added' % locals())

    try:
        add_account_attribute(account=InternalAccount('root', **vo), key='admin', value=True)  # bypass client as schema validation fails at API level
    except Exception as error:
        print(error)

    try:
        c.add_account('panda', 'SERVICE', 'panda@email.com')
        add_account_attribute(account=InternalAccount('panda', **vo), key='admin', value=True)
    except Duplicate:
        print('Account panda already added' % locals())

    try:
        c.add_scope('jdoe', 'mock')
    except Duplicate:
        print('Scope mock already added' % locals())

    try:
        c.add_scope('root', 'archive')
    except Duplicate:
        print('Scope archive already added' % locals())

    # add your accounts here, if you test against CERN authed nodes
    additional_test_accounts = [('/DC=ch/DC=cern/OU=Organic Units/OU=Users/CN=mlassnig/CN=663551/CN=Mario Lassnig', 'x509', 'mario.lassnig@cern.ch'),
                                ('/DC=ch/DC=cern/OU=Organic Units/OU=Users/CN=barisits/CN=692443/CN=Martin Barisits', 'x509', 'martin.barisits@cern.ch'),
                                ('/DC=ch/DC=cern/OU=Organic Units/OU=Users/CN=tbeerman/CN=722011/CN=Thomas Beermann', 'x509', 'thomas.beermann@cern.ch'),
                                ('/DC=ch/DC=cern/OU=Organic Units/OU=Users/CN=ruciobuildbot/CN=692443/CN=Robot: Rucio build bot', 'x509', 'rucio.build.bot@cern.ch'),
                                ('/CN=docker client', 'x509', 'dummy@cern.ch'),
                                ('mlassnig@CERN.CH', 'GSS', 'mario.lassnig@cern.ch')]

    for i in additional_test_accounts:
        try:
            c.add_identity(account='root', identity=i[0], authtype=i[1], email=i[2])
        except Exception:
            print('Already added: ', i)
