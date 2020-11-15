import pytest
import demistomock as demisto

integration_params = {
    'port': '443',
    'vsys': 'vsys1',
    'server': 'https://1.1.1.1',
    'key': 'thisisabogusAPIKEY!',
}

mock_demisto_args = {
    'threat_id': "11111",
    'vulnerability_profile': "mock_vuln_profile",
    'dest_ip': "10.20.20.20",
}


@pytest.fixture(autouse=True)
def set_params(mocker):
    mocker.patch.object(demisto, 'params', return_value=integration_params)
    mocker.patch.object(demisto, 'args', return_value=mock_demisto_args)


@pytest.fixture
def patched_requests_mocker(requests_mock):
    """
    This function mocks various PANOS API responses so we can accurately test the instance
    """
    base_url = "{}:{}/api/".format(integration_params['server'], integration_params['port'])
    # Version information
    mock_version_xml = """
    <response status = "success">
        <result>
            <sw-version>9.0.6</sw-version>
            <multi-vsys>off</multi-vsys>
            <model>Panorama</model>
            <serial>FAKESERIALNUMBER</serial>
        </result>
    </response>
    """
    version_path = "{}{}{}".format(base_url, "?type=version&key=", integration_params['key'])
    requests_mock.get(version_path, text=mock_version_xml, status_code=200)
    mock_response_xml = """
    <response status="success" code="20">
    <msg>command succeeded</msg>
    </response>
    """
    requests_mock.post(base_url, text=mock_response_xml, status_code=200)
    # Mock a show routing route request
    mock_route_xml = """
    <response status="success">
    <result>
        <flags>flags: A:active</flags>
        <entry>
            <virtual-router>CORE</virtual-router>
            <destination>0.0.0.0/0</destination>
            <nexthop>10.0.0.1</nexthop>
            <metric>100</metric>
            <flags>A O2  </flags>
            <age>4072068</age>
            <interface>ae1.1</interface>
            <route-table>unicast</route-table>
        </entry>
        <entry>
            <virtual-router>CORE</virtual-router>
            <destination>10.10.0.0/16</destination>
            <nexthop>192.168.1.1</nexthop>
            <metric>130</metric>
            <flags>A O1  </flags>
            <age>4072068</age>
            <interface>ae1.2</interface>
            <route-table>unicast</route-table>
        </entry>
        <entry>
            <virtual-router>CORE</virtual-router>
            <destination>10.0.0.0/8</destination>
            <nexthop>192.168.2.1</nexthop>
            <metric>130</metric>
            <flags>A O1  </flags>
            <age>4072068</age>
            <interface>ae1.3</interface>
            <route-table>unicast</route-table>
        </entry>
        <entry>
            <virtual-router>CORE</virtual-router>
            <destination>2000::/16</destination>
            <nexthop>fe80::1234</nexthop>
            <metric>130</metric>
            <flags>A O1  </flags>
            <age>4172303</age>
            <interface>ae1.4</interface>
            <route-table>unicast</route-table>
        </entry>
    </result>
    </response>
    """
    route_path = "{}{}{}{}".format(base_url, "?type=op&key=", integration_params['key'],
                                   "&cmd=<show><routing><route></route></routing></show>")
    requests_mock.get(route_path, text=mock_route_xml, status_code=200)

    mock_interface_xml = """
    <response status="success">
    <result>
        <ifnet>
            <entry>
                <name>ethernet1/24</name>
                <zone>MONITOR</zone>
                <fwd>tap</fwd>
                <vsys>2</vsys>
                <dyn-addr/>
                <addr6/>
                <tag>0</tag>
                <ip>N/A</ip>
                <id>87</id>
                <addr/>
            </entry>
            <entry>
                <name>ethernet2/1</name>
                <zone/>
                <fwd>logfwd</fwd>
                <vsys>0</vsys>
                <dyn-addr/>
                <addr6/>
                <tag>0</tag>
                <ip>N/A</ip>
                <id>128</id>
                <addr/>
            </entry>
            <entry>
                <name>ae1.1</name>
                <zone>OUTSIDE</zone>
                <fwd>vr:CORE</fwd>
                <dyn-addr/>
                <addr6/>
                <tag>3</tag>
                <ip>10.10.10.10</ip>
                <id>999</id>
                <addr/>
            </entry>
            <entry>
                <name>ae1.2</name>
                <zone>INSIDE</zone>
                <fwd>vr:CORE</fwd>
                <dyn-addr/>
                <addr6/>
                <tag>34</tag>
                <ip>192.168.1.2</ip>
                <id>998</id>
                <addr/>
            </entry>
            <entry>
                <name>ae1.3</name>
                <zone>DMZ</zone>
                <fwd>vr:CORE</fwd>
                <dyn-addr/>
                <addr6/>
                <tag>34</tag>
                <ip>10.10.10.10</ip>
                <id>997</id>
                <addr/>
            </entry>
        </ifnet>
    </result>
    </response>
    """
    interface_path = "{}{}{}{}".format(base_url, "?type=op&key=", integration_params['key'],
                                       "&cmd=<show><interface>all</interface></show>")
    requests_mock.get(interface_path, text=mock_interface_xml, status_code=200)

    mock_test_routing = """
    <response status="success">
    <result>
        <nh>ip</nh>
        <src>192.168.2.1</src>
        <ip>10.10.10.10</ip>
        <metric>10</metric>
        <interface>ae1.3</interface>
        <dp>s2dp0</dp>
    </result>
    </response>
    """
    test_route_path = "{}{}{}{}".format(base_url, "?type=op&key=", integration_params['key'],
                                        "&cmd=<test><routing><fib-lookup><ip>10.20.20.20</ip>"
                                        + "<virtual-router>default</virtual-router>"
                                        + "</fib-lookup></routing></test>")
    requests_mock.get(test_route_path, text=mock_test_routing, status_code=200)
    return requests_mock


