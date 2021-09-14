from enum import Enum
from os.path import join
from shutil import copy
from datetime import datetime
import re
from bs4 import BeautifulSoup
from bs4.element import NavigableString, Tag


WHISPER_ROLL_FONT = '##660066'
CHAT_FONT = '##261A12'
NPC_CHAT_FONT = '##000066'
OOC_FONT = '##005500'
EMOTE_FONT = '##880000'
MOOD_FONT = '##000000'

FEN_EXT_NAME = "Fen's StarTrekAdventures Extension"

CAMPAIGN_DIR = r'C:\Users\Michael\AppData\Roaming\SmiteWorks\Fantasy Grounds\campaigns\Far Beyond the Stars'
CHATLOG_FILE = 'chatlog.html'
DB_FILE = "db.xml"
OUT_DIR = r'D:\random\dice\Far Beyond the Stars Resources\Chatlogs\output'
BACKUP_DIR = join(OUT_DIR, "backups")

SPEAKER_PATTERN = re.compile("([^:]+:)(.+)", re.DOTALL)
MOOD_PATTERN = re.compile("([^(]+)(\([^:]+)(.+)", re.DOTALL)


class LineTypes(Enum):
    WHISPER_AND_NPC_ROLL = 1,
    PC_ROLL = 2,
    CHAT = 3,
    OOC = 4,
    EMOTE = 5,
    STORY = 6,
    DETERMINE = 7,
    MOOD = 8,
    UNKNOWN = 10


class ChatFormatter:
    def __init__(self, campaign_dir, ep_title, ep_name, out_dir=OUT_DIR):
        self.campaign_dir = campaign_dir
        self.ep_title = ep_title
        self.ep_name = ep_name
        self.out_dir = out_dir
        self.pc_names = self.get_pc_names()
        self.pc_roll_pres = self.get_pc_roll_pres()
        self.pc_chat_pres = self.get_pc_chat_pres()
        self.soup = self.get_chat_soup()

    @staticmethod
    def format_map():
        return {
            LineTypes.PC_ROLL: ChatFormatter.bold,
            LineTypes.CHAT: ChatFormatter.bold_speaker,
            LineTypes.EMOTE: ChatFormatter.italicize,
            LineTypes.STORY: ChatFormatter.blockquote,
            LineTypes.DETERMINE: ChatFormatter.bold,
            LineTypes.MOOD: ChatFormatter.format_mood,
        }

    def get_pc_roll_pres(self):
        return ["%s: [ " % s for s in self.pc_names] + \
               ["%s:  [" % s for s in self.pc_names]

    def get_pc_chat_pres(self):
        return ["%s: " % n for n in self.pc_names]

    def get_pc_names(self):
        with open(join(self.campaign_dir, DB_FILE), 'r') as db_in:
            soup = BeautifulSoup(db_in.read(), 'lxml')
        return [c.find("name", recursive=False).text for c in soup.find("body").find("root").find("charsheet").find_all(recursive=False)]

    def get_chat_soup(self):
        with open(join(self.campaign_dir, CHATLOG_FILE), 'r') as chatlog_in:
            return BeautifulSoup(chatlog_in.read(), "lxml")

    @staticmethod
    def parse_line(line):
        return line["color"], line.text

    def tags(self):
        yield from self.soup.find_all("font")

    def parse_chatlog(self):
        md_body = self.start_body()
        font_tags = self.tags()
        for font_tag in font_tags:
            md_body.append(self.break_line(str(font_tag)))
            if FEN_EXT_NAME in font_tag.text:
                break
        for font_tag in font_tags:
            color, text = self.parse_line(font_tag)
            if isinstance(font_tag.next_sibling, NavigableString):
                text += font_tag.next_sibling
            elif isinstance(font_tag.nex_sigling, Tag):
                text += font_tag.next_sibling.text
            line_type = self.get_line_type(color, text)
            if line_type == LineTypes.UNKNOWN:
                print("Ran into uncategorized line:\n%s" % text)
                print(color)
                print("Some handling may be needed")
            if line_type == LineTypes.WHISPER_AND_NPC_ROLL:
                continue
            elif line_type == LineTypes.OOC:
                md_body.append(self.break_line(str(font_tag)))
            else:
                f = self.format_map().get(line_type)
                if not f:
                    print("Unhandled line type: %s" % str(line_type))
                    continue
                md_body.append(f(text))
        self.save_formatted(md_body)

    def get_line_type(self, color, text):
        if color == OOC_FONT:
            return LineTypes.OOC
        elif (color == CHAT_FONT and any([text.startswith(s) for s in self.pc_chat_pres])) \
                or color == NPC_CHAT_FONT:
            return LineTypes.CHAT
        elif color == CHAT_FONT:
            return LineTypes.STORY
        elif color == EMOTE_FONT:
            return LineTypes.EMOTE
        elif color == WHISPER_ROLL_FONT and any([text.startswith(s) for s in self.pc_roll_pres]):
            return LineTypes.PC_ROLL
        elif color == WHISPER_ROLL_FONT and "has used a point of Determination" in text:
            return LineTypes.DETERMINE
        elif color == WHISPER_ROLL_FONT:
            return LineTypes.WHISPER_AND_NPC_ROLL
        elif color == MOOD_FONT:
            return LineTypes.MOOD
        else:
            return LineTypes.UNKNOWN

    @staticmethod
    def bold_speaker(line):
        m = SPEAKER_PATTERN.match(line)
        if m and m.groups():
            return ChatFormatter.break_line("**%s**" % m.group(1) + m.group(2))
        return ChatFormatter.break_line(line)

    @staticmethod
    def format_mood(line):
        m = MOOD_PATTERN.match(line)
        if m and m.groups():
            return ChatFormatter.break_line("**%s**" % m.group(1) + "*%s*" % m.group(2) + m.group(3))
        return ChatFormatter.break_line(line)

    @staticmethod
    def blockquote(line):
        return ChatFormatter.break_line(">" + line) + "\n"

    @staticmethod
    def italicize(line):
        return ChatFormatter.break_line("*" + line + "*")

    @staticmethod
    def bold(line):
        return ChatFormatter.break_line("**" + line + "**")

    @staticmethod
    def break_line(line):
        return line + "<br />\n"

    def start_body(self):
        md_body = [
            "# %s\n" % self.break_line(self.ep_title),
            self.break_line(""),
            str(self.soup.find("a")) + str(self.soup.find("b")) + "\n",
            self.break_line("")
        ]
        return md_body

    def save_formatted(self, md_body):
        with open(join(self.out_dir, "%s.md" % self.ep_name), 'w', encoding="utf-8") as md_out:
            md_out.writelines(md_body)


def backup_log():
    copy(join(CAMPAIGN_DIR, CHATLOG_FILE), join(BACKUP_DIR, "chatlog_%s.html" % datetime.now().strftime("%Y_%m_%d")))


if __name__ == '__main__':
    backup_log()
    formatter = ChatFormatter(CAMPAIGN_DIR, "Nothing but Blue Skies (Part 2)", "s01_e02_blue_skies_part_2")
    formatter.parse_chatlog()
