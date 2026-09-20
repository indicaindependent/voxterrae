---
title: Commands and keys
summary: Slash commands, keyboard shortcuts and mouse actions.
order: 4
---
## Slash commands
| Command | What it does | Networks |
|---|---|---|
| `/join #room` | Joins a room on the current network | both |
| `/part [#room]` | Leaves a room (the current one if none given); in a private conversation it closes it | both |
| `/msg nick text` | Opens a private conversation and sends the text (`/query nick` just opens it) | both |
| `/me action` | Third-person action line | both |
| `/search words` | Full-text search of your local history for this network | both |
| `/ask question` | Asks Axiom (the room assistant) in the current room | HOME |
| `/reply <id> text` | Replies to a message by id (right-click, or the hover Reply button, does this for you) | HOME |
| `/react <id> 🔥` | Reacts to a message (right-click, or the hover React button) | HOME |
| `/topic [text]` | Shows or sets the room topic | both |
| `/whois nick` | Who is that (answers appear as system lines in the current room) | both |
| `/nick newname` | Changes your handle on this network | both |
| `/clear` | Clears the current view (your history stays in the local store) | both |
| `/help` | Prints the command and key list into the current room | both |
| `/raw LINE` | Sends a raw IRC line | both |

Type `/` in the composer and a command list opens; Up/Down to pick, Enter or Tab to take it.

## Keys
| Key | Action |
|---|---|
| Enter | Send. Shift+Enter breaks a line; a multi-line message is sent as one IRC line per line |
| Tab | Completes a nick from the member list (adds `: ` at the start of a line) or a `/command`; press again to cycle |
| Up / Down | Walks your sent-message history when the box is empty |
| Ctrl+K | Quick switcher: type part of a room name or a `/command`, Enter to go |
| Alt+Up / Alt+Down, Ctrl+Tab | Previous / next room |
| Alt+A | Next room with unread messages |
| Ctrl+1 … Ctrl+9 | Jump to the n-th room in the list |
| Ctrl+, | Settings |
| Ctrl+. | Show or hide the right-hand rail |
| Ctrl+F | Puts `/search ` in the composer |
| Ctrl+L | Clears the current view |
| Ctrl+= / Ctrl+- / Ctrl+0 | Message text larger / smaller / back to 14 px (never below 14) |
| Esc | Cancels a reply in progress, closes the command popup |
| F1 | Help |
| Ctrl+Q | Quit (closing the window only hides it to the tray by default; change that in Settings) |

## Mouse
Hover a message for **Reply**, **React** and **Copy** buttons (HOME rooms; EFnet gets Copy). Right-click a message for those plus **Mention**, **Message** (opens a private conversation), **Copy message id** and the full timestamp. Ctrl+click a message to send 👍. Links in messages are clickable; the tooltip shows where they go. Double-click a member to mention them; right-click a member for Mention / Message / Whois / Copy nick. Click a network header in the room list to collapse it; right-click a room for Mark as read / Leave.
