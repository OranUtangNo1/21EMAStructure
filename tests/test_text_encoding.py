from __future__ import annotations

from pathlib import Path


SUSPICIOUS_MOJIBAKE_TOKENS = (
    "\ufffd",
    "繝",
    "縺",
    "蟆",
    "螳",
    "荳",
    "蜿",
    "譌",
    "遶",
    "逅",
    "蜉",
    "邨",
    "雎",
    "譁",
    "榊",
    "溯",
    "蛻",
    "繧",
)


def test_no_mojibake_markers_in_source_specs_or_tests() -> None:
    roots = (Path("src"), Path("tests"), Path("doc/SystemDocs"))
    suffixes = {".py", ".md", ".txt", ".yaml", ".yml", ".json"}
    hits: list[str] = []
    for root in roots:
        for path in root.rglob("*"):
            if path.is_dir() or path.suffix.lower() not in suffixes:
                continue
            if path.name == "test_text_encoding.py":
                continue
            text = path.read_text(encoding="utf-8")
            for token in SUSPICIOUS_MOJIBAKE_TOKENS:
                if token in text:
                    hits.append(f"{path}: contains {ascii(token)}")
    assert hits == []


def test_cli_japanese_messages_are_isolated_from_oratek_entrypoint() -> None:
    source = Path("src/cli/oratek.py").read_text(encoding="utf-8")
    messages = Path("src/cli/messages_ja.py").read_text(encoding="utf-8")

    assert "CLI_MESSAGES" in source
    assert "実行したい処理" not in source
    assert "株価データ更新" not in source
    assert "ティッカー 例" not in source
    assert "実行したい処理" in messages
    assert "株価データ更新" in messages
    assert "ティッカー 例" in messages
    assert "??" not in messages