def test_panorama_get_interfaces(patched_requests_mocker):
    """
    Given the interface XML from <show><interface>all, expects 5 interfaces to be returned
    """
    from Panorama import panorama_get_interfaces
    import Panorama
    Panorama.URL = 'https://1.1.1.1:443/api/'
    Panorama.API_KEY = 'thisisabogusAPIKEY!'
    r = panorama_get_interfaces()
    assert len(r['response']['result']['ifnet']['entry']) == 5


def test_panorama_route_lookup(patched_requests_mocker):
    """
    Test the route lookup
    """
    from Panorama import panorama_route_lookup_command, initialize_instance
    initialize_instance(mock_demisto_args, integration_params)
    r = panorama_route_lookup_command()
    assert r['interface'] == 'ae1.3'


def test_panorama_route_lookup_bad(patched_requests_mocker, mocker):
    """
    Test a route lookup where there is no resolved next hop
    Should raise DemistoException
    """
    from Panorama import panorama_route_lookup_command, DemistoException

    dargs = {
        "dest_ip": "8.8.8.8"
    }
    mocker.patch.object(demisto, 'args', return_value=dargs)

    mock_test_routing_noresult = """
    <response status="success">
    <result>
        <dp>s2dp0</dp>
    </result>
    </response>
    """
    base_url = "{}:{}/api/".format(integration_params['server'], integration_params['port'])
    test_route_path = "{}{}{}{}".format(base_url, "?type=op&key=", integration_params['key'],
                                        "&cmd=<test><routing><fib-lookup><ip>8.8.8.8</ip>"
                                        + "<virtual-router>default</virtual-router>"
                                        + "</fib-lookup></routing></test>")
    patched_requests_mocker.get(test_route_path, text=mock_test_routing_noresult, status_code=200)

    with pytest.raises(DemistoException):
        panorama_route_lookup_command()


def test_panorama_zone_lookup(patched_requests_mocker):
    from Panorama import panorama_zone_lookup_command
    r = panorama_zone_lookup_command()
    assert r['zone'] == 'DMZ'


def test_panoram_get_os_version(patched_requests_mocker):
    from Panorama import get_pan_os_version
    import Panorama
    Panorama.URL = 'https://1.1.1.1:443/api/'
    Panorama.API_KEY = 'thisisabogusAPIKEY!'
    r = get_pan_os_version()
    assert r == '9.0.6'


