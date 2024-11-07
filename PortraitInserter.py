import re
from json import dump, load
from os.path import join, basename
from shutil import copy
from functools import reduce
from bs4 import BeautifulSoup, Tag

TEST_FILE = r'F:\random\dice\Far Beyond the Stars Resources\Chatlogs\output\s02_e01_oh_doctor_3.md'
TEST_OUT = r'F:\random\dice\Far Beyond the Stars Resources\Chatlogs\output\Portraits'
TEST_OUT_LOGS = r'F:\random\dice\Far Beyond the Stars Resources\Chatlogs\output\Portraits\chatlogs'
FG_BASE_DIR = r'C:\Users\Michael\AppData\Roaming\SmiteWorks\Fantasy Grounds'
CAMPAIGN_DIR = join(FG_BASE_DIR, 'campaigns', 'Far Beyond the Stars')
DB_IN = join(CAMPAIGN_DIR, 'db.xml')
CAMPAIGN_PORTRAITS = join(CAMPAIGN_DIR, 'portraits')

clean_line_images = re.compile("^!\[]\([^)]+\)")

class IdentityParser:
    def __init__(self, load_identities=False):
        self._identities = self.load_identities() if load_identities else {}

    def get_image(self, name):
        return self._identities.get(name)

    def get_identities(self):
        return self._identities

    def store_identities(self):
        with open(join(TEST_OUT, "portrait_mapping.json"), "w") as mapping_out:
            dump(self.get_identities(), mapping_out)

    def load_identities(self):
        with open(join(TEST_OUT, "portrait_mapping.json"), "r") as mapping_in:
            return load(mapping_in)

    def parse_character(self, character: Tag):
        char_id = character.name
        char_name = character.find("name", recursive=False)
        if not(char_name and char_name.text and char_id):
            return
        src_portrait = join(CAMPAIGN_PORTRAITS, char_id)
        dst_portrait = join(TEST_OUT, "%s.png" % char_name.text.replace(" ", "_"))
        copy(src_portrait, dst_portrait)
        self._identities[char_name.text] = dst_portrait

    def store_token(self, name_tag: Tag, token_path):
        token_dst = join(TEST_OUT, basename(token_path))
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


def get_children(tag: Tag):
    return list(reduce(lambda a, b: a+b, map(lambda t: t.findChildren(recursive=False), tag.find_all("category", recursive=False)))) + list(filter(lambda t: t.name.startswith("id-"), tag.findChildren(recursive=False)))


def parse_identities_init():
    with open(DB_IN, 'r') as fg_db:
        soup = BeautifulSoup(fg_db, 'lxml')
        root = soup.find("root")
        characters = root.find("charsheet").find_all(recursive=False)
        npcs = get_children(root.find("npc", recursive=False))
        senior_staff = root.find("crewmate", recursive=False).findChildren(recursive=False)
        id_parser = IdentityParser()
        list(map(id_parser.parse_identity, npcs))
        list(map(id_parser.parse_identity, senior_staff))
        list(map(id_parser.parse_character, characters))
        id_parser.store_identities()


def main():
    parse_identities_init()
    id_parser = IdentityParser(load_identities=True)
    with open(TEST_FILE, "r") as test_chat_in, open(join(TEST_OUT_LOGS, basename(TEST_FILE)), "w") as test_chat_out:
        for line in test_chat_in:
            clean_line = re.sub(clean_line_images, "", line)
            out_line = clean_line
            if clean_line.startswith("**"):
                name = clean_line.split("**")[1].split(":")[0].strip()
                image = id_parser.get_image(name)
                if image:
                    out_line = '<img src="../images/auto/%s" alt="%s" width="50" height="50">' % (basename(image), name)\
                               + clean_line
            test_chat_out.write(out_line)



if __name__ == '__main__':
    main()
