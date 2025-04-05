#!/usr/bin/env python3
import json
import ipaddress
import subprocess

def vtysh(cmd):
    print(f"@: vtysh -c {cmd}")
    return subprocess.run([
        "vtysh",
        "-c",
        cmd
    ], capture_output=True).stdout

def get_frr_vrfs():
    """
    gets the list of VNIs declared in the evpn config
    """
    print("I: Listing evpn VNIs")
    show_evpn_vni = vtysh("sh evpn vni json")
    return json.loads(show_evpn_vni)

def get_frr_arp_cache(vni):
    """
    gets the list of atp-cache entries in the given VNI
    """
    print(f"I: Listing evpn arp-cache for VNI {vni}")
    show_evpn_arp_cache = vtysh(f"sh evpn arp-cache vni {vni} json")
    return json.loads(show_evpn_arp_cache)

def get_current_routes():
    """
    gets the list of routes currently applied using frr-evpn-route-watcher
    """
    command = [
        "ip",
        "route",
        "show",
        "proto",
        "frr-evpn-route-watcher"
    ]
    process4 = subprocess.run(command, capture_output=True)
    process6 = subprocess.run(command + ["-6"], capture_output=True)

    routes = process4.stdout.splitlines() + process6.stdout.splitlines()
    out = {}

    for route in routes:
        # <ip> dev <vrf> scope link
        parts = route.split(" ")
        if len(parts) == 5:
            valid = parts[1] == "dev" \
                and parts[3] == "scope" \
                and parts[4] == "link"
            if valid:
                ipraw = parts[0]
                vrf = parts[2]
                ip = ipaddress.ip_address(ipraw)
                out[ip] = vrf
                print(f"D: Found existing route for {ip}")
    return out

def add_route_vrf(ip, vrf):
    """
    Add a route using the ip route command that points to a vrf interface
    """
    print(f"I: Adding route for {ip} -> {vrf}")
    subprocess.run([
            "ip",
            "route",
            "add",
            str(ip),
            "dev",
            vrf,
            "proto",
            "frr-evpn-route-watcher"
    ])

def remove_route_vrf(ip):
    """removes a route to a given ip"""
    print(f"I: Removing route to {ip}")
    subprocess.run(["ip", "route", "del", str(ip)])

def main():
    print("frr-evpn-route-watcher by Matthieu P. <m@mpgn.dev>")
    # Get all the L2 VRFs
    vrfs = [
        vrf 
        for vrf in get_frr_vrfs()
        if vrf['type'] == "L2"
    ]
    # get all the current routes
    to_remove = get_current_routes()

    for vrf in vrfs:
        vrfName = vrf['tenantVrf']
        vni = vrf['vni']
        arp_cache = get_frr_arp_cache(vni)

        for entry in arp_cache.keys():
            local = type({}) == type(arp_cache[entry]) and \
                arp_cache[entry]['type'] == 'local'
            
            if local:
                ip = ipaddress.ip_address(entry)
                present = ip in to_remove

                # if the route already exists
                if present:
                    # if the route points to the correct VRF interface
                    valid = to_remove[ip] == vrfName

                    # if it's not, we delete the old route and
                    # create a new correct one.
                    if not valid:
                        remove_route_vrf(ip)
                        add_route_vrf(ip, vrfName)
                else:
                    # if the route doesn't exist, we simply create it
                    add_route_vrf(ip, vrfName)
                
                # since the route muse say we remove it from the to_remove list
                to_remove.pop(ip)
    
    for remove in to_remove.keys():
        remove_route_vrf(remove)

if __name__ == "__main__":
    main()
