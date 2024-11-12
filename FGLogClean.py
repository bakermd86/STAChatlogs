import os
from enum import Enum
from os.path import join, basename
from json import dump, load
from shutil import copy
from datetime import datetime
import re
from bs4 import BeautifulSoup
from bs4.element import NavigableString, Tag
from functools import reduce


WHISPER_FONT = '#660066'
ROLL_FONT = '#660067'
CHAT_FONT = '#261A12'
NARRATOR_FONT = '#261A13'
NPC_CHAT_FONT = '#000066'
OOC_FONT = '#005500'
EMOTE_FONT = '#880000'
MOOD_FONT = '#000000'

FEN_EXT_NAME = "Fen's StarTrekAdventures Ruleset"

FG_BASE_DIR = r'C:\Users\Michael\AppData\Roaming\SmiteWorks\Fantasy Grounds'
CAMPAIGN_DIR = join(FG_BASE_DIR, 'campaigns', 'Far Beyond the Stars')
CHATLOG_FILE = 'chatlog.html'
DB_FILE = "db.xml"
FG_RESOURCES_DIR = r'F:\random\dice\Far Beyond the Stars Resources\Chatlogs'
OUT_DIR = join(FG_RESOURCES_DIR, 'output')
BACKUP_DIR = join(OUT_DIR, "backups")
CAMPAIGN_PORTRAITS = join(CAMPAIGN_DIR, 'portraits')
PORTRAITS_OUT = join(FG_RESOURCES_DIR, 'output', 'Portraits')
DB_IN = join(CAMPAIGN_DIR, DB_FILE)


SPEAKER_PATTERN = re.compile("([^:]+):(.+)", re.DOTALL)
MOOD_PATTERN = re.compile("([^(]+)(\([^:]+)(.+)", re.DOTALL)

# SPEAKER_IMAGE_MAP = {
#     "hailey murry": "![](../images/murry.png)",
#     "zox": "![](../images/zox.png)",
#     "skig": "![](../images/skig.png)",
#     "baras": "![](../images/baras.png)",
#     "bachar": "![](../images/bachar.png)",
#     "11 and 10": "![](../images/twins.png)",
#     "viraseti": "![](../images/viraseti.png)",
#     "zerra": "![](../images/zerra.png)",
#     "malat": "![](../images/malat.png)",
# }

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


