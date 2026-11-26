"""Story input: parse a scene script, or write a full moral story from a short theme (no AI service needed)."""
import re
from dataclasses import dataclass, field


@dataclass
class Line:
    speaker: str
    text: str


@dataclass
class Scene:
    heading: str
    visual: str
    lines: list = field(default_factory=list)
    sound: str = ""


@dataclass
class Story:
    title: str
    ending: str
    characters: dict  # name -> look
    scenes: list


NAME_LINE = re.compile(r"^([A-Z][\w' .-]{0,30}?)\s*(?:\([^)]*\))?\s*:\s*(.+)$")
FIELD = re.compile(r"^(visual prompt|visual|scene description|image|picture|narration|narrator|dialogue|dialog|sound|music|"
                   r"ending text|ending|main characters|characters|cast)\s*:\s*(.*)$", re.I)


def _clean(s):
    return re.sub(r"^[#>\-\s*]+", "", s.replace("**", "").replace("__", "").replace("`", "")).strip()


def _unquote(s):
    return s.strip().strip('"“”\'').strip()


def parse_script(text: str):
    title, ending, chars, scenes = "", "", {}, []
    scene, fld = None, None
    for raw in text.splitlines():
        if not raw.strip():
            continue
        if re.match(r"^#\s", raw.strip()) and not title and scene is None:
            title = _clean(raw)
            continue
        l = _clean(raw)
        if re.match(r"^scene\s*\d+", l, re.I):
            scene = Scene(heading=l, visual="")
            scenes.append(scene)
            fld = "visual"
            continue
        m = FIELD.match(l)
        if m:
            k = m.group(1).lower()
            fld = ("visual" if k.startswith(("visual", "scene", "image", "picture")) else "narration" if k.startswith("narrat")
                   else "dialogue" if k.startswith("dialog") else "ending" if k.startswith("ending")
                   else "characters" if ("character" in k or k == "cast") else "sound")
            l = m.group(2).strip()
            if not l:
                continue
        if fld == "ending":
            ending = _unquote(l)
        elif fld == "characters":
            n = NAME_LINE.match(l)
            if n:
                chars[n.group(1).strip()] = _unquote(n.group(2))
        elif scene is None:
            continue
        elif fld == "visual":
            scene.visual = (scene.visual + " " + l).strip()
        elif fld == "sound":
            scene.sound += " " + l
        elif fld == "narration":
            scene.lines.append(Line("Narrator", _unquote(l)))
        elif fld == "dialogue":
            n = NAME_LINE.match(l)
            if n:
                scene.lines.append(Line(n.group(1).strip(), _unquote(n.group(2))))
            elif scene.lines:
                scene.lines[-1].text += " " + _unquote(l)
    scenes = [s for s in scenes if s.visual or s.lines]
    return Story(title, ending or "The End", chars, scenes) if scenes else None


