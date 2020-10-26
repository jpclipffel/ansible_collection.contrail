# Contrail module - Ansible module for Juniper Contrail

*Developer documentation*

## Resources support

This module is not responsible for the resource validation; Contrail's server will verify the resources by itself before trying to create or updated them. Thus, the module support for resources is simple:

* `Resource` is the base class for all resources. It provides method to query, create and delete resources.
* Classes inheriting from `Resource` should only provides their API paths (see example bellow).
* The `Contrail` class maintains a mapping between resource type name (e.g. `virtual-network`) and resource class (e.g. `VirtualNetwork`).

To add support for a new resource type, first create a class which will specify the resource API path:

```python
class VirtualNetwork(Resource):         # Your resource must inherit form `Resource`
    type = "virtual-network"            # Resource type name
    path_get = "virtual-network"        # API path fragment to query (`GET`) the resource
    path_put = "virtual-network"        # API path fragment to update (`PUT`) the resource
    path_post = "virtual-networks"      # API path fragment to create (`POST`) the resource
    parent_type = "project"             # Resource parent type name
```

Then add a new mapping in `Contrail.resources_map`:

```python
class Contrail:
    resources_map = {
        # virtual-network is the resource type name
        # VirtualNetwork is the resource class
        "virtual-network": VirtualNetwork
    }
```
