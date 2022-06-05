server_to_send = 934876901921652787
import asyncio
import pickle

import os
import re

import discord
from discord.ext import commands
from dotenv import load_dotenv

import difflib
import fitz

import json

import requests

import gspread
from oauth2client.service_account import ServiceAccountCredentials

from fuzzywuzzy import fuzz

from datetime import date, datetime, timedelta

import traceback

load_dotenv("bot.env")
TOKEN = os.getenv('DISCORD_TOKEN')
excel_name = "PjsRoyaumesOublies"

bot_prefix = '!'
bot = commands.Bot(command_prefix=bot_prefix)


def replace_strings(string, table):
    for i in table:
        string = string.replace(i, table[i])
    return string


def only_alphanumeric(elem: str):
    return ''.join(ch for ch in elem.lower() if ch.isalnum())


def searchFor(search,dict):
    for i in dict.keys():
        s = only_alphanumeric(i)
        if s == only_alphanumeric(search):
            return dict[i]
    return False

def best_match(item, options, trads = []):
    #print(item)
    without_trad = [(fuzz.token_set_ratio(item, option) - abs(len(item) - len(option)), option) for option in options]
    result = max(without_trad)
    #print(result)
    if trads:
        trads_scores = [(fuzz.token_set_ratio(item, trads[option]) - abs(len(item) - len(trads[option])), option) for option in options if option in trads]
        if trads_scores:
            with_trad = max(trads_scores)
            result = max(result, with_trad)

    #print(result)
    return result

def multiclass_handle(string):
    lis = re.findall(r"[^0-9]+[0-9]+",string)
    out = {}
    for i in lis:
        class_level = i.strip()
        level = re.search(r"[0-9]+", class_level).group()
        level_pos = class_level.index(level)
        class_dnd = class_level[:level_pos].strip()
        out[class_dnd] = int(level)
    return out


def remove_key_from_dict(key, dict,  excep=None):
    to_pop = []
    for i in dict.keys():
        s = only_alphanumeric(i)
        if s == only_alphanumeric(key) and s != excep:
            to_pop.append(i)

    for i in to_pop:
        dict.pop(i)

def replace_name(key, dict):
    found = searchFor(key,dict)

    remove_key_from_dict(key,dict)
    dict[key] = found

def analyse_doc(doc):
    dic_traits = {"Spells": []}
    corrupted = False
    for page in doc:
        widget = page.first_widget
        while widget:
            if widget.field_type == 2 and widget.next.field_name in ["Athl\u00e9tisme",
                                                                     "Acrobaties", "Discr\u00e9tion", "Escamotage",
                                                                     "Arcanes", "Histoire", "Investigation", "Nature",
                                                                     "Religion", "Dressage", "M\u00e9decine",
                                                                     "Perception", "Survie", "Intimidation",
                                                                     "Persuasion", "Repr\u00e9sentation",
                                                                     "Tromperie", "Perspicacité", "Intuition"]:
                if widget.next.field_name == "Intuition" and "Intuition" not in page.get_text():
                    corrupted = True

                skill = widget.next.field_name
                if corrupted:
                    list_corrupted = ["Intuition", "Investigation", "M\u00e9decine", "Nature", "Perception"]
                    if widget.next.field_name in list_corrupted:
                        skill = list_corrupted[(list_corrupted.index(widget.next.field_name) + 1) % len(list_corrupted)]

                if widget.field_value and widget.field_value != "Off":
                    dic_traits["prof" + skill] = True
                else:
                    dic_traits["prof" + skill] = False
            elif widget.field_name in ["ArcanaProf","AcrobaticsProf","AnimalHandlingProf","AthleticsProf","DeceptionProf",
                        "HistoryProf","InsightProf","IntimidationProf","InvestigationProf","MedicineProf","NatureProf",
                        "PerceptionProf", "PerformanceProf","PersuasionProf","ReligionProf","SleightOfHandProf",
                        "StealthProf","SurvivalProf"]:

                table = {"Athletics": "Athl\u00e9tisme", "Acrobatics": "Acrobaties", "Stealth": "Discr\u00e9tion",
                         "SleightOfHand": "Escamotage", "Arcana":"Arcanes", "History":"Histoire",
                         "AnimalHandling": "Dressage", "Medicine": "M\u00e9decine", "Survival": "Survie",
                         "Performance": "Repr\u00e9sentation", "Deception": "Tromperie", "Insight": "Intuition",
                         "Perception": "Perception", "Intimidation":"Intimidation", "Investigation":"Investigation",
                         "Nature":"Nature", "Persuasion":"Persuasion", "Religion": "Religion"}

                dic_traits["prof"+table[widget.field_name[:-4]]] = True if widget.field_value else False

            elif widget.field_name[:6] == "Spells":
                if widget.field_value:
                    dic_traits["Spells"].append(widget.field_value)
            else:
                no_spaces = widget.field_value.replace(" ", "")
                try_match = re.match(r"\d([.,]\d{3})+",no_spaces)
                if try_match and try_match[0] == no_spaces:
                    if re.match(r"\d(,\d{3})+",no_spaces)[0] == no_spaces:
                        without_comma_number = no_spaces.replace(",","")
                        dic_traits[widget.field_name] = without_comma_number
                    else:
                        without_comma_number = no_spaces.replace(".", "")
                        dic_traits[widget.field_name] = without_comma_number
                else:

                    dic_traits[widget.field_name] = widget.field_value

            widget = widget.next

    replace_name("Player_name", dic_traits)
    replace_name("Character_name", dic_traits)
    replace_name("Xp", dic_traits)
    replace_name("Experience_points", dic_traits)
    replace_name("CHAmod", dic_traits)
    replace_name("STRmod", dic_traits)
    replace_name("INTmod", dic_traits)
    replace_name("WISmod", dic_traits)
    replace_name("DEXmod", dic_traits)
    replace_name("CHAmod", dic_traits)

    if dic_traits["Experience_points"]:
        dic_traits["Xp"] = dic_traits["Experience_points"]
    dic_traits["Xp"] = dic_traits["Xp"].replace(",", "")
    replace_name("Race", dic_traits)
    replace_name("Alignment", dic_traits)
    dic_traits["Alignment"] = replace_strings(dic_traits["Alignment"], {"Neutral": "N", "Neutre": "N", "Lawful": "L",
        "Loyal": "L", "Chaotic": "C", "Chaotique": "C", "Good": "B", "Bon": "B", "Evil": "M", "Mauvais": "M",
        "True": "N", " ": ""})
    if dic_traits["Alignment"] == "N":
        dic_traits["Alignment"] = "NN"

    replace_name("Background", dic_traits)

    level = searchFor("level",dic_traits)
    class_level = searchFor("classlevel", dic_traits)

    remove_key_from_dict("level", dic_traits)
    remove_key_from_dict("classlevel", dic_traits)
    if not level:
        #dic_traits["Class/level"] = class_level
        dic_traits["ClassAndLevel"] = multiclass_handle(class_level)
    else:
        levels = re.split("[_,/-]+", level)
        classes = re.split("[_,/-]+", class_level)
        if len(levels) == len(classes):
            dic_traits["ClassAndLevel"] = {}
            empty_count = 0
            for i in range(min(len(classes),len(levels))):
                if not classes[i]:
                    continue
                while not level[i+empty_count]:
                    empty_count += 1
                dic_traits["ClassAndLevel"][classes[i]] = int(levels[i+empty_count])
        else:
            dic_traits["ClassAndLevel"] = multiclass_handle(class_level)

    dic_traits["TranslatedClassAndLevel"] = {}
    new_class_and_level = {}
    for dnd_class in dic_traits["ClassAndLevel"]:
        classes = ["Artificer", "Barbarian", "Bard", "Cleric", "Druid","Sorcerer", "Fighter", "Wizard", "Monk", "Warlock", "Paladin", "Ranger", "Rogue", "Blood Hunter"]
        classes_trads = {'Artificer': 'Artificier', 'Barbarian': 'Barbare', 'Bard': 'Barde', 'Cleric': 'Clerc', 'Druid': 'Druide', 'Sorcerer': 'Ensorceleur', 'Fighter': 'Guerrier', 'Wizard': 'Magicien', 'Monk': 'Moine', 'Warlock': 'Occultiste', 'Paladin': 'Paladin', 'Ranger': 'Rôdeur', 'Rogue': 'Roublard', 'Blood Hunter': 'Chasseur de sang'}
        best_matches_for_words= []
        for word in dnd_class.split():
            found_word = best_match(word, classes, classes_trads)
            best_matches_for_words.append(found_word)
        found_class = max(best_matches_for_words)[1]
        new_class_and_level[found_class] = dic_traits["ClassAndLevel"][dnd_class]
        if found_class != "Blood Hunter":
            dic_traits["TranslatedClassAndLevel"][classes_trads[found_class]] = dic_traits["ClassAndLevel"][dnd_class]
        else:
            dic_traits["TranslatedClassAndLevel"]["Blood Hunter"] = dic_traits["ClassAndLevel"]["Blood Hunter"]

    dic_traits["ClassAndLevel"] = new_class_and_level
    dic_traits["level_fiche"] = sum(dic_traits["ClassAndLevel"].values())




    return dic_traits

