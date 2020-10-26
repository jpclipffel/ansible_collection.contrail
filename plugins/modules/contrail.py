ANSIBLE_METADATA = {
    'metadata_version': '0.1',
    'status': ['preview'],
    'supported_by': 'community'
}

DOCUMENTATION = r'''
---
module: contrail

short_description: Interact with Juniper Contrail via REST API

version_added: "2.9"

description:
    - "Interact with Juniper Contrail via REST API"

options:
    name:
        description:
            - Resource name
        required: true
        type: 'str'
    type:
        description:
            - Resource type (e.g. virtual-network)
        required: true
        type: str
    state:
        description:
            - Expected resource state
        required: true
        choices:
            - present
            - absent
            - query
        type: str
    domain:
        description:
            - Domain name (e.g. default-domain)
        required: true
        type: str
    project:
        description:
            - Project name (e.g. vCenter)
        required: true
        type: str
    definition:
        description:
            - Resource definition (REST API payload)
        required: false
        type: dict

author:
    - Jean-Philippe Clipffel (@jpclipffel)
'''

EXAMPLES = r'''
- name: Query resource
  contrail:
    name: virtualNetwork1
    type: virtual-network
    domain: default-domain
    project: vCenter
    state: query
'''

RETURN = r'''
msg:
    description: General status
    type: str
    returned: always
api:
    description: API request and response
    type: complex
    returned: always
    contains:
        method:
            description: API request method
            type: str
            returned: always
        path:
            description: API request path
            type: str
            returned: always
        request:
            description: API request payload
            type: complex
            returned: always
        response:
            description: API response
            type: complex
            returned: always
        status_code:
            description: API respose status code
            type: int
            returned: always
'''


import re
import json
from hashlib import md5
from copy import deepcopy

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.connection import Connection
# from ansible.module_utils.common.dict_transformations import dict_merge
# pylint: disable=no-name-in-module,import-error
# from ansible.module_utils.contrail import dict_merge




class Result:
    '''Generic Contrail API result.

    Any request made to the API (i.e. using `send_request`) **should** returns a :class:`Result` instance.
    '''
    def __init__(self, changed=False, failed=False, msg="", method="", path="", request={}, response={}, status_code=-1):
        self.changed = changed
        self.failed = failed
        self.msg = msg
        # ---
        self.method = method
        self.path = path
        self.request = request
        self.response = response
        self.status_code = status_code
    
    def to_dict(self):
        '''Transforms the :class:`Result` to a `dict` object suitable for Ansible.
        '''
        return {
            "changed": self.changed,
            "failed": self.failed,
            "msg": self.msg,
            "api": {
                "method": self.method,
                "path": self.path,
                "request": self.request,
                "response": self.response,
                "status_code": self.status_code
            }
        }


class ContrailError(Exception):
    '''Generic Contrail API error.

    This exception wraps a :class:`Result` instance.
    '''
    def __init__(self, result):
        self.result = result


