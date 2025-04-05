# FRR evpn route watcher

This is a workaround of https://github.com/FRRouting/frr/issues/16161,
It periodically re-distributes routes from a given evpn L2 VNI to 
the kernel routing table in order to be advertised by frr using BGP
in the default VRF.