def depth_list(l):
    if isinstance(l, list):
        return 1 + max(depth_list(item) for item in l)
    else:
        return 0


def list_to_string(lis):
    if not lis:
        return ""
    depth = depth_list(lis)
    for i in range(depth):
        lis = ''.join(map(str, lis))
    return lis


def compare_dictionaries(dict1,dict2):
    diff = {}
    for i in list(set(dict1.keys()) | set(dict2.keys())):
        if i not in dict1 or i not in dict2:
            continue
        if dict1[i] != dict2[i]:
            compare1 = dict1[i]
            compare2 = dict2[i]
            if i == "ClassAndLevel":
                for classe in compare2.keys():
                    if classe not in compare1 or compare1[classe] != compare2[classe]:
                        diff[i] = classe
                continue

            if isinstance(compare1, list) or isinstance(compare2, list):
                compare1 = "\n".join(compare1)
                compare2 = "\n".join(compare2)

            if max(len(str(compare1)), len(str(compare2))) < 10:
                #print(str(compare1 or "None")," -> __",str(compare2 or "None"),"__")
                isint1 = re.match(r"\d+([,. ]?\d+)?", str(compare1)) if compare1 else False
                isint1 = isint1[0]==compare1 if isint1 else False
                isint2 = re.match(r"\d+([,. ]?\d+)?", str(compare2)) if compare2 else False
                isint2 = isint2[0] == compare2 if isint2 else False
                if (isint1 and isint2) or (isint1 and not compare2) or (isint2 and not compare1):
                    substraction = float(compare2 or "0") - float(compare1 or "0")
                    substraction = "+"+str(substraction) if substraction>=0 else str(substraction)
                    diff[i] = str(compare1 or "0") + " -> __" + str(compare2 or "0") + "__    *("+substraction+")*"
                else:
                    diff[i] = str(compare1 or "None")+" -> __"+str(compare2 or "None")+"__"
            else:

                translation_map = str.maketrans({"-": " - ", ":":" : ", ",":" , ", ".": " . ", "\n": " \n ", "\r": " \n "})
                compare1 = str(compare1).translate(translation_map)
                compare2 = str(compare2).translate(translation_map)

                first = re.split(" ",compare1)
                then = re.split(" ",compare2)

                differences = list(difflib.ndiff(first, then))


                last_erased = ""
                last_added = ""
                text = ""
                #print(i)
                #print(differences)

                for symbole in differences:

                    if symbole[2:] == "":
                        continue
                    symbole.replace("_", "\_")
                    if symbole[0] == " " or symbole[2:] == "\n":
                        if last_erased:
                            text += "~~" + last_erased[:-1] + "~~ "
                            last_erased = ""
                        if last_added:
                            text += "__" + last_added[:-1] + "__ "
                            last_added = ""
                        text += symbole[2:] + " "
                    elif symbole[0]=="+":
                        if last_erased:
                            text += "~~"+last_erased[:-1]+ "~~ "
                            last_erased = ""
                        last_added += symbole[2:] + " "

                    elif symbole[0]=="-":
                        if last_added:
                            text+= "__"+last_added[:-1]+ "__ "
                            last_added = ""
                        last_erased += symbole[2:] + " "

                if last_erased:
                    text += "~~" + last_erased[:-1] + "~~ "
                if last_added:
                    text += "__" + last_added[:-1] + "__ "

                text = re.sub(r"\n+\s*", r"\n           ", text)

                diff[i] = text
                """diff[i] = ""
                if prem.strip():
                    diff[i] = diff[i] + "<<<Enleve>>>: "+prem
                if deux.strip():
                    diff[i] = diff[i] + "<<<Rajoute>>>: " + deux"""
    #print(diff)
    return diff