class IdentityParser:
    def __init__(self, load_identities=False):
        self._identities = self.load_identities() if load_identities else {}

    def get_image(self, name):
        return self._identities.get(name)

    def get_identities(self):
        return self._identities

    def store_identities(self):
        with open("portrait_mapping.json", "w") as mapping_out:
            dump(self.get_identities(), mapping_out)

    def load_identities(self):
        with open("portrait_mapping.json", "r") as mapping_in:
            return load(mapping_in)

    def parse_character(self, character: Tag):
        char_id = character.name
        char_name = character.find("name", recursive=False)
        if not(char_name and char_name.text and char_id):
            return
        src_portrait = join(CAMPAIGN_PORTRAITS, char_id)
        dst_portrait = join(PORTRAITS_OUT, "%s.png" % char_name.text.replace(" ", "_"))
        copy(src_portrait, dst_portrait)
        self._identities[char_name.text] = dst_portrait

    def store_token(self, name_tag: Tag, token_path):
        token_dst = join(PORTRAITS_OUT, basename(token_path))
        if name_tag and name_tag.text and token_path:
            try:
                copy(token_path, token_dst)
                self._identities[name_tag.text] = token_dst
            except FileNotFoundError:
                return

    def parse_identity(self, identity: Tag):
        token_val = identity.find("token")
        if not token_val or not token_val.text or "@" in token_val.text:
            return
        if token_val.text.startswith("campaign"):
            token_path = join(CAMPAIGN_DIR, token_val.text.removeprefix("campaign/"))
        else:
            token_path = join(FG_BASE_DIR, token_val.text)
        identity_name = identity.find("name", recursive=False)
        non_identity_name = identity.find("nonid_name", recursive=False)
        self.store_token(identity_name, token_path)
        self.store_token(non_identity_name, token_path)

    @staticmethod
    def get_children(tag: Tag):
        return list(reduce(lambda a, b: a + b, map(lambda t: t.findChildren(recursive=False),
                                                   tag.find_all("category", recursive=False)))) + list(
            filter(lambda t: t.name.startswith("id-"), tag.findChildren(recursive=False)))

    def parse_identities(self):
        with open(DB_IN, 'r') as fg_db:
            soup = BeautifulSoup(fg_db, 'lxml')
            root = soup.find("root")
            characters = root.find("charsheet").find_all(recursive=False)
            npcs = self.get_children(root.find("npc", recursive=False))
            senior_staff = root.find("crewmate", recursive=False).findChildren(recursive=False)

            list(map(self.parse_identity, npcs))
            list(map(self.parse_identity, senior_staff))
            list(map(self.parse_character, characters))
            self.store_identities()


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
        self.identity_parser = IdentityParser()

    def format_map(self):
        return {
            LineTypes.PC_ROLL: ChatFormatter.bold,
            LineTypes.CHAT: self.bold_speaker,
            LineTypes.EMOTE: ChatFormatter.italicize,
            LineTypes.STORY: ChatFormatter.blockquote,
            LineTypes.DETERMINE: ChatFormatter.bold,
            LineTypes.MOOD: self.format_mood,
        }

    def get_pc_roll_pres(self):
        return ["%s: [ " % s for s in self.pc_names] + \
               ["%s:  [" % s for s in self.pc_names]

    def get_pc_chat_pres(self):
        return ["%s: " % n for n in self.pc_names]

    def get_pc_names(self):
        with open(join(self.campaign_dir, DB_FILE), 'r') as db_in:
            soup = BeautifulSoup(db_in.read(), 'lxml')
        return [c.find("name", recursive=False).text for c in soup.find("body").find("root").find("charsheet").find_all(recursive=False) if c.find("name", recursive=False)]

    def get_chat_soup(self):
        with open(join(self.campaign_dir, CHATLOG_FILE), 'r') as chatlog_in:
            return BeautifulSoup(chatlog_in.read(), "lxml")

    @staticmethod
    def parse_line(line):
        return line["color"], line.text

    def tags(self):
        yield from self.soup.find_all("font")

    def parse_identities(self):
        self.identity_parser.parse_identities()

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
        # elif (color == CHAT_FONT and any([text.startswith(s) for s in self.pc_chat_pres])) \
        #         or color == NPC_CHAT_FONT:
        elif color == CHAT_FONT or color == NPC_CHAT_FONT:
            return LineTypes.CHAT
        elif color == NARRATOR_FONT:
            return LineTypes.STORY
        elif color == EMOTE_FONT:
            return LineTypes.EMOTE
        elif color == ROLL_FONT and any([text.startswith(s) for s in self.pc_roll_pres]):
            return LineTypes.PC_ROLL
        elif color == ROLL_FONT and "has used a point of Determination" in text:
            return LineTypes.DETERMINE
        elif color in (WHISPER_FONT, ROLL_FONT):
            return LineTypes.WHISPER_AND_NPC_ROLL
        elif color == MOOD_FONT:
            return LineTypes.MOOD
        else:
            return LineTypes.UNKNOWN

    @staticmethod
    def format_speaker_image(speaker, image_path):
        print(speaker, image_path)
        return '<img src="../images/auto/%s" alt="%s" width="50" height="50">' \
               % (basename(image_path), speaker) if (speaker and image_path) else ""

    def add_speaker_image(self, speaker):
        image_path = self.identity_parser.get_image(speaker)
        return ChatFormatter.format_speaker_image(speaker, image_path) + "**%s**" % speaker

    def bold_speaker(self, line):
        m = SPEAKER_PATTERN.match(line)
        if m and m.groups():
            speaker = self.add_speaker_image(m.group(1))
            return ChatFormatter.break_line(speaker + m.group(2))
        return ChatFormatter.break_line(line)

    def format_mood(self, line):
        m = MOOD_PATTERN.match(line)
        if m and m.groups():
            speaker = self.add_speaker_image(m.group(1))
            return ChatFormatter.break_line(speaker + " *%s*" % m.group(2) + m.group(3))
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


def delete_old_log():
    os.remove(join(CAMPAIGN_DIR, CHATLOG_FILE))


if __name__ == '__main__':
    backup_log()
    formatter = ChatFormatter(CAMPAIGN_DIR, "Oh Doctor, Where Art Thou (Part 4)", "s02_e01_oh_doctor_4")
    formatter.parse_identities()
    formatter.parse_chatlog()
    # delete_old_log()
