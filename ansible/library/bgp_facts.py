#!/usr/bin/python

DOCUMENTATION = '''
module:         bgp_facts
version_added:  "2.0"
author:         John Arnold (johnar@microsoft.com)
short_description: Retrieve BGP neighbor information from Quagga
description:
    - Retrieve BGP neighbor information from Quagga, using the VTYSH command line
    - Retrieved facts will be inserted into the 'bgp_neighbors' key
'''

EXAMPLES = '''
- name: Get BGP neighbor information
  bgp_facts:
'''

# Example of the source data
'''
BGP neighbor is 10.0.0.61, remote AS 64015, local AS 65100, external link
 Description: ARISTA15T0
  BGP version 4, remote router ID 0.0.0.0
  BGP state = Active
  Last read 6d13h16m, hold time is 180, keepalive interval is 60 seconds
  Message statistics:
    Inq depth is 0
    Outq depth is 0
                         Sent       Rcvd
    Opens:                  1          1
    Notifications:          0          0
    Updates:             6595          3
    Keepalives:           949        948
    Route Refresh:          0          0
    Capability:             0          0
    Total:               7545        952
  Minimum time between advertisement runs is 30 seconds

 For address family: IPv4 Unicast
  Community attribute sent to this neighbor(both)
  0 accepted prefixes

  Connections established 1; dropped 1
  Last reset 6d13h15m, due to
Next connect timer due in 31 seconds
Read thread: off  Write thread: off
'''


class BgpModule(object):
    def __init__(self):
        self.module = AnsibleModule(
            argument_spec=dict(
            ),
            supports_check_mode=True)

        self.out = None
        self.facts = {}

        return

    def run(self):
        """
            Main method of the class
        """
        self.collect_data('summary')
        self.parse_summary()
        self.collect_data('neighbor')
        self.parse_neighbors()
        self.module.exit_json(ansible_facts=self.facts)

    def collect_data(self, command_str):
        """
            Collect bgp information by reading output of 'vtysh' command line tool
        """
        try:
            rc, self.out, err = self.module.run_command('vtysh -c "show ip bgp ' + command_str + '"',
                                                        executable='/bin/bash', use_unsafe_shell=True)
        except Exception as e:
            self.module.fail_json(msg=str(e))

        if rc != 0:
            self.module.fail_json(msg="Command failed rc=%d, out=%s, err=%s" %
                                      (rc, self.out, err))

        return

    def parse_summary(self):
        regex_asn = re.compile(r'.*local AS number (\d+).*')
        if regex_asn.match(self.out):
            self.facts['bgp_localasn'] = regex_asn.match(self.out).group(1)

    def parse_neighbors(self):

        regex_ip = re.compile(r'^BGP neighbor is \*?(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}|[0-9a-fA-F:]+)')
        regex_remote_as = re.compile(r'.*remote AS (\d+)')
        regex_local_as = re.compile(r'.*local AS (\d+)')
        regex_desc = re.compile(r'.*Description: (.*)')
        regex_stats = re.compile(r'.*(Opens|Notifications|Updates|Keepalives|Route Refresh|Capability|Total):.*')
        regex_state = re.compile(r'.*BGP state = (\w+)')
        regex_mrai = re.compile(r'.*Minimum time between advertisement runs is (\d{1,4})')
        regex_accepted = re.compile(r'.*(\d+) accepted prefixes')
        regex_conn_est = re.compile(r'.*Connections established (\d+)')
        regex_conn_dropped = re.compile(r'.*Connections established \d+; dropped (\d+)')
        regex_routerid = re.compile(r'.*remote router ID (\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})')
        regex_peer_group = re.compile(r'.*Member of peer-group (.*) for session parameters')
        regex_subnet =  re.compile(r'.*subnet range group: (\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\/\d{1,2})')
        regex_cap_gr = re.compile(r'.*Graceful Restart Capabilty: (\w+)')
        regex_cap_gr_peer_restart_time = re.compile(r'.*Remote Restart timer is (\d+)')
        regex_cap_gr_peer_af_ip4 = re.compile(r'.*IPv4 Unicast\((.*)\)')
        regex_cap_gr_peer_af_ip6 = re.compile(r'.*IPv6 Unicast\((.*)\)')

        neighbors = {}

        try:
            split_output = self.out.split("BGP neighbor is")

            for n in split_output:

                # ignore empty rows
                if 'BGP' in n:
                    neighbor = {}
                    capabilities = {}
                    message_stats = {}
                    n = "BGP neighbor is" + n
                    lines = n.splitlines()
                    neighbor['accepted prefixes'] = 0

                    for line in lines:
                        if regex_ip.match(line): neighbor_ip = regex_ip.match(line).group(1).lower()
                        if regex_remote_as.match(line): neighbor['remote AS'] = int(regex_remote_as.match(line).group(1))
                        if regex_local_as.match(line): neighbor['local AS'] = int(regex_local_as.match(line).group(1))
                        if regex_desc.match(line): neighbor['description'] = regex_desc.match(line).group(1)
                        if regex_state.match(line): neighbor['state'] = regex_state.match(line).group(1).lower()
                        if regex_mrai.match(line): neighbor['mrai'] = int(regex_mrai.match(line).group(1))
                        if regex_accepted.match(line): neighbor['accepted prefixes'] += int(regex_accepted.match(line).group(1))
                        if regex_conn_est.match(line): neighbor['connections established'] = int(regex_conn_est.match(line).group(1))
                        if regex_conn_dropped.match(line): neighbor['connections dropped'] = int(regex_conn_dropped.match(line).group(1))
                        if regex_routerid.match(line): neighbor['remote routerid'] = regex_routerid.match(line).group(1)
                        if regex_peer_group.match(line): neighbor['peer group'] = regex_peer_group.match(line).group(1)
                        if regex_subnet.match(line): neighbor['subnet'] = regex_subnet.match(line).group(1)

                        if regex_cap_gr.match(line): capabilities['graceful restart'] = regex_cap_gr.match(line).group(1).lower()
                        if regex_cap_gr_peer_restart_time.match(line): capabilities['peer restart timer'] = int(regex_cap_gr_peer_restart_time.match(line).group(1))
                        if regex_cap_gr_peer_af_ip4.match(line): capabilities['peer af ipv4 unicast'] = regex_cap_gr_peer_af_ip4.match(line).group(1).lower()
                        if regex_cap_gr_peer_af_ip6.match(line): capabilities['peer af ipv6 unicast'] = regex_cap_gr_peer_af_ip6.match(line).group(1).lower()

                        if regex_stats.match(line):
                            key, values = line.split(':')
                            key = key.lstrip()
                            sent, rcvd = values.split()
                            value_dict = {}
                            value_dict['sent'] = int(sent)
                            value_dict['rcvd'] = int(rcvd)
                            message_stats[key] = value_dict

                        if capabilities:
                            neighbor['capabilities'] = capabilities

                        if message_stats:
                            neighbor['message statistics'] = message_stats

                    neighbors[neighbor_ip] = neighbor

        except Exception as e:
            self.module.fail_json(msg=str(e))

        self.facts['bgp_neighbors'] = neighbors
        return


def main():
    bgp = BgpModule()
    bgp.run()

    return


from ansible.module_utils.basic import *
if __name__ == "__main__":
    main()