def text_envoyer(Player_name, Character_name, update_class, diffs):
    out = ["```yaml\n{0} veut mettre a jour son personnage {1}, qui augmente de niveau en {2}.```**Les changements sont:** \n".format(Player_name, Character_name, update_class)]

    for i in diffs:
        parragraph = "●_"+i+"_: "+diffs[i]+"\n"
        if len(out[-1])+len(parragraph) < 2000:
            out[-1] += parragraph
        elif len(parragraph) < 2000:
            out.append(parragraph)
        else:
            messages = [parragraph]
            while len(messages[-1]) > 2000:
                possible_indx = len(messages[-1])
                while possible_indx > 2000:
                    possible_indx = messages[-1].rindex("\n", 0, possible_indx)
                messages.append(messages[-1][possible_indx:])
                messages[-2] = messages[-2][:possible_indx]
            out.extend(messages)

    return out


def save_pj(perso):
    global excel_name
    # use creds to create a client to interact with the Google Drive API
    scope = ['https://spreadsheets.google.com/feeds','https://www.googleapis.com/auth/drive','https://www.googleapis.com/auth/drive.file','https://www.googleapis.com/auth/spreadsheets']
    creds = ServiceAccountCredentials.from_json_keyfile_name('pjs-royaumes-oubliees-0a2c77f89dcb.json', scope)
    client = gspread.authorize(creds)


    # Find a workbook by name and open the first sheet
    # Make sure you use the right name here.
    sheet = client.open(excel_name)

    sheet_instance = sheet.get_worksheet(0)

    #print(sheet_instance.get_all_values())
    cell = sheet_instance.find(perso["Character_name"])
    str_class = "/".join(
        [x + " " + str(perso["TranslatedClassAndLevel"][x]) for x in perso["TranslatedClassAndLevel"]]) if len(
        perso["TranslatedClassAndLevel"].keys()) > 1 else list(perso["TranslatedClassAndLevel"].keys())[0]

    if not cell:
        i = 2
        col = sheet_instance.col_values(1)
        col2 = sheet_instance.col_values(3)

        while i<= sheet_instance.row_count and (col[i].lower() < perso["Discord_user"][0].lower() or (col[i].lower() == perso["Discord_user"][0].lower() and col2[i].lower() < perso["Character_name"].lower())):
            i+= 1

        sheet_instance.insert_row([perso["Discord_user"][0], "", perso["Character_name"], "", perso["Alignment"], perso["Race"], str_class, "", perso["Level_calculated"], "", "", perso["Last_update"], perso["Creation_date"]],i+1)
        sheet_instance.format("B"+str(i+1)+":M"+str(i+1), {"backgroundColor": {"red": 3/255,"green": 252/255,"blue": 206/255},
            "textFormat": {"foregroundColor": { "red": 0, "green": 0, "blue": 0}}})

        if perso["Discord_user"][1]:
            sheet_instance.format("A" + str(i+1), {"backgroundColor": {"red": 52/255,"green": 168/255,"blue": 83/255}})

    else:
        row = cell.row
        if sheet_instance.cell(row, 7).value != str_class:
            sheet_instance.update_cell(row, 7, str_class)
            sheet_instance.format("G"+str(row), {"backgroundColor": {"red": 3/255,"green": 252/255,"blue": 206/255}})
        sheet_instance.update_cell(row, 9, perso["Level_calculated"])
        sheet_instance.format("I"+str(row), {"backgroundColor": {"red": 3 / 255, "green": 252 / 255, "blue": 206 / 255}})
        sheet_instance.update_cell(row, 12, perso["Last_update"])
        sheet_instance.format("L" + str(row), {"backgroundColor": {"red": 3 / 255, "green": 252 / 255, "blue": 206 / 255}})



def point_buy_without_mods(values):
    points = 0
    if max(values)>15 or min(values)<8:
        return False
    for i in values:
        points += min(i-8, 5) + max(0, i-13)*2
        if points > 27:
            return False

    if points == 27:
        return True
    else:
        return False


def detect_point_buy(goal, mods):
    if len(mods) == 0:
        return point_buy_without_mods(goal)
    elif len(mods) == 1:
        for stat_added in range(6):
            no_mod = goal.copy()
            no_mod[stat_added] -= mods[0]
            #print(no_mod)
            if point_buy_without_mods(no_mod):
                return True
        return False
    elif len(mods) == 2:
        for stat_added1 in range(6):
            for stat_added2 in range(6):
                if stat_added2 == stat_added1:
                    continue
                no_mod = goal.copy()
                no_mod[stat_added1] -= mods[0]
                no_mod[stat_added2] -= mods[1]
                no_mod[stat_added2] -= mods[1]
                #print(no_mod)
                if point_buy_without_mods(no_mod):
                    return True
        return False
    elif len(mods) == 3:
        for stat_added1 in range(6):
            for stat_added2 in range(6):
                if stat_added2 == stat_added1:
                    continue
                    for stat_added3 in range(6):
                        if stat_added3 == stat_added1 or stat_added3 == stat_added2:
                            continue
                        no_mod = goal.copy()
                        no_mod[stat_added1] -= mods[0]
                        no_mod[stat_added2] -= mods[1]
                        no_mod[stat_added3] -= mods[2]
                        #print(no_mod)
                        if point_buy_without_mods(no_mod):
                            return True
        return False
    elif len(mods) == 5:
        no_mod = [i-1 for i in goal]
        if point_buy_without_mods(no_mod):
            return True


def detect_prof(pj):
    skills = ["Athl\u00e9tisme", "Acrobaties",
              "Discr\u00e9tion", "Escamotage", "Arcanes","Histoire", "Investigation", "Nature", "Religion", "Dressage",
              "M\u00e9decine", "Perception", "Survie", "Intimidation", "Persuasion", "Repr\u00e9sentation", "Tromperie"]

    if "profIntuition" in pj:
        skills.append("Intuition")
    else:
        skills.append("Perspicacité")

    profs = []
    for skill in skills:
        if pj["prof"+skill]:
            profs.append(skill)

    return profs


def translate(skills):
    table = {"Athl\u00e9tisme": "Athletics",
     "Acrobaties": "Acrobatics", "Discr\u00e9tion": "Stealth", "Escamotage":"Sleight of Hand", "Arcanes":"Arcana", "Histoire": "History",
     "Dressage": "Animal Handling", "M\u00e9decine": "Medicine", "Survie": "Survival", "Repr\u00e9sentation": "Performance",
     "Tromperie": "Deception", "Intuition": "Insight", "Perception":"Perception"}

    for skill_indx in range(len(skills)):
        if skills[skill_indx] in table:
            skills[skill_indx] = table[skills[skill_indx]]

    return skills



