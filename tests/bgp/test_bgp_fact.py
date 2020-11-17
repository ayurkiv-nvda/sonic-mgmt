import pytest

pytestmark = [
    pytest.mark.topology('any'),
    pytest.mark.device_type('vs')
]

def test_bgp_facts(duthosts, enum_dut_hostname, enum_asic_index):
    """compare the bgp facts between observed states and target state"""

    duthost = duthosts[enum_dut_hostname]

    # Check if duthost is 'supervisor' card, and skip the test if dealing with supervisor card.
    if duthosts.is_supervisor_node(duthost):
        pytest.skip("bgp_facts not valid on supervisor card '%s'" % enum_dut_hostname)

    bgp_facts = duthost.bgp_facts(instance_id=enum_asic_index)['ansible_facts']
    namespace = duthost.get_namespace_from_asic_id(enum_asic_index)
    config_facts = duthost.config_facts(host=duthost.hostname, source="running",namespace=namespace)['ansible_facts']

    for k, v in bgp_facts['bgp_neighbors'].items():
        # Verify bgp sessions are established
        assert v['state'] == 'established'
        # Verify local ASNs in bgp sessions
        assert v['local AS'] == int(config_facts['DEVICE_METADATA']['localhost']['bgp_asn'].decode("utf-8"))
        # Check bgpmon functionality by validate STATE DB contains this neighbor as well
        state_fact = duthost.shell('sonic-db-cli STATE_DB HGET "NEIGH_STATE_TABLE|{}" "state"'.format(k), module_ignore_errors=False)['stdout_lines']
        assert state_fact[0] == "Established"

    for k, v in config_facts['BGP_NEIGHBOR'].items():
        # Compare the bgp neighbors name with config db bgp neighbors name
        assert v['name'] == bgp_facts['bgp_neighbors'][k]['description']
        # Compare the bgp neighbors ASN with config db
        assert int(v['asn'].decode("utf-8")) == bgp_facts['bgp_neighbors'][k]['remote AS']
