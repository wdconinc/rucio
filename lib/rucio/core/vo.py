# -*- coding: utf-8 -*-
# Copyright CERN since 2019
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

import re
from sqlalchemy.exc import DatabaseError, IntegrityError
from sqlalchemy.orm.exc import NoResultFound

import rucio.core.config as config_db
from rucio.common import exception
from rucio.common.config import config_get_bool
from rucio.common.types import InternalAccount
from rucio.db.sqla import models
from rucio.db.sqla.constants import AccountType, IdentityType
from rucio.db.sqla.session import read_session, transactional_session

# Format for long VO names
LONG_VO_RE = re.compile(r"^[a-zA-Z0-9\.\-]+$")


@read_session
def vo_exists(vo, session=None):
    """
    Verify that the vo exists.

    :param vo: The vo to verify.
    :param session: The db session in use.

    :returns: True if the vo is in the vo table, False otherwise
    """
    return True if session.query(models.VO).filter_by(vo=vo).first() else False


@transactional_session
def add_vo(vo, description, email, session=None):
    """
    Add a VO and setup a new root user.
    New root user will have account name 'root' and a userpass identity with username: 'root@<vo>' and password: 'password'

    :param vo: 3-letter unique tag for a VO.
    :param descrition: Descriptive string for the VO (e.g. Full name).
    :param email: Contact email for the VO.
    :param session: The db session in use.
    """
    if not config_get_bool('common', 'multi_vo', raise_exception=False, default=False):
        raise exception.UnsupportedOperation('VO operations cannot be performed in single VO mode.')

    if len(vo) != 3:
        raise exception.RucioException('Invalid VO tag, must be 3 chars.')

    new_vo = models.VO(vo=vo, description=description, email=email)

    try:
        new_vo.save(session=session)
    except IntegrityError:
        raise exception.Duplicate('VO {} already exists!'.format(vo))
    except DatabaseError as error:
        raise exception.RucioException(error.args)

    from rucio.core.account import add_account, list_identities
    from rucio.core.identity import add_account_identity
    new_root = InternalAccount('root', vo=vo)
    add_account(account=new_root, type_=AccountType['SERVICE'], email=email, session=session)
    add_account_identity(identity='root@{}'.format(vo),
                         type_=IdentityType['USERPASS'],
                         account=new_root,
                         email=email,
                         default=False,
                         password='password',
                         session=session)

    for ident in list_identities(account=InternalAccount('super_root', vo='def'), session=session):
        add_account_identity(identity=ident['identity'], type_=ident['type'], account=new_root, email='', session=session)


@read_session
def list_vos(session=None):
    """
    List all the VOs in the db.

    :param session: The db session in use.
    :returns: List of VO dictionaries.
    """
    if not config_get_bool('common', 'multi_vo', raise_exception=False, default=False):
        raise exception.UnsupportedOperation('VO operations cannot be performed in single VO mode.')

    query = session.query(models.VO)

    vos = []
    for vo in query.all():
        vo_dict = {'vo': vo.vo,
                   'description': vo.description,
                   'email': vo.email,
                   'created_at': vo.created_at,
                   'updated_at': vo.updated_at}
        vos.append(vo_dict)

    return vos


@transactional_session
def update_vo(vo, parameters, session=None):
    """
    Update VO properties (email, description).

    :param vo: The VO to update.
    :param parameters: A dictionary with the new properties.
    :param session: The db session in use.
    """
    if not config_get_bool('common', 'multi_vo', raise_exception=False, default=False):
        raise exception.UnsupportedOperation('VO operations cannot be performed in single VO mode.')

    try:
        query = session.query(models.VO).filter_by(vo=vo).one()
    except NoResultFound:
        raise exception.VONotFound('VO {} not found'.format(vo))
    param = {}
    for key in parameters:
        if key in ['email', 'description']:
            param[key] = parameters[key]
    query.update(param)


def map_vo(vo):
    """
    Converts a long VO name into the internal short (three letter)
    tag mapping.
    Mappings are loaded from the vo-map section of the config database table.
    If a mapping is not found, the orignal is returned unchanged.
    :param vo: The long VO name string.
    :returns: The short VO name string.
    """
    # Newline is ignored by regexp if at end of string, so test for that as well.
    if not LONG_VO_RE.match(vo) or '\n' in vo:
        raise exception.RucioException('Invalid characters in VO name.')
    if not config_db.has_section("vo-map"):
        return vo  # No mapping config
    return config_db.get("vo-map", vo, default=vo)
