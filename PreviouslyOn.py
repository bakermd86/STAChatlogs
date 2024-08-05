from os import mkdir, rmdir, rename
from os.path import join, exists
from shutil import make_archive, rmtree
from bs4 import BeautifulSoup
from FGLogClean import NPC_CHAT_FONT, CHAT_FONT
from xml.sax.saxutils import escape

DEF_TXT = '<?xml version="1.0" encoding="utf-8"?><root version="4.1" dataversion="20210708" release="0|CoreRPG:5">' \
          '<name>Previously On...</name><ruleset>Fen_StarTrekAdventures</ruleset></root>'


class PreviouslyOnMaker:
    def __init__(self, chatlog, out_dir):
        self.chatlog = chatlog
        self.out_dir = out_dir
        self.soup = self.get_chat_soup()

    def get_chat_soup(self):
        with open(self.chatlog, 'r') as chatlog_in:
            return BeautifulSoup(chatlog_in.read(), "lxml")

    @staticmethod
    def parse_line(line):
        return line["color"], line.text

    def tags(self):
        yield from self.soup.find_all("font")

    def make_previously_on(self):
        font_tags = self.tags()
        body = b'<?xml version="1.0" encoding="utf-8"?><root version="4.1" dataversion="20210708" release="0|CoreRPG:5">' \
               b'<encounter><id-00001><name type="string">Previously On</name><text type="formattedtext">\r\n'
        for font_tag in font_tags:
            color, text = self.parse_line(font_tag)
            if color == CHAT_FONT or color == NPC_CHAT_FONT:
                speaker, *chat = text.split(": ")
                chat = ": ".join(chat)
                body += b"<frame><frameid>%s</frameid>%s</frame>\r\n" % (escape(speaker).encode("utf-8"), escape(chat).encode("utf-8"))
        body += b'</text></id-00001></encounter></root>'
        out_dir = join(self.out_dir, "PreviouslyOn")
        if exists(out_dir):
            rmtree(out_dir)
        mkdir(out_dir)
        db_out = join(out_dir, "db.xml")
        def_out = join(out_dir, "definition.xml")
        mod_out = join(self.out_dir, "PreviouslyOn.mod")
        with open(db_out, 'wb') as f_out:
            f_out.write(body)
        with open(def_out, 'w') as f_out:
            f_out.write(DEF_TXT)
        make_archive(mod_out, "zip", out_dir)
        rename(mod_out + ".zip", mod_out)
        if exists(out_dir):
            rmtree(out_dir)


if __name__ == '__main__':
    maker = PreviouslyOnMaker(r'F:\random\dice\Far Beyond the Stars Resources\Chatlogs\output\backups\id_crisis_1_to_3.html',
                              r'F:\random\dice\Far Beyond the Stars Resources\Chatlogs\output\PrevOn\07-22-2024')
    maker.make_previously_on()
