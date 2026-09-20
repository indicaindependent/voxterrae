"""Pete's channel law, asserted offline so a plain `pytest` enforces it.

Standing instruction (Sep 20 2026): #warheatmap on HOME is the ONLY room any network
auto-joins, on any server, ever. Before this file existed that rule was checked only by
live-gated code -- and test_live_dual_network.py overrides EFNET's autojoin with
replace(EFNET, autojoin=[]) before connecting, so it could not have caught a bad default
even when run. A rule with no test that runs by default is a rule waiting to regress.
"""
from voxterrae.irc.networks import EFNET, HOME


def test_home_autojoins_only_warheatmap():
    assert HOME.autojoin == ["#warheatmap"], (
        f"HOME must auto-join exactly #warheatmap, got {HOME.autojoin!r}"
    )


def test_efnet_autojoins_nothing():
    assert EFNET.autojoin == [], (
        f"EFnet must auto-join NOTHING; got {EFNET.autojoin!r}"
    )
    assert not EFNET.home_channel.startswith("#"), (
        f"EFnet home_channel must be a network buffer, not a room; got {EFNET.home_channel!r}"
    )


def test_no_network_autojoins_any_other_room():
    for net in (HOME, EFNET):
        for room in net.autojoin:
            assert room == "#warheatmap", (
                f"{net.key if hasattr(net,'key') else net}: unexpected autojoin room {room!r}"
            )
