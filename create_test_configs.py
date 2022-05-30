import pathlib
import sqlite3

test_paths = {
    "ascii_path": r"C:\my\ascii.txt",
    "cyrillic_path": r"C:\my\fileЧ.txt",
    "arabic_path": r"C:\my\fileص.txt",
    "latin_path": r"C:\my\fileÉ.txt",
    "greek_path": r"C:\my\fileΨ.txt",
    "traditional_chinese_path": r"C:\my\file碼.txt",
    "simplified_chinese_path": r"C:\my\file响.txt",
    "korean_path": r"C:\my\file탇.txt",
    "japanese_path": r"C:\my\file語.txt",
}

encodings = [
    "utf-8",
    "utf-16-be",
]

path = pathlib.Path(__file__).parent / "tests/example_configs"
for enc in encodings:
    p = path / "{}.yaml".format(enc)
    with open(p, "wb") as h:
        for key in test_paths:
            h.write("{}: {}\n".format(key, test_paths[key]).encode(enc))

    p = path / "{}.toml".format(enc)
    with open(p, "wb") as h:
        for key in test_paths:
            h.write("{} = \"{}\"\n".format(key, test_paths[key]).replace("\\", "\\\\").encode(enc))

    p = path / "{}.json".format(enc)
    with open(p, "wb") as h:
        h.write("{\n".encode(enc))
        first = True
        for key in test_paths:
            if not first:
                h.write(",".encode(enc))
            else:
                first = False
            h.write("\"{}\": \"{}\"\n".format(key, test_paths[key]).replace("\\", "\\\\").encode(enc))
        h.write("}\n".encode(enc))

    p = path / "{}.ini".format(enc)
    with open(p, "wb") as h:
        h.write("[section]\n".encode(enc))
        for key in test_paths:
            h.write("{} = {}\n".format(key, test_paths[key]).encode(enc))

p = pathlib.Path(__file__).parent / "tests/example_configs/basic.db"
conn = sqlite3.connect(p)
cur = conn.cursor()
cur.execute("CREATE TABLE IF NOT EXISTS config(key VARCHAR(1024) UNIQUE, value VARCHAR(1024))")
conn.commit()
cur.execute("INSERT OR IGNORE INTO config(key, value) VALUES ('one', '1')")
cur.execute("INSERT OR IGNORE INTO config(key, value) VALUES ('two.three', '3')")
cur.execute("INSERT OR IGNORE INTO config(key, value) VALUES ('two', '5')")
conn.commit()
