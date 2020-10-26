# Contrail - Manages Contrail resources 

## Synopsis

* Use the Juniper's Contrail's REST API.
* Does not support authentication yet.
* Support check mode.

## Requirements

The below requirements are needed on the Ansible controller that executes this module.

* Ansible plugin `httpapi.contrail` 

## Parameters

| Parameter                        | Choices/Defaults                 | Comments                                            |
|----------------------------------|----------------------------------|-----------------------------------------------------|
| **name**<br>*string/required*    |                                  | Contrail's resource name (e.g. `my_vpc`)            |
| **type**<br>*string/required*    |                                  | Contrail's resource type (e.g. `virtual-network`)   |
| **domain**<br>*string/required*  |                                  | Contrail's domain name (e.g. `default-domain`)      |
| **project**<br>*string/required* |                                  | Contrail's project name (e.g. `vCenter`)            |
| **definition**<br>*complex*      |                                  | The resource defnition as specifiec in Contrail API |
| **state**<br>*string/required*   | - present<br>- absent<br>- query | Determine if an object should be created, patched, deleted or queried. When set to `present`, a resource will be created, if it does not already exist. If set to `absent`, an existing resource will be deleted. If set to `present`, an existing resource will be patched, if its attributes differ from those specified using `definition`. If set to `query`, the resource properties will be collected. |

## Examples

```yaml
- name: Setup a virtual network
  contrail:
    name: test_ansible_1
    type: virtual-network
    domain: default-domain
    project: vCenter
    state: present
    definition:
      network_ipam_refs:
        - attr:
            ipam_subnets:
              - subnet:
                  ip_prefix: 100.100.100.0
                  ip_prefix_len: 24
          to:
            - default-domain
            - vCenter
            - vCenter-ipam

- name: Query a virtual network
  contrail:
    name: test_ansible_1
    type: virtual-network
    domain: default-domain
    project: vCenter
    state: present
```

## Return values

Common return values are documented [here](https://docs.ansible.com/ansible/latest/reference_appendices/common_return_values.html#common-return-values),
the following are the fields unique to this module:

| Key                         | Returned | Description       |
|-----------------------------|----------|-------------------|
| **result**<br>*complex*     | always   | Contrail response |
| **result.api**<br>*integer* | always   | API response      |
