import allure
import logging
import pytest

from ngts.cli_wrappers.linux.linux_mac_clis import LinuxMacCli
from ngts.cli_wrappers.sonic.sonic_lldp_clis import SonicLldpCli

logger = logging.getLogger()


@pytest.mark.lldp
@pytest.mark.push_gate
@allure.title('test_lldp_infromation_remote_and_local')
def test_lldp_infromation_remote_and_local(topology_obj):
    """
    Run PushGate LLDP test case, test doing validation for LLDP peer port MAC address(we check only ports connected
    to hosts, without loopback ports
    """
    try:
        ports_for_validation = {'host_ports': ['ha-dut-1', 'ha-dut-2', 'hb-dut-1', 'hb-dut-2'],
                                'dut_ports': ['dut-ha-1', 'dut-ha-2', 'dut-hb-1', 'dut-hb-2']}

        dut_engine = topology_obj.players['dut']['engine']
        for host_dut_port in zip(ports_for_validation['host_ports'], ports_for_validation['dut_ports']):
            host_port_alias = host_dut_port[0]
            host_name_alias = host_port_alias.split('-')[0]
            host_engine = topology_obj.players[host_name_alias]['engine']
            host_port_mac = LinuxMacCli.get_mac_address_for_interface(host_engine, topology_obj.ports[host_port_alias])
            dut_port = topology_obj.ports[host_dut_port[1]]
            with allure.step('Checking peer MAC address via LLDP in interface {}'.format(dut_port)):
                lldp_info = SonicLldpCli.parse_lldp_info_for_specific_interface(dut_engine, dut_port)
                logger.info('Checking that peer device mac address in LLDP output')
                assert host_port_mac in lldp_info['Chassis']['ChassisID'], \
                    '{} was not found in {}'.format(host_port_mac, lldp_info)

    except Exception as err:
        raise AssertionError(err)
