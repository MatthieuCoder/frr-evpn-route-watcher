import json
import ipaddress
import subprocess
import re
import time

def get_frr_vrfs():
    """Gets the list of vrf VNIs configured in FRR"""
    process = subprocess.run(["vtysh", "-c", "show vrf vni json"], capture_output=True)
    return json.loads(process.stdout)["vrfs"]

def get_frr_evpn_info():
    """Lists all the routes learned via evpn"""
    process = subprocess.run(
        ["vtysh", "-c", "show ip bgp l2vpn evpn json"], capture_output=True
    )
    return json.loads(process.stdout)

def add_route_vrf(ip, vrf):
    """Add a route using the ip route command"""
    subprocess.run(
        ["ip", "route", "add", str(ip), "dev", vrf, "metric", "0"],
    )

def remove_route_vrf(ip):
    subprocess.run(["ip", "route", "del", str(ip)])

def currently_routed(vrfs_names):
    process = subprocess.run(["ip", "route"], capture_output=True, text=True)
    routed_ips = []
    for route in process.stdout.splitlines():
        parts = route.split(" ")
        if len(parts) == 6:
            addr, dev, vrf, scope, link = (
                parts[0],
                parts[1],
                parts[2],
                parts[3],
                parts[4],
            )
            addr = parse_ip(addr)
            if (
                addr != None
                and dev == "dev"
                and vrf in vrfs_names
                and scope == "scope"
                and link == "link"
            ):
                routed_ips.append(addr)
    return routed_ips

def parse_ip(str):
    try:
        return ipaddress.ip_network(str)
    except ValueError:
        return False

def get_vrfs():
    return {str(vrf["vni"]): vrf["vrf"] for vrf in get_frr_vrfs()}

def resolve_routes():
    json = get_frr_evpn_info()
    vrfs = get_vrfs()

    # The local router-id to search for IPs in the evpn routes information
    localRouterId = json["bgpLocalRouterId"]
    localAS = json["localAS"]

    currentlyRouted = currently_routed([vrfs[vrf] for vrf in vrfs])

    for jsonKey in json:
        rd = jsonKey.split(":")
        if len(rd) == 2:
            peer, _ = rd

            if parse_ip(peer) and peer == localRouterId:
                rdObject = json[jsonKey]
                for route in rdObject:
                    matches = re.findall(r"(?:\[([^\]]*)\]:?)", route)
                    if len(matches) == 6:
                        route_type = matches[0]
                        if route_type == "2":
                            ip = parse_ip(matches[5])

                            if ip != None and not ip.is_link_local:
                                extendedCommunities = rdObject[route]["paths"][0][
                                    "extendedCommunity"
                                ]["string"]
                                rts = re.finditer(
                                    f"RT:{localAS}:(\d+)", extendedCommunities
                                )

                                # For all the matches we have in the extentendCommunity value
                                for rt in rts:
                                    vni = rt.group(1)
                                    if vni in vrfs:
                                        vrf = vrfs[vni]
                                        if ip in currentlyRouted:
                                            currentlyRouted.remove(ip)
                                            break
                                        
                                        print(
                                            f"wanting to add route {ip} to {vrf} ({vni}) vrf"
                                        )
                                        add_route_vrf(ip, vrf)
                                        

                                        break
    for remove in currentlyRouted:
        print(f"removing route for {remove}")
        remove_route_vrf(remove)

resolve_routes()