class Resource:
    '''Generic Contrail resource interface.

    One **should not** use a :class:`Resource` directly -> a derivied class, such as
    :class:`VirtualNetwork` must be used instead.
    '''

    # Resource properties, overide by :class:`Resource`'s derived classes.
    type = ""           # string; The resource type name (e.g. 'virtual-network')
    path_get = ""       # string; API path to 'GET' the resource 
    path_put = ""       # string; API path to 'PUT' to the resource
    path_post = ""      # string; API path to 'POST' to the resource
    parent_type = ""    # string; Resource parent type name (e.g. 'project')
    subresources = {}   # dict; Sub resources as { "field_name": "resource_type" }

    def __init__(self, contrail, name, project, domain):
        '''Initializes the instance.

        :param Contrail contrail: :class:`Contrail` instance
        :param str name: Resource name (== display name)
        :param str project: Resource project name
        :param domain: Resource domain name
        '''
        self.contrail = contrail
        self.name = name
        self.project = project
        self.domain = domain
        # ---
        self._uuid = None
        self._definition = None
    
    @property
    def uuid(self):
        '''Returns the resource UUID.

        :rtype: str
        :raise: ContrailError
        '''
        method, path = "POST", "/fqname-to-id"
        request, content, status_code = {}, {}, -1
        # ---
        try:
            if not self._uuid:
                request = {"type": self.type, "fq_name": [self.domain, self.project, self.name]}
                status_code, content = self.contrail.connection.send_request(method, path, request)
                if status_code in [200, ] and "uuid" in content:
                    self._uuid = content["uuid"]
                else:
                    raise Exception("Failed to resolve resource UUID")
            return self._uuid
        except Exception as error:
            raise ContrailError(Result(
                failed=True, msg='Exception: {0}'.format(str(error)), 
                method=method, path=path, request=request, response=content, status_code=status_code))
    
    @property
    def definition(self):
        '''Returns the resource definition.

        :rtype: dict
        :raise: ContrailError
        '''
        method, path = "GET", "/{0}/{1}".format(self.path_get, self.uuid)
        request, content, status_code = {}, {}, -1
        # ---
        try:
            if not self._definition:
                status_code, content = self.contrail.connection.send_request(method, path)
                if status_code in [200, ]:
                    self._definition = content
                else:
                    raise Exception("Failed to fetch resource definition")
            return self._definition
        except Exception as error:
            raise ContrailError(Result(
                failed=True, msg='Exception: {0}'.format(str(error)), 
                method=method, path=path, request=request, response=content, status_code=status_code))
    
    @property
    def exists(self):
        '''Returns `True` is the resource exists (i.e. has an UUID), `False` otherwise.

        :rtype: Bool
        '''
        try:
            if self.uuid:
                return True
            return False
        except ContrailError as error:
            if error.result.status_code in [404, ]:
                return False
            raise error

    def apply(self, definition):
        '''Creates or update the resource.

        If the resource already exists, a 'PUT' call is performed (update).
        If the resource doesn't exists, a 'POST' call is performed (create).

        If the resource definition includes sub-resources references, the sub-resources will be
        created or updated too.
        Supported sub-resources are mapped in the resource class' `.subresources` attribute.

        :param dict definition: Resource definition (API payload)
        :rtype: Result
        :raise: ContrailError
        '''
        # ---
        # Initialize API method, path, payload and return values.
        # method, path = "", ""
        # _definition, content, status_code = {}, {}, -1
        # ---
        # Sub-resources creation or update.
        # To be considered as a valid sub-resource, a sub-reousrce must:
        # - be reference in the base (parent) resource's `.subresources` map
        # - have a `.to` and `.attr` members
        # try:
        #     for sub_type, sub_defns in definition.items():
        #         if sub_type in self.subresources and sub_defns is not None:
        #             for sub_defn in sub_defns:
        #                 if "to" in sub_defn and "attr" in sub_defn:
        #                     # ---
        #                     # Prepare sub-resource
        #                     subresource = self.contrail.resource(
        #                         type=self.subresources[sub_type],
        #                         name=sub_defn["to"][2],
        #                         project=sub_defn["to"][1],
        #                         domain=sub_defn["to"][0])
        #                     # ---
        #                     # Create or update sub-resource
        #                     subresource.apply(mode, sub_defn["attr"])
        #                     # ---
        #                     # Remove sub-resource defnition defnition form base resource
        #                     # That's what Contrail command seems to doe, even though the API server
        #                     # accepts to ahve a non-null `.attr` field.
        #                     sub_defn["attr"] = None
        # except ContrailError as error:
        #     error.result.msg = "Failed to update or create sub resource: {0}".format(error.result.msg)
        #     raise error
        try:
            if self.exists:
                action, method, path = "update", "PUT", '/{0}/{1}'.format(self.path_put, self.uuid)
                _definition = self.definition
                _definition[self.type].update(definition)
                # _definition = dict_merge(self.definition[self.type], definition)
            else:
                action, method, path = "create", "POST", "/{0}".format(self.path_post)
                _definition = {self.type: {
                    "parent_type": self.parent_type,
                    "fq_name": [ self.domain, self.project, self.name ]
                }}
                _definition[self.type].update(definition)
            # ---
            # Run API call
            status_code, content = self.contrail.connection.send_request(method, path, _definition)
            # ---
            # Control API response
            if status_code not in [200, ]:
                raise ContrailError(Result(
                    failed=True, msg="Failed to {0} resource".format(action),
                    method=method, path=path, request=_definition, response=content, status_code=status_code))
            else:
                return Result(
                    changed=True, msg="Resource {0}d".format(action),
                    method=method, path=path, request=_definition, response=content, status_code=status_code)
            # ---
            # Done
        except ContrailError as error:
            raise error
        except Exception as error:
            raise ContrailError(Result(failed=True, msg=str(error)))

    def delete(self, definition={}):
        '''Deletes the resource.

        If the resource exists:
        - it is first emptied (updated with an empty defnition)
        - then it is DELETEd
        If the resource doesn't exists, nothing is done.

        :param dict definition: Resource definition (to dereference it before deletion); Optional
        :rtype: Result
        :raise: ContrailError
        '''
        # ---
        # Initialize API method, path, payload and return values.
        method, path = "DELETE", '/{0}/{{0}}'.format(self.path_put)
        _definition, content, status_code = {}, {}, -1
        try:
            # ---
            # We only try to delete resources which does exists.
            if self.exists:
                # ---
                # Build a custom defnition with empty sub-resrources references:
                # --> Known sub-resource keys are preserved but set to Null to force dereference.
                # for sub_type, _ in definition.items():
                #     if sub_type in self.subresources and sub_type in _definition:
                #         _definition[sub_type] = None
                # ---
                # If we're in merging mode, build the a custom defnition from the existing one minus the provided one.
                # Otherwise, use the provided one.
                # _definition = definition
                # ---
                # Update resource with the custom de-referencing definition
                # self.apply(mode=mode, definition=_definition)
                # status_code, content = self.contrail.connection.send_request("PUT", path.format(self.uuid), definition)
                # ---
                # Delete resource
                status_code, content = self.contrail.connection.send_request(method, path.format(self.uuid))
                if status_code not in [200, ]:
                    raise Exception("Failed to delete resource")
                msg = "Resource deleted"
            else:
                msg = "Resource does not exists"
            return Result(
                changed=False, msg=msg, request=_definition,
                method=method, path=path, status_code=status_code)
        except ContrailError as error:
            raise error
        except Exception as error:
            raise ContrailError(Result(
                failed=True, msg='Exception {0}'.format(str(error)),
                method=method, path=path, response=content, status_code=status_code))



