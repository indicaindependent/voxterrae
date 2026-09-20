"""Demo population for render proofs (no network). Every string here is fictional sample copy."""
from datetime import datetime, timedelta
from .timeline import Item
def populate(win):
    win.set_groups([("HOME", "● connected", ["home/#warheatmap", "home/#ukraine", "home/#hormuz", "home/#osint", "home/#help", "home/Axiom"]),
                    ("EFNET", "● connected", ["efnet/#phpnuke", "efnet/#wk", "efnet/#OGhomecoming", "efnet/#ComebacktoIRC", "efnet/#VetsHateDiscord"])])
    win.rooms.bump("home/#ukraine", 3); win.rooms.bump("home/#hormuz", 12); win.rooms.bump("home/Axiom", 1); win.rooms.bump("efnet/#phpnuke", 2)
    win.meta.setText("· 214 online · topic: the live map, discussed"); win.me.setText("● pete · online")
    t0 = datetime(2026, 9, 20, 2, 1)
    A = lambda n, s, txt, **k: win.add("home/#warheatmap", Item("msg", nick=n, text=txt, ts=t0 + timedelta(seconds=s), msgid=f"m{s}", **k))
    A("Axiom", 0, "New WarDesk thread is live: Ukraine, 8 posts on a 7-minute drip. Event #48812 pinned for this room.", is_bot=True)
    A("maya_k", 130, "is the Kharkiv strike on the map yet? my cousin sent a video an hour ago")
    A("Axiom", 150, "Yes: event #48812, Kharkiv, 01:40 ET, two verified sources. Card is in the rail on the right.", is_bot=True, reply_to_nick="maya_k", reply_to_text="is the Kharkiv strike on the map yet?")
    A("pete", 260, "Good catch. The desk picked it up at 02:00 too, it leads post 3 of the thread.", is_me=True, reactions={"👀": 3, "🔥": 1})
    A("pete", 300, "For anyone new: the map is warheatmap.app, this room is where we talk about what it shows.", is_me=True)
    win.add("home/#warheatmap", Item("read"))
    A("jonas.dk", 420, "first time here. how do you tell a verified event from a rumour on the map?", highlight=True)
    A("Axiom", 440, "Two independent sources with timestamps before it goes red. Amber means one source. Type /ask for the long version.", is_bot=True, reply_to_nick="jonas.dk", reply_to_text="how do you tell a verified event from a rumour")
    win.add("home/#warheatmap", Item("system", text="maya_k reacted 👍 to Axiom"))
    win.typing.setText("maya_k is typing…")
    win.set_reply(win.models["home/#warheatmap"].items[-3]); win.composer.setText("the amber marker is the single-source state, red means two")
    win.rail.set_events([("red", "Hormuz · tanker hit, 2 sources · 01:12"), ("blue", "Kharkiv · strike, verified · 01:40"), ("red", "Red Sea · UAV intercept · 00:58")])
    win.rail.set_members(["~ Axiom", "@ pete", "@ bumbo", "% maya_k", "+ jonas.dk", "  anna_r", "  kwame", "  lior_", "  +207 more"])