def expected_init(pj):
    with open("bot_data.json", "r") as file:
        official_data = json.load(file)
    with open("traductions.json", "r") as file:
        trads = json.load(file)

    found_class = list(pj["ClassAndLevel"].keys())[0]
    """found_class = None
    for potential_class in official_data["class"]:
        if potential_class.lower() in list(pj["ClassAndLevel"].keys())[0].lower():
            found_class = potential_class
            break"""


    found_race = best_match(pj["Race"], official_data["race"], trads)[1]
    """charact_race = pj["Race"].lower().split()[0]
    found_race = None
    for potential_race in official_data["race"]:
        if charact_race in potential_race.lower() or (
                charact_race in trads and trads[charact_race] in potential_race.lower()):
            found_race = potential_race
            break"""

    found_background = best_match(pj["Background"], official_data["background"], trads)[1]
    """
    charact_background = pj["Background"].lower()
    found_background = None
    
    for potential_background in official_data["background"]:
        if charact_background in potential_background.lower():
            found_background = potential_background
            break"""

    #print("Class:",found_class,"Race:", found_race, "Background:", found_background)
    out = "**Proficiencies:** \n"
    profs = set(translate(detect_prof(pj)))

    if found_background:
        background_profs = official_data["background"][found_background]["proficiency"].split(", ") if official_data["background"][found_background]["proficiency"] else []
        profs = profs.difference(background_profs)
        for i in range(official_data["background"][found_background]["num_optional_proficiencies"]):
            for a in official_data["background"][found_background]["optional_proficiencies"].split(", "):
                if a in profs:
                    background_profs.append(a)
                    profs.remove(a)
                    break
        out += "Background ({0}): [{1}]\n".format(found_background, ", ".join(background_profs))
    else:
        out+= "Background: couldn't be recognised\n"

    if found_race:
        race_profs = official_data["race"][found_race]["proficiency"].split(", ") if isinstance(official_data["race"][found_race]["proficiency"], str) else []
        profs = profs.difference(race_profs)
        out += "Race ({0}): [{1}]\n".format(found_race, ", ".join(race_profs))
    else:
        out += " Race: couldn't be recognised\n"
    #print(profs)

    if found_class:
        class_profs = [value for value in official_data["class"][found_class]["proficiency"].split(", ") if
                       value in profs][:int(official_data["class"][found_class]["numSkills"])]
        profs = profs.difference(class_profs)
        out += " Class ({0}): [{1}]\n".format(found_class, ", ".join(class_profs))
    else:
        out += " Class: couldn't be recognised\n"

    if profs:
        out += "  Couldn't be matched: ["+", ".join(list(profs))+"]\n"

    if found_race:
        goal = [int(pj["STRmod"]), int(pj["DEXmod"]), int(pj["CONmod"]), int(pj["INTmod"]), int(pj["WISmod"]), int(pj["CHAmod"])]
        #print(official_data["race"][found_race]["ability"])
        mods = re.findall(r"[0-9]+", official_data["race"][found_race]["ability"]) if isinstance(official_data["race"][found_race]["ability"], str) else []
        mods = [int(i) for i in mods]
        #print(goal, mods)
        out += "**PointBuy:**"
        if detect_point_buy(goal, mods):
            out+= "\n ✅ Potential PointBuy with mods: ["+", ".join(map(str, mods))+"]"
        else:
            out += "\n ❌ No PointBuy with mods: [" + ", ".join(map(str, mods)) + "]"
    return out


async def await_new(task_name, waiting_message_id, announce_msg_id, ctx_message_id, player_id, info_pj, abrev, ctx_channel_id, bot_messages_channel_id):
    ctx_channel = bot.get_channel(ctx_channel_id)
    bot_messages_channel = bot.get_channel(bot_messages_channel_id)

    player = await bot.fetch_user(player_id)

    waiting_message = await ctx_channel.fetch_message(waiting_message_id)
    ctx_message = await ctx_channel.fetch_message(ctx_message_id)
    announce_msg = await bot_messages_channel.fetch_message(announce_msg_id)

    doc_inbytes = ctx_message.attachments[0]
    URL = doc_inbytes.url
    res = requests.get(URL)
    doc = fitz.open("pdf", stream=res.content)

    def check(payload):
        roles = [i.name for i in payload.member.roles]
        return ("MJ" in roles or "Intendant" in roles) and payload.message_id in [ctx_message_id, announce_msg_id] and str(payload.emoji) in ["🟩", "❌"]

    confirmation_task = asyncio.create_task(bot.wait_for("raw_reaction_add", check=check), name=task_name)
    confirmation = await confirmation_task

    if confirmation:
        with open("pending.json", "r+") as file_pending:
            tasks = json.load(file_pending)
            for i in range(len(tasks)):
                if tasks[i][0] == task_name:
                    found = i
                    break
            tasks.pop(found)
            file_pending.truncate(0)
            file_pending.seek(0)
            json.dump(tasks, file_pending)


        await waiting_message.delete()
        if str(confirmation.emoji) == "❌":
            await ctx_message.add_reaction("❌")
            if announce_msg:
                await announce_msg.add_reaction("❌")

            await player.send("La création de votre personnage {0} n'a pas été acceptée par {1}.".format(info_pj["Character_name"], confirmation.member.name))
            return
        else:

            await player.send("La création de votre personnage {0} a été acceptée.".format(info_pj["Character_name"]))
            today = date.today()

            info_pj["Xp_calculated"] = info_pj["Xp"]
            gold_fiche = float(info_pj["PP"] or 0) * 10 + float(info_pj["GP"] or 0) + float(
                info_pj["EP"] or 0) * 0.5 + float(info_pj["SP"] or 0) * 0.1 + float(info_pj["CP"] or 0) * 0.01

            info_pj["Po_calculated"] = gold_fiche
            info_pj["Level_calculated"] = info_pj["level_fiche"]
            info_pj["Creation_date"] = today.strftime("%d/%m/%Y")
            info_pj["Last_update"] = today.strftime("%d/%m/%Y")
            path = "pjs/"+info_pj["Character_name"]+".json"

            with open(path, 'w') as json_file:
                json.dump(info_pj, json_file)

            if abrev and abrev!="None":
                abrev = abrev.replace("_"," ")
                with open("pjs/abreviations.json", "r+") as abrev_file:
                    dict_abrev = json.load(abrev_file)
                    if abrev in dict_abrev.keys():
                        await ctx_channel.send("The pseudo is already taken. Set another one with {0}change-pseudo".format(bot_prefix))
                    else:

                        dict_abrev[abrev] = info_pj["Character_name"]
                        abrev_file.truncate(0)
                        abrev_file.seek(0)
                        json.dump(dict_abrev, abrev_file)

            await ctx_message.add_reaction("🟩")
            if announce_msg:
                await announce_msg.add_reaction("🟩")
                await announce_msg.edit(
                    content="```yaml\n La création du personnage {0} de {1} a été acceptée par {2}```".format(
                        info_pj["Character_name"], player.name, confirmation.member.name))
            else:
                await bot_messages_channel.send(
                    content="```yaml\n La création du personnage {0} de {1} a été acceptée par {2}```".format(
                        info_pj["Character_name"], player.name, confirmation.member.name))

            save_pj(info_pj)
            await ctx_message.add_reaction("✅")
            if announce_msg:
                await announce_msg.add_reaction("✅")

            doc.save("sauvegardes/"+info_pj["Character_name"]+".pdf")

