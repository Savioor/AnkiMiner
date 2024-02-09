# AnkiMiner
This is a library intended for mining Anki cards from various sources - currently mainly from videos with subtitles.

## What this projects aims to be
This project's main goal is to assist with studying Japanese using the Anki app. To
achieve this, the project is built mainly with "readers" (mining information form 
various sources) and "writers" (creating Anki cards from the information).

From these goals a few main features are derived.

### Safety
The worst that can happen to your Anki collection is for it to get messed up which will 
force a rollback to your last backup (which you should have). This is a big hit to motivation
and so this project aims to be as safe as possible - preforming as many tests as possible
and not performing any actions on the collection without being sure it's alright.

### Flexibility
This project doesn't aim to solve any one particular problem, but instead provide a 
framework to create cards from any outside source. As such, the project is built to be
modular and any feature that aids with Japaneses learning will find it's place in this
project.

### User Experience
This is NOT a product, and so it doesn't aim to be simple to use. More precisely, this
project doesn't aim to be "plug-and-play". The user interface isn't meant to be pretty 
or friendly, and some actions in the card mining process will not be implemented and thus
will be done by hand. With that said, the goal of this project is to *help*, and so it 
still aims to greatly reduce the time it takes to create Anki cards. Just don't expect it
to do all the work for you, and expect a slight learning curve in using this project.

## Installation

Currently, the only way to download this project is to clone the repository. The main file
of interest for users is `/miners/cmd_miner.py`. To run it you will need to install python 3
and the requirements listed in the `requirements` file. The requirements can be downloaded with the command:
```shell
pip install -r requirements
```
Then, you can run the miner with:
```shell
python miners/cmd_miner.py
```
