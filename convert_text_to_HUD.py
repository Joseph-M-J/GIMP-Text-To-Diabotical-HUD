from urlparse import urlparse
import urllib
import time
import io
import os
import shutil
import json
import string
from gimpfu import *
    
#  _____________________________________________
#  |                                           |
#  | GIMP plugin "GIMP Text To Diabotical HUD" |
#  |                                           |
#  | Copyright:                                |
#  |    2021 Joseph M. Johnston                |
#  |                                           |
#  | Version:                                  |
#  |   1.0                                     |
#  |                                           |
#  | License:                                  |
#  |   GNU General Public License v3.0         |
#  |___________________________________________|
#   

whitespace = {
    "em":     u"\u2003",
    "ideo":   u"\u3000",
    "figure": u"\u2007",
    "en":     u"\u2002",
    "punct":  u"\u2008",
    "3pem":   u"\u2004",
    "4pem":   u"\u2005",
    "normal": u"\u0020",
    "narrow": u"\u202F",
    "thin":   u"\u2009",
    "6pem":   u"\u2006",
    "hair":   u"\u200A"
}

def _print(message):
    pdb.gimp_message(str(message) + "\n")

def _get_font_size(layer):
    font_size, unit = pdb.gimp_text_layer_get_font_size(layer)

    if unit != 0:
        name = pdb.gimp_layer_get_name(layer)
        _print(
            "ERROR: In Layer: [" + name + "], " + 
            "please use pixels as the font size scale."
        )
        return -1

    return font_size

def _get_font_name(layer):
    supported_fonts = ["Noto Sans JP Medium"]
    font = pdb.gimp_text_layer_get_font(layer)

    if font not in supported_fonts:
        name = pdb.gimp_layer_get_name(layer)
        _print(
            "ERROR: In Layer: [" + name + "], "  +
            "please use the " + str(supported_fonts) + " font."
        )
        return ""

    return font

def _convert_font_size(font_size, image_height):
    return font_size * 100.0 / image_height

def _convert_position(image, layer, image_width, image_height):
    layer_copy = pdb.gimp_layer_copy(layer, 1)

    pdb.gimp_image_insert_layer(image, layer_copy, None, 0)
    pdb.gimp_text_layer_set_text(layer_copy, u"\u2594")
    pdb.gimp_text_layer_set_antialias(layer_copy, 0)
    pdb.gimp_image_set_active_layer(image, layer_copy)
    pdb.plug_in_autocrop_layer(image, layer_copy)
    
    x, y = layer_copy.offsets
    percent_x = x * 100.0 / image_width
    percent_y = y * 100.0 / image_height

    pdb.gimp_image_remove_layer(image, layer_copy)

    return percent_x, percent_y

def _get_opacity_and_mode(layer):
    opacity = pdb.gimp_layer_get_opacity(layer) / 100.0

    while layer.parent is not None:
        opacity *= pdb.gimp_layer_get_opacity(layer.parent) / 100.0
        layer = layer.parent
        
    return opacity, pdb.gimp_layer_get_mode(layer)

def _get_hex(value):
    return hex(int(round(value * 255)))[2:].zfill(2)

def _get_color(layer):
    color = pdb.gimp_text_layer_get_color(layer)

    opacity, mode = _get_opacity_and_mode(layer)

    if mode == 28:
        opacity **= 1.0 / 2.2
    elif mode != 0:
        name = pdb.gimp_layer_get_name(layer)
        _print(
            "ERROR: In Layer: [" + name + "], " +
            "please either normal or normal(legacy) blending mode."
        )
        return ""

    r = _get_hex(color.red)
    g = _get_hex(color.green)
    b = _get_hex(color.blue)
    a = _get_hex(opacity)

    return "#" + r + g + b + a

def _get_text(layer):
    text = pdb.gimp_text_layer_get_text(layer)
    name = pdb.gimp_layer_get_name(layer)

    if text is None:
        _print(
            "ERROR: In Layer: [" + name + "], " +
            "please remove style from text."
        )
        return ""

    if "\n" in text:
        _print(
            "ERROR: In Layer: [" + name + "], " +
            "please only use one line of text."
        )
        return ""

    spaces = whitespace.values()
    spaces.extend(string.whitespace)

    if True in [s in text for s in spaces]:
        _print(
            "ERROR: In Layer: [" + name + "], " +
            "Don't include spaces manually, please use merge groups instead."
        )
        return ""

    return text.decode("utf-8")

def _get_font_for_space(space):
    if space == "normal" or space == "narrow":
        return "Furore" 

    if space == "ideo":
        return "Noto Sans JP Medium"

    return "Roboto"