@bot.command(name='new-pj', brief='Crée un nouveau Pj pour le bot.', description="Cette commande va créer perso pour le bot, qui sera ensuite utilisé pour comparer. Un pseudo peut être choisi (pour les autres commandes) et vous pouvez écrire 0 au deuxième argument si ce n'est pas un niveau 1 (ne vérifira pas les compétences et le point buy).La colonne sera automatiquement crée sur le tableau de recensement.")
async def new_pj(ctx, abrev=None, lvl_1="True"):
    if not(ctx.message.attachments):
        await ctx.send('There is no file attached.')
        return
    ctx_message = ctx.message
    player = ctx_message.author
    await ctx_message.add_reaction("🤖")
    waiting_message = await ctx.send('Waiting for confirmation.')


    doc_inbytes = ctx_message.attachments[0]
    URL = doc_inbytes.url
    res = requests.get(URL)
    doc = fitz.open("pdf", stream=res.content)

    info_pj = analyse_doc(doc)
    info_pj["Discord_user"] = [player.name, "MJ" in [x.name for x in player.roles]]

    announce_msg = ""
    if lvl_1 !="False" and lvl_1 != "0":
        channel = bot.get_channel(server_to_send)
        detected_inits = expected_init(info_pj)
        intro = '__**Creation of pj "{0}" of user {1}:**__ \n'.format(info_pj["Character_name"], info_pj["Discord_user"][0])
        announce_msg = await channel.send(intro + detected_inits)

    with open("pending.json", "r+") as file_pending:
        tasks = json.load(file_pending)
        name_pending = "new-pj "+info_pj["Character_name"]
        tasks.append([name_pending, waiting_message.id, announce_msg.id, ctx_message.id, player.id, info_pj, abrev, ctx.channel.id, server_to_send])
        file_pending.truncate(0)
        file_pending.seek(0)
        json.dump(tasks, file_pending)


    await await_new(name_pending, waiting_message.id, announce_msg.id, ctx_message.id, player.id, info_pj, abrev, ctx.channel.id, server_to_send)


async def await_update(name_pending, to_delete, update_info, bot_messages_channel_id, player_id, check_ids, file_path, ctx_channel_id):
    #to delete = message_bot, message_warning_gold, message_warning_xp
    print(name_pending)
    player = await bot.fetch_user(player_id)

    bot_messages_channel = bot.get_channel(bot_messages_channel_id)
    ctx_channel = bot.get_channel(ctx_channel_id)

    file_message = await ctx_channel.fetch_message(check_ids[0])
    doc_inbytes = file_message.attachments[0]
    URL = doc_inbytes.url
    res = requests.get(URL)
    doc = fitz.open("pdf", stream=res.content)

    def check(payload):
        roles = [i.name for i in payload.member.roles]
        return ("MJ" in roles or "Intendant" in roles) and payload.message_id in check_ids and str(payload.emoji) in ["🟩", "❌"]


    confirmation_task = asyncio.create_task(bot.wait_for("raw_reaction_add", check=check), name=name_pending)
    #confirmation_task = asyncio.create_task(bot.wait_for("reaction_add"), name="update-pj " + update_info["Character_name"])

    print(name_pending + "2")
    confirmation = await confirmation_task
    print(name_pending + "3")
    if confirmation:
        with open("pending.json", "r+") as file_pending:
            tasks = json.load(file_pending)
            for i in range(len(tasks)):
                if tasks[i][0] == name_pending:
                    found = i
                    break
            tasks.pop(found)
            file_pending.truncate(0)
            file_pending.seek(0)
            json.dump(tasks, file_pending)

        for id in to_delete:
            message = await ctx_channel.fetch_message(id)
            await message.delete()

        if str(confirmation.emoji) == "❌":
            await file_message.add_reaction("❌")
            message = await bot_messages_channel.fetch_message(check_ids[1])
            await message.add_reaction("❌")
            await message.edit(
                content="```yaml\nLa mise à jour du perso {0} de {1} n'a pas été acceptée par {2}```".format(
                    update_info["Character_name"], update_info["Discord_user"][0], confirmation.member.name))
            for id in check_ids[2:]:
                message = await bot_messages_channel.fetch_message(id)
                await message.delete()

            await player.send("La mise à jour de votre personnage {0} n'a pas été acceptée par {1}.".format(
                update_info["Character_name"], confirmation.member.name))
            return

        else:

            for id in check_ids[2:]:
                message = await bot_messages_channel.fetch_message(id)
                await message.delete()

            await player.send(
                "La mise à jour de votre personnage {0} a été acceptée.".format(update_info["Character_name"]))
            with open(file_path, 'w') as json_file:
                json.dump(update_info, json_file)

            await file_message.add_reaction("🟩")
            message = await bot_messages_channel.fetch_message(check_ids[1])
            await message.add_reaction("🟩")
            await message.edit(content="```yaml\nLa mise à jour du perso {0} de {1} a été acceptée par {2}```".format(
                update_info["Character_name"], update_info["Discord_user"][0], confirmation.member.name))

            save_pj(update_info)
            await file_message.add_reaction("✅")
            message = await bot_messages_channel.fetch_message(check_ids[1])
            await message.add_reaction("✅")

            doc.save("sauvegardes/" + update_info["Character_name"] + ".pdf")


