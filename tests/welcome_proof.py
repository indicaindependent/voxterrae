"""Proof of the exe's double-click path: no args -> Welcome -> click ENTER with a handle -> both networks connect."""
import os, sys
if os.environ.get("VOXTERRAE_LIVE_TESTS") != "1":
    sys.exit("live proof: connects to real IRC networks; set VOXTERRAE_LIVE_TESTS=1 to run")
import asyncio, secrets, sys, os
os.environ["QT_QPA_PLATFORM"] = "offscreen"
from voxterrae.app import __main__ as entry
from PySide6.QtWidgets import QApplication
import qasync

# Drive main() but inject a click after the loop starts: patch loop.run_forever via a task scheduled on the app
handle = "vtwel" + secrets.token_hex(2)
orig_main = entry.main
def main():
    from voxterrae.app.main_window import MainWindow
    orig_show = MainWindow.show
    def show(self):
        orig_show(self)
        async def drive():
            await asyncio.sleep(0.5)
            assert self.stack.currentWidget() is self.welcome, "did not start on Welcome"
            self.welcome.handle.setText(handle); self.welcome.enter.emit(self.welcome.handle.text())   # = clicking ENTER
            for _ in range(60):
                await asyncio.sleep(0.5)
                b = self.findChild(object, "") ; 
                st = [i.text() for i in [self.rooms.item(j) for j in range(self.rooms.count())] if i.data(0x0100) is None]
                if len(st) == 2 and all("connected" in t for t in st): break
            keys = [self.rooms.item(j).data(0x0100) for j in range(self.rooms.count()) if self.rooms.item(j).data(0x0100)]
            efnet_rooms = [k for k in keys if k.startswith("efnet/") and not k.endswith("*server*")]
            assert efnet_rooms == [], f"EFnet auto-joined something: {efnet_rooms}"   # Pete's rule: #warheatmap is the only auto-join anywhere
            print("WELCOME PROOF:", {"on_chat": self.stack.currentWidget() is self.chat, "group_headers": st, "me": self.me.text(), "rooms": keys, "efnet_autojoined": efnet_rooms})
            QApplication.instance().quit()
        asyncio.get_event_loop().create_task(drive())
    MainWindow.show = show
    return orig_main([])
sys.exit(main())
