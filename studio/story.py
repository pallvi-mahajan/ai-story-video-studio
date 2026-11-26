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
STOP = {"A", "An", "The", "One", "Once", "When", "How", "Why", "My", "Our", "Story", "Learn", "Learns", "Today",
        "She", "He", "They", "Girl", "Boy", "Little", "Kid", "Child"}
AGE_RE = re.compile(r"\b(?:at\s+)?(?:the\s+)?age\s+(?:of\s+)?(\d{1,2})\b|\b(\d{1,2})[- ]?(?:years?|yrs?)[- ]?old\b", re.I)
SKILL_RE = re.compile(r"\blearn(?:s|ed|t|ing)?\s+(?:how\s+)?(?:to\s+)?([a-z][a-z' ]*?)\s*"
                      r"(?:$|[.!?,]|\b(?:at|when|with|from|in|on|because|after|before|by|for)\b)")
HANDS_ON = re.compile(r"^(make|cook|bake|prepare|ride|swim|play|draw|paint|read|write|sing|dance|tie|grow|plant|build)\b")
SKILL_PLACES = [
    (r"cook|rice|bak|cake|roti|bread|tea\b|soup|food|pancake|cookie|dal|curry|noodle|egg|sandwich|breakfast|lunch|dinner",
     "bright cozy kitchen with pots, pans and colourful spices"),
    (r"swim", "sunny swimming pool with sparkling blue water"),
    (r"ride|cycl|bike|skate", "sunny park path with trees and flowers"),
    (r"read|writ|spell|math|count|homework|study", "cozy room with a little desk and a bookshelf"),
    (r"draw|paint|colou?r", "bright art room with paints and paper"),
    (r"danc|sing|music|piano|guitar|violin|drum", "colourful music room with instruments"),
    (r"plant|garden|grow|flower", "sunny garden with flowers and vegetables"),
]
BOY_NAMES = set("arjun|aarav|kabir|rohan|ravi|rahul|vivaan|aditya|ali|omar|noah|liam|leo|max|sam|tom|ben|jack|ethan|lucas|oliver|"
                "james|jake|ryan|adam|dev|ishaan|krish|neil|sid|yash|zayn|daniel|david|mohan|raju".split("|"))


def _title_case(s):
    return " ".join(w if i and w in {"a", "an", "the", "to", "of", "and", "in", "on"} else w.capitalize() for i, w in enumerate(s.split()))


def write_story(theme: str, n_scenes: int = 6, characters: dict | None = None) -> Story:
    text = theme.strip()
    am = AGE_RE.search(text)
    age = int(am.group(1) or am.group(2)) if am else 0
    low = re.sub(r"\s+", " ", AGE_RE.sub(" ", text.lower())).strip()
    sm = SKILL_RE.search(low)
    skill = sm.group(1).strip() if sm else ""
    lesson = None if skill and HANDS_ON.match(skill) else next(
        (l for l in LESSONS if re.search(r"\b(?:%s)" % l[0], skill or low)), None if skill else LESSONS[6])
    names = [w for w in re.findall(r"\b[A-Z][a-z]{2,}\b", text) if w not in STOP]
    lm = re.match(r"^([a-z]{3,})\s+(?:learn|learns|learned|learnt|wants|tries|is|goes|loves|finds|makes|gets|and)\b", text, re.I)
    if not names and lm and lm.group(1).capitalize() not in STOP:
        names = [lm.group(1).capitalize()]
    boy_name = bool(names) and names[0].lower() in BOY_NAMES
    boy = (bool(re.search(r"\b(he|his|him|boy)\b", low)) or boy_name) and not re.search(r"\b(she|her|girl)\b", low)
    aged = lambda look: re.sub(r"\b\d+-year-old\b", f"{age}-year-old", look, count=1) if age else look
    chars = list((characters or {}).items())
    H, hlook = chars[0] if chars else (names[0] if names else ("Arjun" if boy else "Mia"), aged(HERO["boy" if boy else "girl"]))
    rest = chars[1:]
    A, alook = next((c for c in rest if re.search(r"grand|mom|dad|mother|father|teacher", c[0] + c[1], re.I)), ADULT)
    others = [c for c in rest if c[0] != A]
    fname, flook0 = FRIEND["boy" if boy else "girl"]
    F, flook = others[0] if others else (fname, aged(flook0))
    B, blook = others[1] if len(others) > 1 else BUDDY
    her = "his" if boy else "her"
    if lesson:
        title, all_scenes, extra = _lesson_scenes(lesson, low, H, F, A, B, her)
    else:
        title, all_scenes, extra = _skill_scenes(skill, low, age, H, F, A, B, "he" if boy else "she", "himself" if boy else "herself")
    order = {3: [0, 1, 5], 4: [0, 1, 4, 5], 5: [0, 1, 3, 4, 5]}.get(n_scenes, [0, 1, 2, 3, 4, 5])
    scenes = [all_scenes[i] for i in order]
    k = 0
    while len(scenes) < n_scenes:
        scenes.insert(-1, extra[k % len(extra)])
        k += 1
    used = {l.speaker for s in scenes for l in s.lines}
    cast = {n: lk for n, lk in [(H, hlook), (F, flook), (A, alook), (B, blook)] if n in used}
    if boy:
        title = title.replace("Her ", "His ")
    return Story(f"{H} {title}", "The End", cast, scenes)


