from os.path import join
from shutil import copy
from datetime import datetime
import re

PC_NAMES = [
    "Skig",
    "Zox",
    "Hailey Murry",
    "Oakadan",
    "Kolea",
]

WHISPER_ROLL_FONT = '<font color="##660066">'
CHAT_FONT = '<font color="##261A12">'
NPC_CHAT_FONT = '<font color="##000066">'
OOC_FONT = '<font color="##005500">'
EMOTE_FONT = '<font color="##880000">'

CHATLOG_FILE = r'C:\Users\Michael\AppData\Roaming\SmiteWorks\Fantasy Grounds\campaigns\Far Beyond the Stars\chatlog.html'
OUT_DIR = r'E:\random\dice\Far Beyond the Stars Resources\Chatlogs\output'
BACKUP_DIR = join(OUT_DIR, "backups")

PC_ROLL_PRES = [WHISPER_ROLL_FONT + "%s: [ " % s for s in PC_NAMES] + \
               [WHISPER_ROLL_FONT + "%s: </font> [" % s for s in PC_NAMES]
PC_CHAT_PRES = [CHAT_FONT + "%s: " % n for n in PC_NAMES]

STRIP_PATTERN = re.compile("<font color=\"[#0-8A-F]+\">([^<]+)</font>([^<]*)<br />")


def filter_line(line):
    return not line.startswith(WHISPER_ROLL_FONT) or any([line.startswith(s) for s in PC_ROLL_PRES])


def clean_log(ep_name):
    with open(CHATLOG_FILE, 'r') as chatlog_in:
        lines = list(filter(filter_line, chatlog_in))
    with open(join(OUT_DIR, "chatlog_%s.html" % ep_name), "w") as log_out:
        log_out.writelines(lines)


def backup_log():
    copy(CHATLOG_FILE, join(BACKUP_DIR, "chatlog_%s.html" % datetime.now().strftime("%Y_%m_%d")))


def parse_font_tag(line):
    return line[0:23]


def get_tags(chatlog):
    with open(chatlog, 'r') as file_in:
        for tag in [t for t in set(list(map(parse_font_tag, file_in))) if t.startswith("<font")]:
            print(tag)


def reformat_file(in_file, display_name):
    with open(join(OUT_DIR, "chatlog_%s.html" % in_file), 'r') as log_in:
        lines_in = log_in.readlines()
    lines_out = lines_in[0:7] + ["\n"] + list(map(format_line, lines_in[7:]))
    with open(join(OUT_DIR, in_file+".md"), 'w') as log_out:
        log_out.write("# %s<br />\r\n" % display_name)
        log_out.writelines(lines_out)


def format_line(line):
    if line.startswith(OOC_FONT):
        return line
    elif line.startswith(NPC_CHAT_FONT) or any([line.startswith(s) for s in PC_CHAT_PRES]):
        return break_line(bold_speaker(strip_line(line)))
    elif line.startswith(CHAT_FONT):
        return blockquote(strip_line(line))
    elif line.startswith(EMOTE_FONT):
        return italicize(strip_line(line))
    elif any([line.startswith(s) for s in PC_ROLL_PRES]):
        return bold(strip_line(line))
    return line


def strip_line(line):
    m = STRIP_PATTERN.match(line)
    if m and m.groups():
        if m.group(2):
            return m.group(1) + " " + m.group(2)
        return m.group(1)
    return line


SPEAKER_PATTERN = re.compile("([^:]+:)(.+)")
def bold_speaker(line):
    m = SPEAKER_PATTERN.match(line)
    if m and m.groups():
        return "**%s**" % m.group(1) + m.group(2)
    return line


def blockquote(line):
    return break_line(">"+line) + "\r"


def italicize(line):
    return break_line("*"+line+"*")


def bold(line):
    return break_line("**"+line+"**")


def break_line(line):
    return line + "<br />\r"


if __name__ == '__main__':
    clean_log("s01_e01_just_war_part_2")
    reformat_file("s01_e01_just_war_part_2", "Just War (Part 2)")