def _solve_whitespace(space_widths, spaces_sorted, target):
    if target < spaces_sorted[-1][1]:
        if spaces_sorted[-1][1] - target > target:
            return 0, []
        return spaces_sorted[-1][1], [spaces_sorted[-1][0]]

    snapshot_total = 0
    active_total = 0
    snapshot_buffer = []
    active_buffer = []
    last_position = 0

    while active_total < target:
        backtrack = True

        for i, (space, width) in enumerate(spaces_sorted):
            if i >= last_position:
                if abs((active_total + width) - target) < abs(snapshot_total - target):
                    snapshot_total = active_total + width
                    snapshot_buffer = active_buffer + [space]
                
                if active_total + width <= target:
                    last_position = i
                    backtrack = False
                    active_total += width
                    active_buffer.append(space)
                    break

        if backtrack:
            if len(active_buffer) > 0:
                elem = active_buffer.pop()
                active_total -= space_widths[elem]

                if last_position == len(spaces_sorted):
                    last_position = spaces_sorted.index((elem, space_widths[elem]))
               
                last_position += 1
            else:
                return snapshot_total, snapshot_buffer

    return active_total, active_buffer

def _get_group_text(group_name, children):
    font_size = _get_font_size(children[0][0])
    ws_sizes = {}

    for space in whitespace:
        width, _, _, _ = pdb.gimp_text_get_extents_fontname(
            whitespace[space], font_size, 0, _get_font_for_space(space)
        )
        ws_sizes[space] = width

    ws_sorted = sorted(ws_sizes.items(), key=lambda x: x[1], reverse=True)
    new_text = ""

    for child in children:
        new_text += _get_text(child[0])

        if child[1] != 0:
            ws_size, ws_string = _solve_whitespace(ws_sizes, ws_sorted, child[1])
            child_name = pdb.gimp_layer_get_name(child[0])

            if ws_size != child[1]:
                _print(
                    "WARNING: In Group: [" + group_name + "], " + 
                    "whitespace error after Layer: [" + child_name + "], " + 
                    "Target size: " + str(child[1]) + ", " +
                    "Actual Size: " + str(ws_size) + "."
                )

            new_text += "".join(map(lambda x: whitespace[x], ws_string))

    return new_text

def _sanitize_group(name, group):
    children = sorted(group.children, key=lambda x: x.offsets[0])
    base = None
    children_measured = []

    for i, child in enumerate(children):
        if not pdb.gimp_item_is_text_layer(child):
            _print(
                "ERROR: In Group: [" + name + "], " +
                "Cannot combine sub groups."
            )
            break
        
        x, y = child.offsets
        
        font_size = _get_font_size(child)
        if font_size < 0: 
            break

        font_name = _get_font_name(child)
        if font_name == "":
            break

        if base is None:
            base = (y, font_size, font_name)
        else:
            child_name = pdb.gimp_layer_get_name(child)

            if y != base[0]:
                _print(
                    "ERROR: In Group: [" + name + "], " +
                    "Layer: [" + child_name + "] " + 
                    "is not horizontally aligned with the leftmost element."
                )
                break

            if font_size != base[1]:
                _print(
                    "ERROR: In Group: [" + name + "], " + 
                    "Layer: [" + child_name + "] " + 
                    "is not the same size as the leftmost element."
                )
                break

            if font_name != base[2]:
                _print(
                    "ERROR: In Group: [" + name + "], " + 
                    "Layer: [" + child_name + "] " + 
                    "is not using the same font as the leftmost element."
                )
                break
        
        text = _get_text(child)
        if text == "":
            break

        if i < len(children)-1:
            width, _, _, _ = pdb.gimp_text_get_extents_fontname(
                text, font_size, 0, font_name
            )
            x1 = x + width
            x2 = children[i+1].offsets[0]
            
            if x2 < x1:
                child_name_1 = pdb.gimp_layer_get_name(child)
                child_name_2 = pdb.gimp_layer_get_name(children[i+1])
               
                _print(
                    "ERROR: In Group: [" + name + "], " + 
                    "Layer: [" + child_name_1 + "] " +
                    "is overlapping with Layer: [" + child_name_2 + "]."
                )
                break

            children_measured.append((child, x2-x1))

        else:
            children_measured.append((child, 0))
            return children_measured

    return None

def _build_element(x, y, text, size, color):
    return {
        "t": "text",
        "gid": -1,
        "x": round(x, 8),
        "y": round(y, 8), 
        "pivot": "top-left",
        "txt": text,
        "font": "default",
        "fontSize": round(size, 8),
        "color": color, 
        "shadow": 0,
        "hide_dead": 0,
        "native": 1
    }