LESSONS = [
    (r"shar(e|ing)", "Learns to Share", "sunny park with swings, trees and flowers", "toys", "doesn't want to share",
     "Can I play with your {obj} too, please?", "No! They are mine!", "Playing alone is not much fun",
     "When we share, the fun gets bigger, not smaller.", "Here, {F}! Let's play with my {obj} together!", "Sharing turns one smile into two!"),
    (r"sorry|apolog|forgive", "Learns to Say Sorry", "sunny beach with a big sandcastle", "sandcastle",
     "breaks a friend's sandcastle by mistake and runs away", "Who broke my {obj}?", "It wasn't me!",
     "Hiding the truth makes my tummy feel heavy", "A brave heart says sorry and helps fix things.",
     "I'm sorry, {F}. It was me. Let's build it again together!", "Saying sorry is a little word with big magic!"),
    (r"patien|wait|turn|line|queue", "Learns to Wait", "colourful fair with a long line for the teacup ride", "turn",
     "wants to skip the long line", "Hey, please wait for your turn!", "But I don't want to wait!",
     "Pushing ahead made everyone sad", "Good things come to those who wait patiently.",
     "I'm sorry. I'll wait for my turn like everyone else.", "Waiting your turn is a way of being kind!"),
    (r"try|give up|practi|again|fail", "Never Gives Up", "park path with a small shiny bicycle", "bicycle",
     "falls off the bicycle and wants to give up", "Are you okay? Want to try again?", "No! I can't do it!",
     "Giving up feels worse than falling", "Every expert was once a beginner. Try one more time!",
     "One more time... I can do it!", "Never give up. Every try makes you stronger!"),
    (r"honest|truth|lie|lying", "Tells the Truth", "cozy living room with a broken flower vase", "vase",
     "breaks a vase and hides it", "Oh no! Who broke the {obj}?", "Maybe the cat did it!",
     "A lie feels like a heavy backpack", "Telling the truth is always the bravest choice.",
     "I broke the {obj}. I'm really sorry.", "The truth always shines brighter than a lie!"),
    (r"brave|fear|afraid|scared|dark|courage", "Finds Courage", "cozy bedroom at night with a little night light", "night light",
     "is scared of the dark", "Why are you hiding under the blanket?", "There might be monsters in the dark!",
     "Being scared all the time is tiring", "Courage isn't having no fear. It's being brave anyway.",
     "I'm brave! The dark is just the night saying goodnight.", "You are braver than you think!"),
    (r"kind|help|care", "Learns to Be Kind", "flower garden with a little lost puppy", "puppy",
     "walks past someone who needs help", "Please, can you help me?", "Not now, I'm busy!",
     "Ignoring a friend made my heart feel cold", "Small acts of kindness make the world brighter.",
     "Don't worry, I'll help you!", "Kindness is a gift everyone can give!"),
    (r"clean|tidy|mess", "Learns to Tidy Up", "messy playroom full of toys", "toys", "leaves toys everywhere",
     "Ouch! I stepped on a block!", "Tidying is boring!", "I can't find anything in this mess",
     "When everything has a home, playing is easier.", "Let's make tidying a game!", "A tidy room makes a happy home!"),
    (r"teeth|brush|healthy|vegetable|eat|food", "Learns Healthy Habits", "bright kitchen with colourful vegetables", "vegetables",
     "only wants sweets", "Would you like some yummy carrots?", "Yuck! I only want candy!",
     "Too much candy gives me a tummy ache", "Colourful food makes you strong and full of energy.",
     "Crunch! Carrots are actually yummy!", "Healthy habits make happy, strong kids!"),
    (r"thank|grateful", "Learns to Say Thank You", "birthday party in a colourful room", "gift", "forgets to say thank you",
     "Do you like the {obj} I made for you?", "It's okay, I guess.", "My friend looks sad now",
     "Thank you are two words that make hearts happy.", "Thank you so much, {F}! I love it!", "Always remember to say thank you!"),
]
HERO = {"girl": "a cheerful 6-year-old girl with long curly dark-brown hair, a yellow flower clip, big brown eyes and a pink dress",
        "boy": "a cheerful 7-year-old boy with short black hair, big brown eyes, a blue t-shirt and jeans"}
FRIEND = {"girl": ("Leo", "a 6-year-old boy with short brown hair, big brown eyes, a green t-shirt and blue jeans"),
          "boy": ("Zara", "a 6-year-old girl with a long black ponytail, big brown eyes and a yellow dress")}
ADULT = ("Grandma Rose", "a kind grandmother with grey hair in a bun, round glasses and a purple shawl")
BUDDY = ("Buzzy", "a tiny round cute honeybee with big shiny eyes and a black graduation cap")
STOP = {"A", "An", "The", "One", "Once", "When", "How", "Why", "My", "Our", "Story", "Learn", "Learns", "Today"}


