# GIMP Text To Diabotical HUD
A GIMP plugin that converts GIMP text layers to Diabotical HUD elements

This plugin facilitates the creative use of unicode characters to design HUDs.

Example: https://drive.google.com/file/d/1M9DnBqTkpXZYiTofDOZ-u0DXkmEQVTLZ/view?usp=sharing

Tutorial: https://youtu.be/416G1A__I9w

- [GIMP Text To Diabotical HUD](#gimp-text-to-diabotical-hud)
  - [How To Install](#how-to-install)
    - [The Plugin](#the-plugin)
    - [The Fonts](#the-fonts)
  - [How To Uninstall](#how-to-uninstall)
    - [The Plugin](#the-plugin-1)
    - [The Fonts](#the-fonts-1)
  - [Usage](#usage)
    - [Making Designs](#making-designs)
      - [Text Layer Rules](#text-layer-rules)
    - [Importing Designs](#importing-designs)
    - [Optimizing Designs](#optimizing-designs)
      - [Technical Details](#technical-details)
  - [Issues](#issues)
      - [Alignment](#alignment)
      - [Opacity](#opacity)
      - [Technical Details](#technical-details-1)

## How To Install

###  The Plugin

Navigate to the GIMP plugins folder:

> e.g. C:\Users\\**USER-NAME**\AppData\Roaming\GIMP\2.10\plug-ins

Simply place [convert_text_to_HUD.py](https://github.com/Joseph-M-J/GIMP-Text-To-Diabotical-HUD/blob/main/convert_text_to_HUD.py) into this folder, then restart GIMP.

###  The Fonts

Navigate to the Diabotical fonts folder:

> e.g. C:\EpicGames\Diabotical\ui\html\fonts

Install three fonts (right click the file and select install):
- furore.otf
- Roboto-Regular.ttf
- NotoSansJP-Medium.otf

## How To Uninstall

###  The Plugin

Just remove [convert_text_to_HUD.py](https://github.com/Joseph-M-J/GIMP-Text-To-Diabotical-HUD/blob/main/convert_text_to_HUD.py) from the GIMP plugins folder.

###  The Fonts

Navigate to the Windows font folder:

> e.g. C:\Windows\Fonts

Search for and uninstall three fonts (right click the font and select delete):
- Furore Regular
- Roboto Regular
- Noto Sans JP Medium 

## Usage

### Making Designs

Open GIMP and create a fresh image or import a screenshot. 

In either case, it's very important that the GIMP canvas and Diabotical share the same resolution. This is usually the desktop resolution.

Designs should consist of one or more text layers, any other types of layers will be ignored.

Invisible layers will also be ignored.

#### Text Layer Rules

Text layers must:
- Use the Noto Sans JP Medium Font.
- Use pixels (px) for font size.
- Not have any special formatting.
- Not contain any spaces.
- Occupy only one line.

**[Here is a spreadsheet](https://docs.google.com/spreadsheets/d/1GAbxKdHAz2kVsf5OFy_NglOF5SpcLj-I6tfg_c1sBZE/edit?usp=sharing) containing a list of unicode characters that will play nicely with this plugin, use them to make designs.**

Text layer size, color and font should be adjusted using the main (docked) text tool
options panel, not the popup text options panel.

Text layer opacity should be adjusted using the layer opacity slider.

### Importing Designs

Once you have a design you're happy with, activate the plugin:
1. Ensure Diabotical is closed.
2. Expand the "Filters" drop-down menu.
3. Select "Convert Text To HUD".
4. Locate the Diabotical settings file if needed (usually auto-detected).
   > %appdata%\Diabotical\CloudSave\Settings.txt by default
5. Choose to overwrite the playing HUD or the spectating HUD or both.
6. Select OK.
7. Wait for the plugin to finish processing.
8. If there were no errors, Launch Diabotical.

If the Epic Launcher asks whether to "Upload To Cloud" or "Download To Machine" select
"Upload To Cloud".

On success the plugin will report the number of HUD elements imported. 

A backup of the previous settings will always be saved inside the same folder as the GIMP document.

On failure the plugin will describe the problem and suggest a fix.

### Optimizing Designs

Layer groups named with the prefix "**M_**" (M for Merge) are referred to as "merge groups".

> e.g. M_MyLayerGroup

Any text layers inside of a merge group will be combined into one text element. This will reduce the number of text elements without changing the design.

This technique is essential for making complex designs, as too many elements will cause the Diabotical HUD system to stop rendering.

Text layers inside of a merge group must:
- Follow [Text layer rules](#text-layer-rules).
- Be horizonally aligned.
- Be the same size.
- Not overlap.

#### Technical Details

The merge group technique uses whitespace characters to replicate the spacing of the text layers, using only one line of text.

This is possible because there are varying widths of whitespace characters. The whitespace characters supported by Diabotical are:

| **Whitespace Name** | **Character Code** | **Width** |
| --- | --- | --- |
| EM | U+2003 | LARGE |
| Ideographic | U+3000 | |
| Figure | U+2007 | |
| EN | U+2002 | |
| Punctuation | U+2008 | |
| Three-Per-EM | U+2004 | | 
| Four-Per-EM | U+2005 | |
| Normal | U+0020 | |
| Narrow No-Break | U+202F | |
| Thin | U+2009 | |
| Six-Per-EM | U+2006 | |
| Hair | U+200A | SMALL |

The size order for the middle spaces fluctuates between fonts.

The plugin will measure the distance between each text layer in a merge group, and the width of each whitespace character at the appropriate font size.

For each character glyph in a text element, Diabotical will prefer Furore over Roboto, and Roboto over Noto Sans JP. To get accurate measurements the plugin 
mimics this font hierarchy.

Using these measurements, `_solve_whitespace(...)` will attempt to find an efficient combination of whitespace characters that would correctly seperate the text layers. 
The plugin will warn us if it cannot perfectly match the target distance.

## Issues

#### Alignment

The text elements can be misaligned by a pixel or two when imported into Diabotical.

If pixel perfect alignment is required it's possible to compensate for the error in
GIMP, i.e. if the element is a pixel too far to the right in Diabotical, offset the
element by a pixel to the left in GIMP.

#### Opacity

By default GIMP layer opacity (transparency) does not translate directly to Diabotical
opacity. An effort is made to convert opacity however to achieve an exact conversion the
layer mode needs to be set to "legacy".

#### Technical Details

Currently, `_convert_position(...)` uses a hack to convert the position of a text layer:
1. Clone the text layer.
2. Set the text content of the clone to just ▔ (U+2594).
3. Crop the clone layer to the visible region.
4. Convert the position of the cropped clone layer instead of the original.
5. Remove the clone layer.

GIMP and Diabotical render text differently. This makes designing an exact conversion procedure difficult. 

This hack works because the substitute character will sit at the top of the Diabotical text element bounding box. This character is one reason why the text layer font 
must be set to Noto Sans JP, Furore and Roboto do not support it. The other reason is that working with a medley of fonts in GIMP can become overwhelming, additionally 
Noto Sans JP alone contains most of the useful characters.