def _process_layers(image):
    elements = []
    layers = image.layers
    
    for layer in layers:
        if not layer.visible:
            continue

        if pdb.gimp_item_is_text_layer(layer):
            font_size = _get_font_size(layer)
            if font_size < 0: 
                return []
            
            font_name = _get_font_name(layer)
            if font_name == "":
                return []
            
            x, y = _convert_position(
                image, layer, image.width, image.height
            )
            
            text = _get_text(layer)
            if text == "":
                return []

            color = _get_color(layer)
            if color == "":
                return []

            elements.append(_build_element(
                x, y, 
                text,
                _convert_font_size(font_size, image.height),
                color
            ))

        elif pdb.gimp_item_is_group(layer) and len(layer.children) > 0:
            group_name = pdb.gimp_layer_get_name(layer)
            
            if group_name[:2] != "M_":
                layers.extend(layer.children)
                continue
            
            children = _sanitize_group(group_name, layer)
            
            if children is None:
                return []
            
            c0 = children[0][0]
            
            font_size = _get_font_size(c0)
            
            x, y = _convert_position(
                image, c0, image.width, image.height
            )

            color = _get_color(c0)
            if color == "":
                return []
            
            elements.append(_build_element(
                x, y,
                _get_group_text(group_name, children),
                _convert_font_size(font_size, image.height),
                color
            ))

    return elements

def _get_settings_file():
    env_appdata = os.path.expandvars("%APPDATA%")
    env_homedrive = os.path.expandvars("%HOMEDRIVE%")
    env_homepath = os.path.expandvars("%HOMEPATH%")
    env_username = os.path.expandvars("%USERNAME%")
    env_userprofile = os.path.expandvars("%USERPROFILE%")

    appdata_path_list = [
        env_appdata,
        os.path.join(env_homedrive, env_homepath, "AppData\\Roaming"),
        os.path.join(env_homedrive, "Users", env_username, "AppData\\Roaming"),
        os.path.join(env_userprofile, "AppData\\Roaming")
    ]

    for path in appdata_path_list:
        settings_path = os.path.join(path, "Diabotical\\CloudSave\\Settings.txt")
        if os.path.exists(settings_path):
            return settings_path

    return "Locate settings file..."

def convert_text_to_HUD(image, _, settings_path, overwrite_p_hud, overwrite_s_hud):
    if image is None:
        _print("ERROR: No image.")
        return

    if image.uri is None:
        _print("ERROR: Please save GIMP document.")
        return

    if not os.path.exists(settings_path):
        _print("ERROR: Invalid settings file path.")
        return
    
    if not overwrite_p_hud and not overwrite_s_hud:
        _print("ERROR: Please choose at least one of Playing HUD or Spectating HUD.")
        return
        
    _, fonts = pdb.gimp_fonts_get_list(r"(roboto|furore|noto sans)")
    
    if "Roboto" not in fonts:
        _print("ERROR: Please install Roboto-Regular.ttf")
        return
    
    if "Furore" not in fonts:
        _print("ERROR: Please install furore.otf")
        return
    
    if "Noto Sans JP Medium" not in fonts:
        _print("ERROR: Please install NotoSansJP-Medium.otf")
        return

    pdb.gimp_image_undo_freeze(image)
    hud_elements = _process_layers(image)
    pdb.gimp_image_undo_thaw(image)
    
    if hud_elements:
        time_stamp = time.strftime("%b-%a-%H-%M-%S", time.gmtime())
        backup_path = os.path.join(
            os.path.dirname(urllib.url2pathname(urlparse(image.uri).path)), 
            "Settings_Backup_" + time_stamp + ".txt"
        )
        shutil.copy(settings_path, backup_path)
        
        file = io.open(settings_path, "r+", encoding="utf-8")
        settings = [l.strip() for l in file if l]

        file.truncate(0)
        file.seek(0)

        for var in settings:
            var_name = var.split("=")[0].strip()

            if overwrite_p_hud and var_name == "hud_definition":
                continue
            elif overwrite_s_hud and var_name == "hud_definition_spec":
                continue
            else:
                file.write(var + "\n")
        
        hud_json = json.dumps({"version": 1.7, "elements": hud_elements})

        if overwrite_p_hud:
            file.write(u"hud_definition = " + hud_json + "\n")

        if overwrite_s_hud:
            file.write(u"hud_definition_spec = " + hud_json + "\n")

        file.close()

        _print(
            "Success!\n\n" + 
            str(len(hud_elements)) + " elements imported into settings file.\n\n" +
            "Backup written to " + backup_path
        )
    else:
        _print(
            "Failure!\n\n" + 
            "No elements converted."
        )

register(
    "python_fu_convert_text_to_HUD",
    "Convert all text layers to Diabotical HUD elements",
    "https://github.com/Joseph-M-J/GIMP-Text-To-Diabotical-HUD",
    "Joseph M. Johnston",
    "Copyright Joseph M. Johnston",
    "2021",
    "<Image>/Filters/Convert Text To HUD",
    "*",
    [
        (PF_FILENAME, "Output_File", "Diabotical settings file", _get_settings_file()),
        (PF_BOOL, "Playing_HUD", "Overwrite playing HUD", True),
        (PF_BOOL, "Spectating_HUD", "Overwrite spectating HUD", False)
    ],
    [],
    convert_text_to_HUD
)

main()