@bot.command(name='update-pj', brief='Met à jour un Pj.', description="Cette commande va comparer le fichier joint et le dernier, et envoyer aux MJs les changements. Elle se chargera aussi de mettre à jour le tableau de recensement.")
async def update_pj(ctx):
    await ctx.message.add_reaction("🤖")

    file_message = ctx.message
    if not file_message.attachments:
        await ctx.send('There is no file attached.')
        return

    doc_inbytes = file_message.attachments[0]
    URL = doc_inbytes.url
    res = requests.get(URL)
    doc = fitz.open("pdf", stream=res.content)
    update_info = analyse_doc(doc)
    #doc.close()

    file_path = "pjs/" + update_info["Character_name"] + ".json"
    if not(os.path.isfile(file_path)):
        await ctx.send("The file storing the informations of this character can't be found. Check if you have created it with {0}new-pj or if you have changed the name.".format(bot_prefix))
        return

    player = file_message.author

    with open(file_path, 'r') as json_file:
        old_info = json.load(json_file)

    message_warning_xp = None
    if update_info["level_fiche"] != old_info["Level_calculated"]:
        message_warning_xp = await ctx.send("Warning. The level of the file doesn't correspond to yours. Your level is {0} and the file's is {1}.".format(old_info["Level_calculated"],update_info["level_fiche"]))
    gold_fiche = int(update_info["PP"] or 0)*10+int(update_info["GP"] or 0)+int(update_info["EP"] or 0)*0.5+int(update_info["SP"] or 0)*0.1+int(update_info["CP"] or 0)*0.01

    message_warning_gold = None
    if gold_fiche != old_info["Po_calculated"]:
        message_warning_gold = await ctx.send(
            "Warning. The gold of the file doesn't correspond to yours. You have {0}GP and the file has {1}GP.".format(
                old_info["Po_calculated"], gold_fiche))

    update_info["Xp_calculated"] = old_info["Xp_calculated"]
    update_info["Po_calculated"] = gold_fiche
    update_info["Level_calculated"] = old_info["Level_calculated"]
    update_info["Discord_user"] = old_info["Discord_user"]
    update_info["Creation_date"] = old_info["Creation_date"]
    today = date.today()
    update_info["Last_update"] = today.strftime("%d/%m/%Y")

    comparaison = compare_dictionaries(old_info,update_info)

    update_info["Xp_calculated"] = update_info["Xp"]
    update_info["Level_calculated"] = get_level_from_xp(int(update_info["Xp"]))



    if "ClassAndLevel" in comparaison:
        update_class = comparaison["ClassAndLevel"]
        comparaison.pop('ClassAndLevel')
    else:
        update_class = "aucune classe"
    if "TranslatedClassAndLevel" in comparaison:
        comparaison.pop('TranslatedClassAndLevel')
    if "Last_update" in comparaison:
        comparaison.pop('Last_update')
    if "level_fiche" in comparaison:
        comparaison.pop('level_fiche')

    splitted = text_envoyer(update_info["Discord_user"][0], update_info["Character_name"], update_class, comparaison)

    check_ids = [file_message.id]
    channel = bot.get_channel(server_to_send)
    for i in splitted:
        msg = await channel.send(i)
        check_ids.append(msg.id)

    message_bot = await ctx.send('The file has been sent for confirmation. You will receive a message when it gets accepted.')

    todelete = [message_bot.id]
    if message_warning_gold:
        todelete.append(message_warning_gold.id)
    if message_warning_xp:
        todelete.append(message_warning_xp.id)

    with open("pending.json", "r+") as file_pending:
        tasks = json.load(file_pending)
        name_pending = "update-pj "+update_info["Character_name"]
        tasks.append([name_pending, todelete, update_info, channel.id, player.id, check_ids, file_path, ctx.channel.id])
        file_pending.truncate(0)
        file_pending.seek(0)
        json.dump(tasks, file_pending)

    await await_update(name_pending, todelete, update_info, channel.id, player.id, check_ids, file_path, ctx.channel.id)


@bot.command(name='set-pseudo', brief='Change ou ajoute un pseudo au Pj', description="La commande changera le pseudo du Pj(premier argument, peut être l'ancien pseudo) à celui introduit(deuxième pseudo).")
async def pseudo_change(ctx, pj, new):
    await ctx.message.add_reaction("🤖")
    with open("pjs/abreviations.json", "r+") as abrev:

        dict_abrev = json.load(abrev)

        if new in dict_abrev.keys():
            await ctx.send("The pseudo is already taken. Try with another one.")
            return

        pj = pj.replace("_", " ")

        path = "pjs/" + pj + ".json"
        if not os.path.isfile(path):
            if pj not in dict_abrev.keys():
                await ctx.send("PJ couldn't be found. Check if created.")
                return
            dict_abrev[new] = dict_abrev[pj]
            await ctx.send('Pseudo of "{0}" changed from "{1}" to "{2}"'.format(dict_abrev[new], pj, new))
            dict_abrev.pop(pj)
        else:
            if pj in dict_abrev.values():
                for key, value in dict_abrev.items():
                    if value == pj:
                        await ctx.send('Pseudo of "{0}" changed from "{1}" to "{2}"'.format(dict_abrev[key],key,new))
                        dict_abrev.pop(key)
                        dict_abrev[new] = pj
                        break
            else:
                dict_abrev[new] = pj
                await ctx.send('Pseudo of "{0}" set to "{1}"'.format(pj, new))

        abrev.truncate(0)
        abrev.seek(0)
        json.dump(dict_abrev, abrev)


def get_level_from_xp(xp):
    table = [300, 900, 2700, 6500, 14000, 23000, 34000, 48000, 64000, 85000, 100000, 120000, 140000, 165000, 195000,
             225000, 265000, 305000, 355000]
    for i in range(len(table)):
        if xp < table[i]:
            return i+1
    return 20


def find_path(pj, extension=".json", preceding="pjs/"):
    path = preceding + pj + extension
    if not os.path.isfile(path):
        with open("pjs/abreviations.json", "r") as abrev:
            dict_abrev = json.load(abrev)
            if pj not in dict_abrev.keys() or not os.path.isfile(preceding + dict_abrev[pj] + extension):
                return False
            path = preceding + dict_abrev[pj] + extension

    return path


def give_xp_to_pj(mode, player, value):
    player = player.replace("_", " ")
    path = find_path(player)
    if not path:
        return "PJ {0} n'a pas été trouvé. Vérifiez l'ortographe et sa création.".format(player)


    with open(path, "r+") as pj_file:
        pj_info = json.load(pj_file)
        if mode == "set":
            pj_info["Xp_calculated"] = int(value)
            pj_info["Level_calculated"] = get_level_from_xp(pj_info["Xp_calculated"])
            out = 'Xp de PJ "{0}" fixée à {1}. PJ est maintenant niveau {2}'.format(pj_info["Character_name"], value,
                                                                                   str(pj_info["Level_calculated"]))

        elif mode == "add":
            old_level = pj_info["Level_calculated"]
            pj_info["Xp_calculated"] += int(value)
            new_level = get_level_from_xp(pj_info["Xp_calculated"])

            out = '{1} Xp ajoutés à PJ "{0}". Son Xp est maintenant {2}.'.format(pj_info["Character_name"], value,
                                                                                     pj_info["Xp_calculated"])
            if old_level != new_level:
                out += "\nLevel up! Vous êtes maintenant niveau {0}.".format(new_level)
                pj_info["Level_calculated"] = new_level
        elif mode == "get":
            out = 'Xp de PJ "{0}" est {1}, donc de niveau {2}'.format(pj_info["Character_name"],
                                                                                 str(pj_info["Xp_calculated"]),
                                                                                 str(pj_info["Level_calculated"]))

        pj_file.truncate(0)
        pj_file.seek(0)
        json.dump(pj_info, pj_file)

        save_pj(pj_info)

        return out