def _skill_scenes(skill, low, age, H, F, A, B, she, self):
    """A story about learning a new skill (cooking, swimming, riding a bike...): dream, first try, mess, help, success."""
    ing = bool(re.match(r"^\w+ing\b", skill))
    verb = f"do {skill}" if ing else skill
    how = skill if ing else f"how to {skill}"
    mine = lambda s: re.sub(r"\b(her|his|their)\b", "my", s)
    words = skill.split()
    obj = words[-1] if len(words) > 1 else ""
    place = next((p for r, p in SKILL_PLACES if re.search(r, low)), "sunny backyard with trees and flowers")
    cooking = "kitchen" in place
    all_scenes = [
        Scene("A Big Dream", f"{H} watches {A} {verb} in the {place}, eyes shining with excitement, {B} flies nearby",
              [Line("Narrator", f"This is {H}.{f' {H} is {age} years old.' if age else ''} More than anything, {she} wants to learn {how}!"),
               Line(H, f"{A}, can you teach me {mine(how)}?"),
               Line(A, f"You're {age} now. I think you're ready! First, watch me carefully." if age
                    else "Of course, my little one! First, watch me carefully.")], "cheerful happy music"),
        Scene("The First Try", f"{H} tries to {verb} all alone in the {place}, everything goes wrong, a funny mess everywhere, {H} looks surprised",
              [Line("Narrator", f"The next day, {H} tried to {verb} all by {self}. But it was much harder than it looked!"),
               Line(H, f"Oh no! The {obj or 'food'} is all wrong!" if cooking else "Oh no! This is so hard!"), Line(B, "Uh-oh! Bzzz!")],
              "uh-oh sound"),
        Scene("Feeling Sad", f"{H} sits alone looking sad in the {place}, {B} beside {H}",
              [Line("Narrator", f"{H} felt like giving up."), Line(H, f"Maybe I'm too little to {mine(verb)}..."),
               Line(B, f"Don't give up! Let's ask {A} for help!")], "soft emotional music"),
        Scene(f"{A}'s Lesson", f"{A} kneels down and shows {H} what to do step by step in the {place}, warm golden light",
              [Line(A, "Everyone makes mistakes at the start. Let's do it together, one step at a time."),
               Line(A, "Measure carefully, follow each step, and be patient." if cooking else "Go slowly, watch carefully, and keep practising."),
               Line(H, "Step by step... okay!")], "warm calm music"),
        Scene("Trying Again", f"{H} carefully tries again in the {place} and it works, {H} smiles proudly and {A} claps",
              [Line("Narrator", f"{H} took a deep breath and tried again, slowly and carefully."),
               Line(H, "I did it! I really did it!"), Line(A, f"I'm so proud of you, {H}!")], "happy music, magical sparkle"),
        Scene("A Proud Moment",
              f"{H} proudly serves the {obj or 'food'} to {A} and {F} at the table in the {place}, everyone smiles, {B} and magical sparkles all around"
              if cooking else f"{H} proudly shows {F} and {A} {how} in the {place}, everyone cheers, {B} and magical sparkles all around",
              [Line("Narrator", f"And from that day on, {H} remembered: with patience and practice, you can learn anything!"),
               Line(F, f"Yum! This is delicious, {H}!" if cooking else f"Wow, {H}! You're amazing!"),
               Line(H, "Learning new things is the best!")], "joyful magical music"),
    ]
    extra = [Scene("Practice Makes Perfect", f"{H} practises again and again in the {place}, getting better every time, {B} cheers",
                   [Line(H, "Practice makes perfect!"), Line(B, "Bzzz! You're getting better every time!")], "cheerful music")]
    return (f"Learns {_title_case(skill)}" if ing else f"Learns to {_title_case(skill)}"), all_scenes, extra


def _lesson_scenes(lesson, low, H, F, A, B, her):
    """A moral story (sharing, saying sorry, being brave...) built from one of the LESSONS."""
    pattern, title, place, obj, problem, ask, refuse, feel, advice, fix, moral = lesson
    m = re.search(r"\b(?:her|his|the|my|their)\s+([a-z]+)\b", low)
    obj = m.group(1) if m and not re.search(r"\b(?:%s)" % pattern, m.group(1)) else obj
    obj = "toys" if obj == "toy" else obj
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
    extra = [Scene("Playing Together", f"{H}, {F} and {B} play a fun game together in the {place}",
                   [Line(F, "This is so much fun!"), Line(H, "Let's do it again!")], "cheerful music")]
    return title, all_scenes, extra


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
