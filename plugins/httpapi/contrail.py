from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

DOCUMENTATION = '''
---
author:
    - Jean-Philippe Clipffel (@jpclipffel)
httpapi : contrail
short_description: Httpapi Plugin for Juniper Contrail REST API
description:
  - This httpapi plugin provides methods to connect to Juniper Contrail via REST API
version_added: "2.9"

'''

import json

from ansible.errors import AnsibleConnectionFailure
from ansible.plugins.httpapi import HttpApiBase
from ansible.module_utils.basic import to_text
from ansible.module_utils.connection import ConnectionError
# pylint: disable = no-name-in-module, import-error
from ansible.module_utils.six.moves.urllib.error import HTTPError


# Contrail API except at least the Content-Type header.
# Authentication token must be passed in headers too.
BASE_HEADERS = {
    "Content-Type": "application/json;charset=UTF-8"
}


class HttpApi(HttpApiBase):
    '''Interfaces with Contrail API (low-level functions).
    '''
    def __init__(self, connection):
        super(HttpApi, self).__init__(connection)

    def send_request(self, request_method, path, data={}):
        '''Prepares, sends and format resonse of Contrail API requests.

        :param str request_method: HTTP method
        :param str path: API path
        :param dict data: Request data, serializable as JSON

        :return: A tuple as (status_code: int, content: dict)
        :rtype: tuple
        '''
        # Contrail API call may fail, and response may be empty or not in JSON format.
        # In such cases, a **custom** JSON content is returned as { "message": "..." }
        try:
            response, response_data = self.connection.send(path, json.dumps(data), method=request_method, headers=BASE_HEADERS)
            # Request succeed
            if response.getcode() in [200, ]:
                try:
                    content = json.loads(to_text(response_data.getvalue()))
                # Request succeed, but response not in JSON -> Generate custom response content
                except Exception:
                    content = { "message": to_text(response_data.getvalue()) }
                return response.getcode(), content
            # Request failed -> Generate custom response content
            else:
                return response.getcode(), {"message": to_text(response_data.getvalue())}
        # Generic errors -> Generate custom response content
        except AnsibleConnectionFailure as error:
            if to_text('401') in to_text(error):
                return 401, { "message": "Authentication failure" }
        except HTTPError as error:
            return error.code, json.loads(error.read())
