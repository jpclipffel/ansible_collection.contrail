# Ansible collection - Contrail

An Ansible collection to manage Contrail and Contrail infrastructures.

## Installation

### Automated and project-wide installation

Add a reference to this collection in your project's `collections/requirements.yml` (create the file if necessary).

Example when using a self-hosted collection (Ansible 2.10+):

```yaml
collections:
  - name: "https://<your.scm.url>/contrail.git"
```

Example when using a collection hosted on Ansible Galaxy:

```yaml
collections:
  - name: jpclipffel.contrail
```

### Manual installation

When using a locally-stored collection (Ansible 2.10+):

```bash
# Build the collection
# Assuming we are in the collection root directory:
ansible-galaxy collection build

# Install the collection
# Replace <version> with the appropriate version number
ansible-galaxy collection install "jpclipffel-contrail-<version>.tar.gz"
```

When using a collection hosted on Ansible Galaxy:

```bash
ansible-galaxy collection install jpclipffel.contrail
```

## Usage

### Inventory setup

As Contrail is **not** accessed through SSH but through an REST API, your Contrail host(s) must specify the connection parameters.

The following variables must be provided in your inventory for each Contrail host:

| Variable               | Type      | Required | Default | Expected value                 | Description            |
|------------------------|-----------|----------|---------|--------------------------------|------------------------|
| `ansible_httpapi_port` | `integer` | Yes      | -       | `8082`                         | Contrail API port      |
| `ansible_network_os`   | `string`  | Yes      | -       | `jpclipffel.contrail.contrail` | Network device module  |

Example:

```yaml
all:
  hosts:
    contrail.fqdn:
      ansible_network_os: jpclipffel.contrail.contrail      # Network device module
      ansible_httpapi_port: 8082                            # Contrail API port
```

### Playbooks setup

As Contrail is **not** accessed through SSH but through an REST API, your Contrail host(s) must specify the connection method.
It is also advised to provide Contrail's domain, project and IPAM values at the track level (see example).

The following parameters can be provided in your playbooks tracks when targetting Contrail hosts:

| Parameter     | Type               | Required | Default | Expected value | Description                                           |
|---------------|--------------------|----------|---------|----------------|-------------------------------------------------------|
| `connection`  | `string`           | Yes      | -       | `httpapi`      | Connection method                                     |
| `collections` | `list` of `string` | No       | -       | -              | List of collections which will be searched by default |

Example:

```yaml
- hosts: contrail

  # Required: Ansible connection type
  connection: httpapi

  # Optional: Collections
  collections:
    - jpclipffel.contrail

  # Optional: Contrail resources default variables
  vars:
    contrail_domain: "default-domain"
    contrail_project: "vCenter"
    contrail_ipam: "vCenter-ipam"

  # List of tasks:
  tasks:

    - name: Query VirtualNetwork
      # Use 'contrail' without collection prefix as we're referencing 'jpclipffel.contrail' in the playbook's collection
      contrail:
        # ...
    
    - name: Query LogicalRouter
      # We would prefix the 'contrail' module if we'rnt referencing 'jpclipffel.contrail' in the playbook's collections
      jpclipffel.contrail.contrail:
        # ...
```

## Custom components

This collection provides two customs Ansible modules:

| Component                     | Component type            | Description                                 | Documentation                                                         |
|-------------------------------|---------------------------|---------------------------------------------|-----------------------------------------------------------------------|
| `plugins/modules/contrail.py` | Ansible module            | Ansible module for Juniper Contrail         | [User](docs/contrail-module.md)<br>[Dev](docs/contrail-module-dev.md) |
| `plugins/httpapi/contrail.py` | Ansible connection plugin | Ansible HTTPApi plugin for Juniper Contrail | [Dev](docs/contrail-plugin-dev.md)                                    |

## Supported resources

This collection supports the following Contrail resources:

| Resource name             | Resource type               | Resource class            | Comments                              |
|---------------------------|-----------------------------|---------------------------|---------------------------------------|
| Logical Router            | `logical-router`            | `LogicalRouter`           | -                                     |
| Virtual Machine Interface | `virtual-machine-interface` | `VirtualMachineInterface` | Aliased by `virtual-port`             |
| Virtual Networks          | `virtual-network`           | `VirtualNetwork`          | -                                     |
| Virtual Port              | `virtual-port`              | `VirtualMachineInterface` | Alias of `virtual-machine-interface`  |
| Virtual Port Group        | `virtual-port-group`        | `VirtualPortGroup`        | -                                     |

> Adding support for a new resource type is easy: [module dev documentation](docs/contrail-module-dev.md)

## To do

The Ansible module and plugin are still a work in progress.

- [x] Basic connection to Contrail from Ansible
- [ ] Authentication support
- [x] State support: `query`
- [x] State support: `present` (resource creation)
- [x] State support: `present` (resource update)
- [x] State support: `absent`
- [x] Module documentation for users
- [x] Module documentation for dev
- [ ] Plugin documentation for dev