def write_story(theme: str, n_scenes: int = 6, characters: dict | None = None) -> Story:
    low = theme.lower()
    lesson = next((l for l in LESSONS if re.search(l[0], low)), LESSONS[6])
    _, title, place, obj, problem, ask, refuse, feel, advice, fix, moral = lesson
    names = [w for w in re.findall(r"\b[A-Z][a-z]{2,}\b", theme) if w not in STOP]
    boy = bool(re.search(r"\b(he|his|him|boy)\b", low)) and not re.search(r"\b(she|her|girl)\b", low)
    chars = list((characters or {}).items())
    H, hlook = chars[0] if chars else (names[0] if names else ("Arjun" if boy else "Mia"), HERO["boy" if boy else "girl"])
    F, flook = chars[1] if len(chars) > 1 else FRIEND["boy" if boy else "girl"]
    A, alook = ADULT
    B, blook = chars[2] if len(chars) > 2 else BUDDY
    m = re.search(r"\b(?:her|his|the|my|their)\s+([a-z]+)\b", low)
    obj = m.group(1) if m else obj
    obj = "toys" if obj == "toy" else obj
    her = "his" if boy else "her"
    f = lambda s: s.replace("{obj}", obj).replace("{F}", F)
    all_scenes = [
        Scene("A Happy Day", f"{H} plays happily with {her} {obj} in a {place}, {B} flies nearby smiling",
              [Line("Narrator", f"This is {H}. {H} loves {her} {obj} more than anything!"),
               Line(H, f"Look, {B}! Isn't this the best day ever?"), Line(B, "Bzzz! It's wonderful!")], "cheerful happy music"),
        Scene("Uh-oh!", f"{F} walks over and asks {H} to play in the {place}, {H} hugs the {obj} tightly and looks grumpy",
              [Line("Narrator", f"Then {F} came by. But {H} {problem}."), Line(F, f(ask)), Line(H, f(refuse))], "uh-oh sound"),
        Scene("Feeling Sad", f"{F} walks away sadly, {H} sits alone looking sad in the {place}, {B} beside {H}",
              [Line("Narrator", f"{F} walked away, feeling sad. Soon {H} didn't feel happy either."),
               Line(H, f"{feel}..."), Line(B, f"Maybe {A} can help!")], "soft emotional music"),
        Scene(f"{A}'s Advice", f"{A} kneels down and gently hugs {H} in the {place}, warm golden light",
              [Line(A, "What's wrong, my little one?"), Line(H, f"I made {F} sad."), Line(A, advice)], "warm calm music"),
        Scene("The Right Choice", f"{H} smiles and offers the {obj} to {F} in the {place}, {F} looks happy and surprised",
              [Line("Narrator", f"{H} took a deep breath and went back to {F}."), Line(H, f(fix)), Line(F, "Yay! Thank you!")],
              "happy music, magical sparkle"),
        Scene("Happy Together", f"{H} and {F} laugh and play together joyfully in the {place}, {B} and magical sparkles all around",
              [Line("Narrator", f"And from that day on, {H} remembered: {moral}"), Line(H, "Playing together is the best!")],
              "joyful magical music"),
    ]
    order = {3: [0, 1, 5], 4: [0, 1, 4, 5], 5: [0, 1, 3, 4, 5]}.get(n_scenes, [0, 1, 2, 3, 4, 5])
    scenes = [all_scenes[i] for i in order]
    while len(scenes) < n_scenes:
        scenes.insert(-1, Scene("Playing Together", f"{H}, {F} and {B} play a fun game together in the {place}",
                                [Line(F, "This is so much fun!"), Line(H, "Let's do it again!")], "cheerful music"))
    used = {l.speaker for s in scenes for l in s.lines}
    cast = {n: lk for n, lk in [(H, hlook), (F, flook), (A, alook), (B, blook)] if n in used}
    return Story(f"{H} {title}", "The End", cast, scenes)


def load_story(text: str, n_scenes: int = 6, characters: dict | None = None) -> Story:
    """A full script (with 'Scene 1' headings) is used as written; anything else is treated as a theme."""
    story = parse_script(text)
    if story:
        story.characters = {**story.characters, **(characters or {})}
        return story
    return write_story(text, n_scenes, characters)


def parse_characters(text: str) -> dict:
    out = {}
    for l in (text or "").splitlines():
        m = NAME_LINE.match(l.strip())
        if m:
            out[m.group(1).strip()] = _unquote(m.group(2))
    return out
