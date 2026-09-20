"""Parser unit tests. Vectors follow the IRCv3 message-tags spec + ircdocs parser-tests corpus shape."""
import pytest
from voxterrae.irc.message import parse, Message, escape_tag_value, unescape_tag_value


def test_plain_command():
    m = parse("PING :abc")
    assert m.command == "PING" and m.params == ["abc"] and m.tags == {} and m.source is None


def test_source_and_params():
    m = parse(":nick!user@host PRIVMSG #chan :hello world")
    assert m.source == "nick!user@host" and m.nick == "nick"
    assert m.params == ["#chan", "hello world"]


def test_tags_escapes_and_empty_values():
    m = parse(r"@a=b\:c\s\\d;e;msgid=X;time=2026-09-20T05:00:00.000Z :s!u@h PRIVMSG #c :hi")
    assert m.tags["a"] == "b;c \\d"   # \: -> ; , \s -> space, \\\\ -> backslash
    assert m.tags["e"] == ""            # tag with no value -> empty string, present
    assert m.msgid == "X" and m.server_time.startswith("2026-09-20")


def test_invalid_escape_and_trailing_backslash():
    assert unescape_tag_value(r"\q") == "q"     # invalid escape yields the char
    assert unescape_tag_value("abc\\") == "abc"  # trailing lone backslash dropped


def test_escape_roundtrip():
    for v in ["", "a;b", "a b", "back\\slash", "cr\rlf\n", "unicode ✓ ; "]:
        assert unescape_tag_value(escape_tag_value(v)) == v


def test_trailing_only_colon_param():
    m = parse(":srv 005 me CHANTYPES=# :are supported by this server")
    assert m.command == "005" and m.params[-1] == "are supported by this server" and "CHANTYPES=#" in m.params


def test_multiple_spaces_are_tolerated():
    m = parse(":srv   PRIVMSG   #c   :x")
    assert m.params == ["#c", "x"]


def test_empty_trailing():
    m = parse("PRIVMSG #c :")
    assert m.params == ["#c", ""]


def test_command_only_colon_body():
    with pytest.raises(ValueError):
        parse("@only=tags")


def test_serialize_roundtrip_with_tags():
    m = Message("TAGMSG", ["#c"], tags={"+draft/react": "🔥", "+draft/reply": "abc"})
    line = m.serialize()
    assert line.startswith("@") and "TAGMSG #c" in line
    back = parse(line)
    assert back.tags == m.tags and back.params == m.params


def test_serialize_trailing_rules():
    assert Message("PRIVMSG", ["#c", "hi there"]).serialize() == "PRIVMSG #c :hi there"
    assert Message("PRIVMSG", ["#c", ":lead"]).serialize() == "PRIVMSG #c ::lead"
    assert Message("PRIVMSG", ["#c", ""]).serialize() == "PRIVMSG #c :"
    with pytest.raises(ValueError):
        Message("PRIVMSG", ["#c d", "x"]).serialize()
    with pytest.raises(ValueError):
        Message("PRIVMSG", ["#c", "a\nb"]).serialize()


def test_batch_tag_and_kind_passthrough():
    m = parse("@batch=abc;msgid=1;time=t :n!u@h PRIVMSG #c :x")
    assert m.batch == "abc"
