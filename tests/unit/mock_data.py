import uuid

from mrack.config import ProvisioningConfig
from mrack.dbdrivers.file import FileDBDriver
from mrack.host import STATUS_ACTIVE, Host
from mrack.transformers.beaker import BeakerTransformer


class MockedBeakerTransformer(BeakerTransformer):
    """Mock Beaker transformer."""

    async def init_provider(self):
        """Override the init_provider to do nothing."""
        pass


class MockProvider:
    """Mock provider for working in DB."""

    def __init__(self, name):
        self.name = name


def create_metadata(ipaservers, ipaclients, ads):
    """
    Generate example metadata, using FreeIPA as example project.
    """

    domain_name = "example.test"
    addomain_name = "adexample.test"
    fedora = "fedora-31"

    ipa_hosts = []
    ipadomain = {
        "name": domain_name,
        "type": "ipa",
        "hosts": ipa_hosts,
    }

    for i in range(ipaservers):
        host = {
            "name": f"ipaserver{i}@{domain_name}",
            "os": fedora,
            "role": "ipaserver",
            "groups": ["ipaserver"],
        }
        ipa_hosts.append(host)

    for i in range(ipaclients):
        host = {
            "name": f"ipaclient{i}@{domain_name}",
            "os": fedora,
            "role": "ipaclient",
            "groups": ["ipaclient"],
        }
        ipa_hosts.append(host)

    ad_hosts = []
    addomain = {
        "name": addomain_name,
        "type": "ad",
        "hosts": ad_hosts,
    }

    for i in range(ads):
        host = {
            "name": f"ad{i}@{addomain_name}",
            "os": "windows",
            "role": "ad",
            "groups": ["win-2019"],
        }
        ad_hosts.append(host)

    domains = []

    if ipaservers or ipaclients:
        domains.append(ipadomain)
    if ads:
        domains.append(addomain)

    return {
        "domains": domains,
    }


def metadata_extra():
    hosts = [
        {
            "name": "srv1.example.test",
            "os": "windows-2019",
            "role": "ad",
            "groups": ["windows"],
            "meta_readonly_dc": "yes",
            "meta_something_else": "val",
        },
        {
            "name": "srv2.example.test",
            "os": "fedora",
            "role": "master",
            "groups": ["ipaserver"],
            "meta_readonly_dc": "no",
            "meta_os": "fedora-32",
        },
    ]
    return {
        "domains": [
            {
                "name": "example.test",
                "type": "mixed",
                "hosts": hosts,
            }
        ]
    }


def get_ip(index=0):
    """Get IPv4 IP from 192.168.0/24 network."""
    return f"192.168.0.{index+1}"


def create_db_host(
    hostname,
    operating_system="fedora",
    group=None,
    index=0,
    status=STATUS_ACTIVE,
    username=None,
    password=None,
    provider="openstack",
    meta_extra=None,
):
    """Create Host object based on minimal info."""

    return Host(
        MockProvider(provider),
        uuid.uuid4(),
        hostname,
        operating_system,
        group,
        [get_ip(index)],
        status,
        {},
        meta_extra=meta_extra,
        username=username,
        password=password,
        error_obj=None,
    )


def create_db(hostnames, provider="openstack", meta_extra=None):
    """Create artificial DB based on hostnames."""
    db = FileDBDriver("mock_path")
    db.save_on_change = False  # to prevent attempt to save when adding hosts

    for index, hostname in enumerate(hostnames):
        host = create_db_host(hostname, index, provider=provider, meta_extra=meta_extra)
        db.add_hosts([host])
    return db


def get_db_from_metadata(metadata, provider="openstack", host_extra=None):
    """Create DB from metadata for testing."""
    hostnames = []
    for domain in metadata.get("domains", []):
        for host in domain.get("hosts", []):
            hostnames.append(host["name"])

    db = create_db(hostnames, meta_extra=host_extra)
    return db


def common_inventory_layout():
    """Get common inventory layour for testing FreeIPA project."""
    return {
        "all": {
            "children": {
                "ipa": {"children": {"ipaserver": {}, "ipaclient": {}}},
                "linux": {"children": {"ipa": {}, "sssd": {}}},
                "windows": {"children": {"ad": {}, "client": {}}},
            }
        }
    }


def provisioning_config(inventory_layout=None):
    """Get basic provisioning config for testing."""
    cfg = {
        "ssh_key_filename": "config/id_rsa",
        "beaker": {
            "strategy": "retry",
            "max_retry": 2,
            "distros": {
                "c9s": "CentOS-Stream-9%",
                "fedora-36": "Fedora-36%",
                "rhel-8.6": "RHEL-8.6%",
                "fedora-latest": "Fedora-36%",
            },
            "distro_tags": {
                "CentOS-Stream-9%": [
                    "RC-01",
                ]
            },
            "distro_variants": {
                "default": "BaseOS",
                "CentOS-Stream-9%": "BaseOS",
                "Fedora-36%": "Server",
            },
            "reserve_duration": 86400,
            "kickstart_metadata": {
                "default": "PROV_CONF_DEFAULT",
                "rhel-8.6": "PROV_CONF_RHEL86_KS_META",
                "c9s": "PROV_CONF_CENTOS_KS_META",
            },
            "timeout": 120,
        },
        "users": {
            "fedora-30": "fedora",
            "fedora-31": "fedora",
            "rhel-8.2": "cloud-user",
            "rhel-8.6": "cloud-user",
            "win-2019": "Administrator",
            "default": "cloud-user",
        },
        "python": {
            "fedora-30": "/usr/bin/python3",
            "fedora-31": "/usr/bin/python3",
            "rhel-8.2": "/usr/libexec/platform-python",
            "rhel-8.6": "/usr/libexec/platform-python",
            "default": "/usr/bin/python3",
        },
    }
    if inventory_layout:
        cfg["inventory_layout"] = inventory_layout

    config = ProvisioningConfig(cfg)
    return config