# class IPAM:
#     '''Contrail API object 'network-ipam'
#     '''
#     type = "ipam"
#     path_get = "ipam"
#     path_put = "ipam"
#     path_post = "ipam"
#     parent_type = "project"
#     subresources = {
#         "network_ipam_refs": "ipam"
#     }


class VirtualNetwork(Resource):
    '''Contrail API object 'virtual-network'
    '''
    type        = "virtual-network"
    path_get    = "virtual-network"
    path_put    = "virtual-network"
    path_post   = "virtual-networks"
    parent_type = "project"
    # subresources = {
    #     "network_ipam_refs": "ipam"
    # }


class VirtualMachineInterface(Resource):
    '''Contrail API object 'virtual-machine-interface' and 'virtual-port'
    '''
    type = "virtual-machine-interface"
    path_get = "virtual-machine-interface"
    path_put = "virtual-machine-interface"
    path_post = "virtual-machine-interfaces"
    parent_type = "project"


class VirtualPortGroup(Resource):
    '''Contrail API object 'virtual-port-group'
    '''
    type = "virtual-port-group"
    path_get = "virtual-port-group"
    path_put = "virtual-port-group"
    path_post = "virtual-port-groups"
    parent_type = "fabric"
    subresources = {
        "virtual_machine_interface_refs": "virtual-machine-interface"
    }


class LogicalRouter(Resource):
    '''Contrail API object 'logical-router'
    '''
    type = 'logical-router'
    path_get = 'logical-router'
    path_put = 'logical-router'
    path_post = 'logical-routers'
    parent_type = 'project'