def test_panoram_override_vulnerability(patched_requests_mocker):
    from Panorama import panorama_override_vulnerability
    import Panorama
    Panorama.URL = 'https://1.1.1.1:443/api/'
    r = panorama_override_vulnerability(mock_demisto_args['threat_id'], mock_demisto_args['vulnerability_profile'],
                                        'reset-both')
    assert r['response']['@status'] == 'success'


def test_add_argument_list():
    from Panorama import add_argument_list
    list_argument = ["foo", "bar"]

    response_with_member = add_argument_list(list_argument, "test", True)
    expected_with_member = '<test><member>foo</member><member>bar</member></test>'
    assert response_with_member == expected_with_member

    response_with_member_field_name = add_argument_list(list_argument, "member", True)
    expected_with_member_field_name = '<member>foo</member><member>bar</member>'
    assert response_with_member_field_name == expected_with_member_field_name


def test_add_argument():
    from Panorama import add_argument
    argument = "foo"

    response_with_member = add_argument(argument, "test", True)
    expected_with_member = '<test><member>foo</member></test>'
    assert response_with_member == expected_with_member

    response_without_member = add_argument(argument, "test", False)
    expected_without_member = '<test>foo</test>'
    assert response_without_member == expected_without_member


def test_add_argument_yes_no():
    from Panorama import add_argument_yes_no
    arg = 'No'
    field = 'test'
    option = True

    response_option_true = add_argument_yes_no(arg, field, option)
    expected_option_true = '<option><test>no</test></option>'
    assert response_option_true == expected_option_true

    option = False
    response_option_false = add_argument_yes_no(arg, field, option)
    expected_option_false = '<test>no</test>'
    assert response_option_false == expected_option_false


def test_add_argument_target():
    from Panorama import add_argument_target
    response = add_argument_target('foo', 'bar')
    expected = '<bar><devices><entry name=\"foo\"/></devices></bar>'
    assert response == expected


def test_prettify_addresses_arr():
    from Panorama import prettify_addresses_arr
    addresses_arr = [{'@name': 'my_name', 'fqdn': 'a.com'},
                     {'@name': 'my_name2', 'fqdn': 'b.com'}]
    response = prettify_addresses_arr(addresses_arr)
    expected = [{'Name': 'my_name', 'FQDN': 'a.com'},
                {'Name': 'my_name2', 'FQDN': 'b.com'}]
    assert response == expected


def test_prettify_address():
    from Panorama import prettify_address
    address = {'@name': 'my_name', 'ip-netmask': '1.1.1.1', 'description': 'lala'}
    response = prettify_address(address)
    expected = {'Name': 'my_name', 'IP_Netmask': '1.1.1.1', 'Description': 'lala'}
    assert response == expected


def test_prettify_address_group():
    from Panorama import prettify_address_group
    address_group_static = {'@name': 'foo', 'static': {'member': 'address object'}}
    response_static = prettify_address_group(address_group_static)
    expected_address_group_static = {'Name': 'foo', 'Type': 'static', 'Addresses': 'address object'}
    assert response_static == expected_address_group_static

    address_group_dynamic = {'@name': 'foo', 'dynamic': {'filter': '1.1.1.1 and 2.2.2.2'}}
    response_dynamic = prettify_address_group(address_group_dynamic)
    expected_address_group_dynamic = {'Name': 'foo', 'Type': 'dynamic', 'Match': '1.1.1.1 and 2.2.2.2'}
    assert response_dynamic == expected_address_group_dynamic


def test_prettify_service():
    from Panorama import prettify_service
    service = {'@name': 'service_name', 'description': 'foo', 'protocol': {'tcp': {'port': '443'}}}
    response = prettify_service(service)
    expected = {'Name': 'service_name', 'Description': 'foo', 'Protocol': 'tcp', 'DestinationPort': '443'}
    assert response == expected


def test_prettify_service_group():
    from Panorama import prettify_service_group
    service_group = {'@name': 'sg', 'members': {'member': ['service1', 'service2']}}
    response = prettify_service_group(service_group)
    expected = {'Name': 'sg', 'Services': ['service1', 'service2']}
    assert response == expected


def test_prettify_custom_url_category():
    from Panorama import prettify_custom_url_category
    custom_url_category = {'@name': 'foo', 'list': {'member': ['a', 'b', 'c']}}
    response = prettify_custom_url_category(custom_url_category)
    expected = {'Name': 'foo', 'Sites': ['a', 'b', 'c']}
    assert response == expected


