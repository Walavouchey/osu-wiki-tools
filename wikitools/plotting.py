import os
import shutil
import csv
import datetime
import math
from itertools import chain
from pathlib import Path
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap
import numpy as np

import importlib
import sys

from wikitools import online_data

OSU_CMAP = None
COLOURS = None


def set_up_theme():
    global OSU_CMAP
    global COLOURS

    file_path = "meta/osu-matplotlib-theme/osu_cmap.py"
    module_name = "osu_cmap"
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    #from osu_cmap import OSU_CMAP, COLORS # type: ignore
    OSU_CMAP = module.OSU_CMAP
    COLOURS = module.COLORS

    plt.rcParams["axes.prop_cycle"] = plt.cycler("color", OSU_CMAP.colors)
    plt.style.use('meta/osu-matplotlib-theme/osu-wiki.mplstyle')


def plot_originals_over_time(language="en", translation_keys=None):
    set_up_theme()

# data
    data = online_data.get_spreadsheet_range("1o--KQKvNF9JtmZmTGuzN6KyBpFwoQDr98TWRHhrzh-E", "statistics!AK:AT")
    data_dates = [datetime.date.fromisoformat(row['Date']) for row in data]
    data_tournament_community = [int(row['Community tournaments']) for row in data]
#data_gts = [int(row['Global Taiko Showdown']) for row in data]
    data_tournament_official = [int(row['Official tournaments']) for row in data]
    data_contest_community = [int(row['Community contests']) for row in data]
    data_contest_official = [int(row['Official contests']) for row in data]
    data_fa = [int(row['Featured Artist releases']) for row in data]
    data_beatmap = [int(row['Standalone beatmaps']) for row in data]
    data_ost = [int(row['Original soundtrack']) for row in data]
    data_other = [int(row['Other']) for row in data]

    data_list = [
        data_tournament_community,
#    data_gts,
        data_tournament_official,
        data_contest_community,
        data_contest_official,
        data_fa,
        data_beatmap,
        data_ost,
        data_other,
    ]

#data_tournament_community = [row['Community tournaments'] for row in data]

    label_keys = {
        "title": "Bespoke music over time",
        "xlabel": "Year",
        "ylabel": "Count",
        "tournament_community": "Official tournaments",
        "tournament_official": "Community contests",
        "contest_community": "Official contests",
        "contest_official": "Community contests",
        "fa_release": "Featured Artist releases",
        "beatmap": "Standalone beatmaps",
        "ost": "osu! original soundtrack",
        "other": "Other osu!-related releases",
    }

    if translation_keys:
        translated_keys = translation_keys.get("graph")
        if translated_keys:
            for key, value in translated_keys.items():
                label_keys[key] = value


    labels = [
        label_keys["tournament_community"],
        label_keys["tournament_official"],
        label_keys["contest_community"],
        label_keys["contest_official"],
        label_keys["fa_release"],
        label_keys["beatmap"],
        label_keys["ost"],
        label_keys["other"],
    ]

    years = list(range(2007, 2025))

    def hex_to_tuple(hex):
        return tuple(int(hex[i:i + 2], 16) for i in (0, 2, 4))

    osu_colours_list = [
        hex_to_tuple("FFAA66"), # orange
        #hex_to_tuple("FF6666"), # red
        hex_to_tuple("66AAFF"), # light blue
        hex_to_tuple("AAFF66"), # green
        hex_to_tuple("6666FF"), # blue
        hex_to_tuple("66FFCC"), # turquoise
        hex_to_tuple("DD55FF"), # purple
        hex_to_tuple("FF66AA"), # osu!pink
        hex_to_tuple("FFFFFF"), # white
        #[140, 102, 255], # purple
        #[255, 217, 102], # orange (actually yellow)
        #[255, 102, 171], # osu!pink
        #[102, 255, 115], # green
        #[178, 255, 102], # lime
        ##[102, 204, 255], # blue
        #[255, 102, 171], # osu!pink
        #[255, 102, 102], # orange
    ]

    osu_colours = ListedColormap(np.array(osu_colours_list) / 255)
    colours = osu_colours.colors
    colours_reversed = ListedColormap(np.array(list(reversed(osu_colours_list))) / 255).colors

    fig, ax = plt.subplots()

    plt.stackplot(data_dates, list(reversed(data_list)), labels=labels, alpha=0.5, zorder=3, colors=colours_reversed)
    accumulated = [0] * len(data_list[0])
    for i, series in enumerate(reversed(data_list), start=3):
        accumulated = [curr + new for curr, new in zip(accumulated, series)]
        plt.plot(data_dates, accumulated, linewidth=2, color=colours_reversed[i-3], zorder=8+3-i)
#plt.plot(years, non_fa_counts, linewidth=2, color=colours[1], zorder=4)
#plt.plot(years, community_counts, linewidth=2, color=colours[0], zorder=5)
#plt.rcParams["axes.prop_cycle"] = plt.cycler("color", reversed(colours))

    plt.title(label_keys["title"])
    plt.xlabel(label_keys["xlabel"])
    plt.ylabel(label_keys["ylabel"])
    plt.legend(loc='upper left')
    legend = ax.get_legend()
    for legend, colour in zip(legend.legend_handles, colours):
       legend.set_color(colour)
#ax.yaxis.set_major_formatter(mtick.PercentFormatter(100))
    ax.set_xlim(datetime.date.fromisoformat("2008-03-01"))
#ax.set_ylim([0, 135])
#ax.set_yticks(list(range(0, 176, 25)))


    language_suffix = "" if language == "en" else f"-{language.upper()}"
    plt.savefig(f"wiki/Community/Bespoke_music/img/bespoke-music-over-time{language_suffix}.png", transparent=True)