@bot.command(name='xp', brief="Toutes les commandes relatives à l'xp d'un perso", description="""La commande a 3 modes (premier argument):
-get: Montre l'xp d'un Pj(deuxième argument)
-add: Ajoute value(troisième argument) à un Pj(deuxième argument)
-set: Fixe l'xp d'un Pj(deuxième argument) à value(troisième argument)""")
async def mod_xp(ctx, mode=None, player=None, value=""):
    await ctx.message.add_reaction("🤖")
    roles = [x.name for x in ctx.message.author.roles]
    if not ("MJ" in roles or "Intendant" in roles):
        await ctx.send("Seuls 'MJ' ou 'Intendant' peuvent faire ceci.")
        return
    if not mode or (mode!="get" and not value) or not player:
        await ctx.send("Arguments manquants (utilisez '{0}help xp' pour de l'aide).".format(bot_prefix))
        return
    if mode not in ["add","set","get"]:
        await ctx.send("Mode {0} inexistant (utilisez '{1}help xp' pour de l'aide).".format(mode, bot_prefix))
        return
    if mode!="get" and not value.isdecimal():
        await ctx.send("Value doit être un nombre (utilisez '{0}help xp' pour de l'aide).".format(bot_prefix))
        return

    for pj in player.split(","):
        pj = pj.strip()
        await ctx.send(give_xp_to_pj(mode, pj, value))


def give_gold_to_pj(mode, player, value):
    player = player.replace("_", " ")
    path = find_path(player)
    if not path:
        return "PJ {0} n'a pas été trouvé. Vérifiez l'ortographe et sa création.".format(player)

    with open(path, "r+") as pj_file:
        pj_info = json.load(pj_file)
        if mode == "set":
            pj_info["Po_calculated"] = float(value)
            out = 'L\'or de PJ "{0}" fixé à {1} POs.'.format(pj_info["Character_name"], value)

        elif mode == "add":
            pj_info["Po_calculated"] += float(value)
            out = '{1} POs ajoutées à PJ "{0}". Il a maintenant {2} GP.'.format(pj_info["Character_name"], value,
                                                                                   pj_info["Po_calculated"])

        elif mode == "get":
            out = 'PJ "{0}" a {1} POs.'.format(pj_info["Character_name"], str(pj_info["Po_calculated"]))

        pj_file.truncate(0)
        pj_file.seek(0)
        json.dump(pj_info, pj_file)

        return out


@bot.command(name='gold', brief="Toutes les commandes relatives à l'or d'un perso", description="""La commande a 3 modes (premier argument):
-get: Montre les POs d'un Pj(deuxième argument)
-add: Ajoute value(troisième argument) POs à un Pj(deuxième argument)
-set: Fixe les POs d'un Pj(deuxième argument) à value(troisième argument)""")
async def mod_gold(ctx, mode=None, player=None, value=""):
    await ctx.message.add_reaction("🤖")
    roles = [x.name for x in ctx.message.author.roles]
    if mode!="get" and not ("MJ" in roles or "Intendant" in roles):
        await ctx.send("Seuls 'MJ' ou 'Intendant' peuvent faire ceci.")
        return
    if not mode or (mode!="get" and not value) or not player:
        await ctx.send("Arguments manquants (utilisez '{0}help gold' pour de l'aide).".format(bot_prefix))
        return
    if mode not in ["add","set","get"]:
        await ctx.send("Mode {0} inexistant (utilisez '{1}help gold' pour de l'aide).".format(mode, bot_prefix))
        return
    translation_map = str.maketrans({".": None, "-": None})
    if mode!="get" and not value.translate(translation_map).isdigit():
        await ctx.send("Value doit être un nombre (utilisez '{0}help gold' pour de l'aide).".format(bot_prefix))
        return

    for pj in player.split(","):
        pj = pj.strip()
        await ctx.send(give_gold_to_pj(mode, pj, value))


@bot.command(name='transfer', brief="Commande pour les achats entre Pjs.", description="La commande va enlever value(troisième argument) POs au premier Pj et les verser au deuxième.")
async def transfer(ctx, player1=None, player2=None, value=""):
    await ctx.message.add_reaction("🤖")
    if not player1 or not player2 or not value:
        await ctx.send("Arguments manquants (utilisez '{0}help transfer' pour de l'aide).".format(bot_prefix))
        return

    def check(reaction, user):
        roles = [x.name for x in user.roles]
        return ("MJ" in roles or "Intendant" in roles) and str(reaction.emoji) in ["🟩","❌"] and reaction.message == ctx.message

    confirmation_task = asyncio.create_task(bot.wait_for("reaction_add", check=check),
                                            name=ctx.message)
    confirmation = await confirmation_task

    if confirmation[0].emoji == "❌":
        await ctx.send("Transfer non accepté par {0}.".format(confirmation[1].name))
        return

    else:

        translation_map = str.maketrans({".": None, "-": None})
        if not value.translate(translation_map).isdigit():
            await ctx.send("Value doit être un nombre (utilisez '{0}help transfer' pour de l'aide).".format(bot_prefix))
            return

        player1 = player1.replace("_"," ")
        player2 = player2.replace("_"," ")
        path1 = find_path(player1)
        if not path1:
            await ctx.send("Player1 n'a pas été trouvé. Vérifiez l'ortographe et sa création.")
            return

        path2 = find_path(player2)
        if not path2:
            await ctx.send("Player2 n'a pas été trouvé. Vérifiez l'ortographe et sa création.")
            return

        with open(path1, "r+") as pj1_file:
            pj1_info = json.load(pj1_file)

            if pj1_info["Po_calculated"] < float(value):
                await ctx.send("Pj '{0}' a juste {1} PO. Ce n'est pas assez.".format(pj1_info["Character_name"],pj1_info["Po_calculated"]))
                return

            with open(path2, "r+") as pj2_file:
                pj2_info = json.load(pj2_file)

                pj2_info["Po_calculated"] += float(value)
                pj1_info["Po_calculated"] -= float(value)
                await ctx.send("{0} PO tranférées avec succés de Pj '{1}' (avec maintenant {2} PO) au Pj '{3}' (avec maintenant {4} PO)".format(value, pj1_info["Character_name"], pj1_info["Po_calculated"], pj2_info["Character_name"], pj2_info["Po_calculated"]))

                pj1_file.truncate(0)
                pj1_file.seek(0)
                json.dump(pj1_info, pj1_file)
                pj2_file.truncate(0)
                pj2_file.seek(0)
                json.dump(pj2_info, pj2_file)