def test_prettify_edl():
    from Panorama import prettify_edl
    edl = {'@name': 'edl_name', 'type': {'my_type': {'url': 'abc.com', 'description': 'my_desc'}}}
    response = prettify_edl(edl)
    expected = {'Name': 'edl_name', 'Type': 'my_type', 'URL': 'abc.com', 'Description': 'my_desc'}
    assert response == expected


def test_build_traffic_logs_query():
    # (addr.src in 192.168.1.222) and (app eq netbios-dg) and (action eq allow) and (port.dst eq 138)
    from Panorama import build_traffic_logs_query
    source = '192.168.1.222'
    application = 'netbios-dg'
    action = 'allow'
    to_port = '138'
    response = build_traffic_logs_query(source, None, None, application, to_port, action)
    expected = '(addr.src in 192.168.1.222) and (app eq netbios-dg) and (port.dst eq 138) and (action eq allow)'
    assert response == expected


def test_prettify_traffic_logs():
    from Panorama import prettify_traffic_logs
    traffic_logs = [{'action': 'my_action1', 'category': 'my_category1', 'rule': 'my_rule1'},
                    {'action': 'my_action2', 'category': 'my_category2', 'rule': 'my_rule2'}]
    response = prettify_traffic_logs(traffic_logs)
    expected = [{'Action': 'my_action1', 'Category': 'my_category1', 'Rule': 'my_rule1'},
                {'Action': 'my_action2', 'Category': 'my_category2', 'Rule': 'my_rule2'}]
    assert response == expected


def test_prettify_logs():
    from Panorama import prettify_logs
    traffic_logs = [{'action': 'my_action1', 'category': 'my_category1', 'rule': 'my_rule1', 'natdport': '100',
                     'bytes': '12'},
                    {'action': 'my_action2', 'category': 'my_category2', 'rule': 'my_rule2', 'natdport': '101',
                     'bytes_sent': '11'}]
    response = prettify_logs(traffic_logs)
    expected = [{'Action': 'my_action1', 'CategoryOrVerdict': 'my_category1', 'Rule': 'my_rule1',
                 'NATDestinationPort': '100', 'Bytes': '12'},
                {'Action': 'my_action2', 'CategoryOrVerdict': 'my_category2', 'Rule': 'my_rule2',
                 'NATDestinationPort': '101', 'BytesSent': '11'}]
    assert response == expected


def test_build_policy_match_query():
    from Panorama import build_policy_match_query
    source = '1.1.1.1'
    destination = '6.7.8.9'
    protocol = '1'
    application = 'gmail-base'
    response = build_policy_match_query(application, None, destination, None, None, None, protocol, source)
    expected = '<test><security-policy-match><source>1.1.1.1</source><destination>6.7.8.9</destination>' \
               '<protocol>1</protocol><application>gmail-base</application></security-policy-match></test>'
    assert response == expected


def test_prettify_matching_rule():
    from Panorama import prettify_matching_rule
    matching_rule = {'action': 'my_action1', '@name': 'very_important_rule', 'source': '6.7.8.9', 'destination': 'any'}
    response = prettify_matching_rule(matching_rule)
    expected = {'Action': 'my_action1', 'Name': 'very_important_rule', 'Source': '6.7.8.9', 'Destination': 'any'}
    assert response == expected


def test_prettify_static_route():
    from Panorama import prettify_static_route
    static_route = {'@name': 'name1', 'destination': '1.2.3.4', 'metric': '10', 'nexthop': {'fqdn': 'demisto.com'}}
    virtual_router = 'my_virtual_router'
    response = prettify_static_route(static_route, virtual_router)
    expected = {'Name': 'name1', 'Destination': '1.2.3.4', 'Metric': 10,
                'NextHop': 'demisto.com', 'VirtualRouter': 'my_virtual_router'}
    assert response == expected


def test_validate_search_time():
    from Panorama import validate_search_time
    assert validate_search_time('2019/12/26')
    assert validate_search_time('2019/12/26 00:00:00')
    with pytest.raises(Exception):
        assert validate_search_time('219/12/26 00:00:00')
        assert validate_search_time('219/10/35')
