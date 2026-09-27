"""Autojoin law (Pete, Sep 20 2026; amended Sep 26 2026 when the HOME network was retired):
VoxTerrae auto-joins exactly ONE room anywhere: #warheatmap on EFnet. No other network is built in,
and no other channel name may appear in the built-in configuration."""
from voxterrae.irc.networks import BUILTIN, EFNET

def test_only_efnet_is_built_in():
    assert [n.key for n in BUILTIN] == ["efnet"], f"BUILTIN must be EFnet only, got {[n.key for n in BUILTIN]!r}"

def test_efnet_autojoins_only_warheatmap():
    assert EFNET.autojoin == ["#warheatmap"], f"EFnet must auto-join exactly #warheatmap, got {EFNET.autojoin!r}"
    assert EFNET.home_channel == "#warheatmap"

def test_no_other_channel_names_in_builtins():
    for net in BUILTIN:
        for ch in net.autojoin:
            assert ch.lower() == "#warheatmap", f"{net.key} carries a foreign channel {ch!r}"

def test_no_home_network_remains():
    import voxterrae.irc.networks as n
    assert not hasattr(n, "HOME"), "HOME network object must be gone (retired 2026-09-26)"
    for net in BUILTIN:
        for s in net.servers: assert "warheatmap.app" not in s.host