@bot.command(name='get-save', brief="Envoie la copie de sécurité d'un Pj", description="Pas grand chose à dire... ça envoie la dernière fiche envoyée au bot.")
async def sauvegarde(ctx, pj):
    pj.replace("_"," ")
    path = find_path(pj, ".pdf", "sauvegardes/")
    if not path:
        await ctx.send("PJ {0} n'a pas été trouvé. Vérifiez l'ortographe et sa création.".format(pj))
        return
    else:
        file = discord.File(path)
        await ctx.send(file=file, content="Ci-joint la dernière sauvegarde du PJ {0}".format(pj))


@bot.command(name='delete-pj', brief="Efface un Pj", description="En avez vous assez de ce Pj que vous avez crée en plaisantant? Vos compagnons bous ont-ils abandonné au combat contre une tarrasque? Vos exploits ne seront pas oubliés, ils seront stockées dans la corbeille à fichiers. (Bref efface un Pj).")
async def delete(ctx, to_delete):
    roles = [x.name for x in ctx.message.author.roles]
    if not ("MJ" in roles or "Intendant" in roles):
        await ctx.send("Vous avez besoin du role 'MJ' ou 'Intendant' pour faire ceci.")
        return
    message = await ctx.send("Etes vous sûr(e) que vous voulez effacer ce PJ? Ceci ne sera pas reversible.")

    def check(reaction, user):
        return reaction.message == message and str(reaction.emoji) == "🟩" and user == ctx.author

    confirmation_task = asyncio.create_task(bot.wait_for("reaction_add", check=check),
                                            name=ctx.message)
    confirmation = await confirmation_task

    if confirmation:
        to_delete = to_delete.replace("_", " ")
        pj = to_delete
        with open("pjs/abreviations.json", "r+") as file:
            dict = json.load(file)
            if to_delete in dict:
                pj = dict[to_delete]
                dict.pop(to_delete)
            dict = {key:val for key, val in dict.items() if val != to_delete}
            file.truncate(0)
            file.seek(0)
            json.dump(dict, file)

        path = find_path(pj)
        os.remove(path)
        path = find_path(pj, ".pdf", "sauvegardes/")
        os.remove(path)
        await ctx.send("Pj '{0}' effacé avec succés.".format(pj))


@bot.command(name='catalogue', brief="Montre la liste des Pjs", description="Easter egg: https://www.youtube.com/watch?v=34Ig3X59_qA")
async def recencement(ctx):

    emojis = ["1️⃣","2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣"]


    sort_column = 0
    reverse_search = False

    def sorting(elem):
        return elem[sort_column]

    def table(lis):
        out = "```"

        max_lenghts = []
        for i in range(len(lis[0])):
            max_lenghts.append(max([len(str(a[i])) for a in lis]) + 3)

        out += "" + "Player".ljust(max_lenghts[0]) + "PJ".ljust(max_lenghts[1]) + "Level".ljust(max_lenghts[2]) + "\n"
        out += "-" * sum(max_lenghts) + "\n"
        for i in lis:
            ligne = ""
            for a in range(len(i)):
                ligne += str(i[a]).ljust(max_lenghts[a])
            out += ligne+"\n"

        return out+"```"

    files = os.listdir("pjs")
    files.remove("abreviations.json")
    lis = []
    for i in files:
        with open("pjs/" + i, "r") as file:
            data = json.load(file)
            lis.append([data["Discord_user"][0], data["Character_name"], sum(data["ClassAndLevel"].values())])
    lis.sort(key=sorting)

    num_colums = len(lis[0])
    emojis = emojis[:num_colums]

    msg = await ctx.send(table(lis))
    for i in emojis:
        await msg.add_reaction(i)

    def check(reaction, user):
        return str(reaction.emoji) in emojis and reaction.message == msg and user != bot.user

    while True:
        confirmation_task = asyncio.create_task(bot.wait_for("reaction_add", check=check), name=ctx.message.content)
        confirmation = False
        try:
            confirmation = await asyncio.shield(confirmation_task)
        except asyncio.CancelledError:
            #print("Eureka!")
            await msg.delete()
        #print("Eureka?")
        if confirmation:

            indx = emojis.index(confirmation[0].emoji)
            author = confirmation[1]
            await confirmation[0].remove(author)
            if indx == sort_column:
                reverse_search = False if reverse_search else True
            else:
                reverse_search = False
                sort_column = indx
            lis.sort(key=sorting, reverse = reverse_search)
            await msg.edit(content=table(lis))


@bot.command(name='active', brief="", description="")
async def debugging(ctx, id=None):
    test_tasks = asyncio.all_tasks(loop=None)
    for i in test_tasks:
        task_name = i.get_name()
        if task_name[:5] != "Task":
            await ctx.send(i.get_name())


@bot.command(name='test', brief="", description="")
async def debugging(ctx, id=None):
    channel = ctx.channel
    await channel.send("test")


class CommandErrorHandler(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        """The event triggered when an error is raised while invoking a command.
        Parameters
        ------------
        ctx: commands.Context
            The context used for command invocation.
        error: commands.CommandError
            The Exception raised.
        """
        if hasattr(ctx.command, 'on_error'):
            return

        cog = ctx.cog
        if cog:
            if cog._get_overridden_method(cog.cog_command_error) is not None:
                return

        message = None

        ignored = (commands.CommandNotFound, )
        error = getattr(error, 'original', error)

        if isinstance(error, ignored):
            return

        if isinstance(error, commands.DisabledCommand):
            message = await ctx.send(f'{ctx.command} has been disabled.')

        elif isinstance(error, commands.NoPrivateMessage):
            try:
                message = await ctx.author.send(f'{ctx.command} can not be used in Private Messages.')
            except discord.HTTPException:
                pass

        elif isinstance(error, commands.BadArgument):
            if ctx.command.qualified_name == 'tag list':
                message = await ctx.send('I could not find that member. Please try again.')

        else:
            text_send = '```Ignoring exception in command {0}.\nDonées pour le geek: \n{1}:{2} => Error line: "{3}"```'.format(ctx.command, type(error), error, traceback.extract_tb(error.__traceback__)[-1].line)
            message = await ctx.send(text_send)
            with open("logs.txt", "r+") as log_file:
                logs = log_file.read()
                logs += str(datetime.today())+":"+text_send[3:-3]+"\n\n"
                log_file.write(logs)


bot.add_cog(CommandErrorHandler(bot))
@bot.event
async def on_ready():
    with open("pending.json", "r+") as file_pending:
        tasks = json.load(file_pending)
        #print(tasks)
        await asyncio.gather(*[await_update(*i) if i[0][:9]=="update-pj"  else await_new(*i) for i in tasks])

bot.run(TOKEN)
