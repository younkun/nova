# Copyright 2012 Nebula, Inc.
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

from webob import exc

from nova import context
from nova import db


CHUNKS = 4
CHUNK_LENGTH = 255
MAX_SIZE = CHUNKS * CHUNK_LENGTH


def extract_password(instance):
    result = ''
    for datum in sorted(instance.get('system_metadata', []),
                        key=lambda x: x['key']):
        if datum['key'].startswith('password_'):
            result += datum['value']
    return result or None


def set_password(context, instance_uuid, password):
    """Stores password as system_metadata items.

    Password is stored with the keys 'password_0' -> 'password_3'.
    """
    password = password or ''
    meta = {}
    for i in xrange(CHUNKS):
        meta['password_%d' % i] = password[:CHUNK_LENGTH]
        password = password[CHUNK_LENGTH:]
    db.instance_system_metadata_update(context,
                                       instance_uuid,
                                       meta,
                                       False)


def handle_password(req, meta_data):
    ctxt = context.get_admin_context()
    password = meta_data.password
    if req.method == 'GET':
        return meta_data.password
    elif req.method == 'POST':
        # NOTE(vish): The conflict will only happen once the metadata cache
        #             updates, but it isn't a huge issue if it can be set for
        #             a short window.
        if meta_data.password:
            raise exc.HTTPConflict()
        if (req.content_length > MAX_SIZE or len(req.body) > MAX_SIZE):
            msg = _("Request is too large.")
            raise exc.HTTPBadRequest(explanation=msg)
        set_password(ctxt, meta_data.uuid, req.body)
    else:
        raise exc.HTTPBadRequest()