class Contrail:
    '''Interfaces with Contrail API (high-level functions).

    :attr resources_map: Mapping between resources type name and classes.
    '''

    resources_map = {
        # "ipam": IPAM,
        'virtual-network': VirtualNetwork,
        'virtual-machine-interface': VirtualMachineInterface,
        'virtual-port': VirtualMachineInterface,
        'virtual-port-group': VirtualPortGroup,
        'logical-router': LogicalRouter
    }

    def __init__(self, module, connection):
        '''Initializes instance.

        :param object module: Ansible module instance
        :param object connection: Ansible connection plugin interface
        '''
        self.module = module
        self.connection = connection

    def resource(self, type, name, project, domain):
        '''Returns the requested resource.

        :param str type: Resource type name (e.g. 'virtual-network')
        :param str name: Resource name
        :param str project: Resource project
        :param str domain: Resource domain

        :return: A new resource instance
        :rtype: Resource
        :raise: ContrailError
        '''
        if not type in self.resources_map:
            raise ContrailError(Result(False, "failure", "Unknown resource type: {0}".format(type)))
        return self.resources_map[type](self, name, project, domain)

    def state_query(self, type, name, project, domain, **kwargs):
        '''Query a resource.

        :param str type: Resource type name (e.g. 'virtual-network')
        :param str name: Resource name
        :param str project: Resource project
        :param str domain: Resource domain

        :return: A new resource instance
        :rtype: Result
        :raise: ContrailError
        '''
        resource = self.resource(type, name, project, domain)
        return Result(msg="Resource queried", response=resource.definition)
        # if resource.exists:
        #     return Result(msg="Resource queried", response=resource.definition)
        # else:
        #     return Result(failed=True, msg="Resource does not exists")

    def state_present(self, type, name, project, domain, definition, **kwargs):
        '''Creates or updates a resource.

        :param str type: Resource type name (e.g. 'virtual-network')
        :param str name: Resource name
        :param str project: Resource project
        :param str domain: Resource domain
        :param definition: Resource definition (API payload)

        :return: A new resource instance
        :rtype: Result
        :raise: ContrailError
        '''
        try:
            resource = self.resource(type, name, project, domain)
            return resource.apply(definition)
        except ContrailError as error:
            raise error

    def state_absent(self, type, name, project, domain, definition={}, **kwargs):
        '''Removes a resource.

        :param str type: Resource type name (e.g. 'virtual-network')
        :param str name: Resource name
        :param str project: Resource project
        :param str domain: Resource domain
        :param definition: Resource definition (to dereference resource before deletion)

        :return: A new resource instance
        :rtype: Result
        :raise: ContrailError
        '''
        try:
            resource = self.resource(type, name, project, domain)
            return resource.delete(definition)
        except ContrailError as error:
            raise error


def run_module():
    '''Ansible module entry point.
    '''
    # Ansible module arguments
    module_args = dict(
        name=dict(type=str, required=True),
        type=dict(type=str, required=True, choices=[k for k, _ in Contrail.resources_map.items()]),
        state=dict(type=str, required=True, choices=["present", "absent", "query"]),
        domain=dict(type=str, required=True),
        project=dict(type=str, required=True),
        definition=dict(type=dict, required=False, default={}))
    # Initializes module, connection and API helper
    module = AnsibleModule(argument_spec=module_args, supports_check_mode=False)
    connection = Connection(module._socket_path)
    contrail = Contrail(module, connection)
    # Run module
    try:
        # Run module in 'query' mode (gather info)
        if module.params["state"] in ["query", ]:
            # result = contrail.state_query(resource_type, resource_name, resource_project, resource_domain)
            result = contrail.state_query(**module.params)
        # Run module in 'present' mode (may create or update resource(s))
        elif module.params["state"] in ["present", ]:
            # result = contrail.state_present(resource_type, resource_name, resource_project, resource_domain, resource_definition)
            result = contrail.state_present(**module.params)
        # Run module in 'absent' mode (may deletes resource(s))
        elif module.params["state"] in ["absent", ]:
            # result = contrail.state_absent(resource_type, resource_name, resource_project, resource_domain, resource_definition)
            result = contrail.state_absent(**module.params)
        # Invalid state
        else:
            result = Result(failed=True, msg="Invalid module state: {0}".format(module.params["state"]))
    except ContrailError as error:
        result = error.result
    # Exit
    if result.failed:
        module.fail_json(**result.to_dict())
    else:
        module.exit_json(**result.to_dict())


def main():
    run_module()


if __name__ == '__main__':
    main()
