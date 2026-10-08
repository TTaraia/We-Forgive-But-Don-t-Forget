"""Languages, voices, on-screen strings and mixed-script text drawing (English / Amharic / Tigrinya).
NOTE: the Amharic/Tigrinya strings and map names below are DRAFTS - have a native speaker check them."""
import os, urllib.request
from PIL import Image, ImageDraw, ImageFont

LANGS = {"en": "English", "am": "Amharic", "ti": "Tigrinya"}
VOICES = {"en": (os.environ.get("VOICE_MALE", "en-US-AndrewNeural"), os.environ.get("VOICE_FEMALE", "en-US-JennyNeural")),
          "am": ("am-ET-AmehaNeural", "am-ET-MekdesNeural")}   # Tigrinya has no free voice
STR = {
 "en": {"title": ["Eritrea In The Eyes", "Of The World Today"], "outro": ["Allegations are claims,", "not independently verified"],
        "outro_sub": "Sources are in the description", "source": "Source:", "map": "Map:", "story": "Story {n} of {t}",
        "legend": "Eritrea: flag colours · Ethiopia: light red", "borders": "Natural Earth borders, for orientation only"},
 "am": {"title": ["ኤርትራ በዓለም ዓይን", "ዛሬ"], "outro": ["ክሶች የይገባኛል ጥያቄዎች ናቸው፤", "በገለልተኛ አካል አልተረጋገጡም"],
        "outro_sub": "ምንጮች በመግለጫው ውስጥ ይገኛሉ", "source": "ምንጭ፦", "map": "ካርታ፦", "story": "{n} / {t}",
        "legend": "ኤርትራ፦ የባንዲራ ቀለማት · ኢትዮጵያ፦ ቀላል ቀይ", "borders": "ድንበሮች ለማመልከቻ ብቻ (Natural Earth)",
        "intro_spoken": "ኤርትራ በዓለም ዓይን ዛሬ። የዛሬው የዜና ማጠቃለያ።",
        "outro_spoken": "ክሶች የይገባኛል ጥያቄዎች ብቻ ናቸው፤ በገለልተኛ አካል አልተረጋገጡም። ምንጮቹ በቪዲዮው መግለጫ ውስጥ ተዘርዝረዋል።"},
 "ti": {"title": ["ኤርትራ ኣብ ዓይኒ ዓለም", "ሎሚ"], "outro": ["ክሲታት ጥርዓናት እዮም፣", "ብነጻ ኣካል ኣይተረጋገጹን"],
        "outro_sub": "ምንጭታት ኣብ መግለጺ ኣለዉ", "source": "ምንጪ፦", "map": "ካርታ፦", "story": "{n} / {t}",
        "legend": "ኤርትራ፦ ሕብሪ ባንዴራ · ኢትዮጵያ፦ ፍኩስ ቀይሕ", "borders": "ዶባት ንምርኣይ ጥራይ (Natural Earth)",
        "intro_spoken": "ኤርትራ ኣብ ዓይኒ ዓለም ሎሚ። ሓጺር ጸብጻብ ናይ ሎሚ ዜና።",
        "outro_spoken": "ክሲታት ጥርዓናት ጥራይ እዮም፣ ብነጻ ኣካል ኣይተረጋገጹን። ምንጭታት ኣብ መግለጺ እቲ ቪዲዮ ተዘርዚሮም ኣለዉ።"}}
NAMES = {
 "am": {"Eritrea": "ኤርትራ", "Ethiopia": "ኢትዮጵያ", "Sudan": "ሱዳን", "South Sudan": "ደቡብ ሱዳን", "Djibouti": "ጅቡቲ",
        "Somalia": "ሶማሊያ", "Egypt": "ግብፅ", "Kenya": "ኬንያ", "Uganda": "ኡጋንዳ", "Yemen": "የመን", "Chad": "ቻድ",
        "Libya": "ሊቢያ", "Saudi Arabia": "ሳዑዲ ዓረቢያ", "Oman": "ኦማን", "Afar": "አፋር", "Tigray": "ትግራይ", "Amhara": "አማራ",
        "Oromia": "ኦሮሚያ", "Assab": "አሰብ", "Benishangul-Gumuz": "ቤንሻንጉል ጉሙዝ", "Red Sea": "ቀይ ባሕር", "Gulf of Aden": "የኤደን ባሕረ ሰላጤ"},
 "ti": {"Eritrea": "ኤርትራ", "Ethiopia": "ኢትዮጵያ", "Sudan": "ሱዳን", "South Sudan": "ደቡብ ሱዳን", "Djibouti": "ጅቡቲ",
        "Somalia": "ሶማልያ", "Egypt": "ግብጺ", "Kenya": "ኬንያ", "Uganda": "ዩጋንዳ", "Yemen": "የመን", "Chad": "ጫድ",
        "Libya": "ሊብያ", "Saudi Arabia": "ሳዑዲ ዓረብ", "Oman": "ዖማን", "Afar": "ዓፋር", "Tigray": "ትግራይ", "Amhara": "ኣምሓራ",
        "Oromia": "ኦሮሚያ", "Assab": "ዓሰብ", "Benishangul-Gumuz": "ቤንሻንጉል ጉሙዝ", "Red Sea": "ቀይሕ ባሕሪ", "Gulf of Aden": "ወሽመጥ ዓደን"}}

_fonts, _D = {}, ImageDraw.Draw(Image.new("L", (1, 1)))
EFONT = "https://raw.githubusercontent.com/notofonts/notofonts.github.io/main/fonts/NotoSansEthiopic/hinted/ttf/NotoSansEthiopic-Bold.ttf"

def _path(cls):
    if cls == "L":
        p = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"; return p if os.path.exists(p) else None
    p = os.path.join("mapdata", "NotoSansEthiopic-Bold.ttf")
    if not os.path.exists(p):
        os.makedirs("mapdata", exist_ok=True)
        try:
            req = urllib.request.Request(EFONT, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=60) as r, open(p, "wb") as o: o.write(r.read())
        except Exception as e:
            print("Ethiopic font download failed:", e); return None
    return p

def get_font(cls, sz):
    k = (cls, sz)
    if k not in _fonts:
        p = _path(cls)
        _fonts[k] = ImageFont.truetype(p, sz) if p else ImageFont.load_default()
    return _fonts[k]

def runs(text):
    out = []
    for ch in text:
        cls = "E" if ("\u1200" <= ch <= "\u139f" or "\u2d80" <= ch <= "\u2ddf") else ("S" if ch == " " else "L")
        if cls == "S": cls = out[-1][0] if out else "L"
        if out and out[-1][0] == cls: out[-1][1] += ch
        else: out.append([cls, ch])
    return out

def width(text, sz): return sum(_D.textlength(t, font=get_font(c, sz)) for c, t in runs(text))

def draw_text(d, xy, text, sz, fill, anchor="l", stroke=0, stroke_fill=None):
    """y is the vertical centre of the line; anchor l/m/r is horizontal. Mixes Latin and Ethiopic fonts."""
    x, yc = xy; w = width(text, sz)
    x = x - w / 2 if anchor == "m" else (x - w if anchor == "r" else x)
    for c, t in runs(text):
        f = get_font(c, sz)
        d.text((x, yc + 0.36 * sz), t, font=f, fill=fill, anchor="ls", stroke_width=stroke, stroke_fill=stroke_fill)
        x += d.textlength(t, font=f)

def wrap(text, sz, maxw, max_lines):
    lines, cur = [], ""
    for w in text.split():
        t = (cur + " " + w).strip()
        if width(t, sz) <= maxw or not cur: cur = t
        else: lines.append(cur); cur = w
    if cur: lines.append(cur)
    if len(lines) > max_lines: lines = lines[:max_lines]; lines[-1] = lines[-1].rstrip(" .,") + "…"
    return lines

# ---------- additions for the history project (DRAFT Amharic/Tigrinya: have a native speaker check) ----------
NAMES["am"].update({"Asmara": "አስመራ", "Massawa": "ምጽዋ", "Adwa": "ዓድዋ", "Aksum": "አክሱም", "Addis Ababa": "አዲስ አበባ"})
NAMES["ti"].update({"Asmara": "ኣስመራ", "Massawa": "ምጽዋዕ", "Adwa": "ዓድዋ", "Aksum": "ኣክሱም", "Addis Ababa": "ኣዲስ ኣበባ"})
HIST = {
 "en": {"title": ["Eritrea:", "A Short Modern History"], "intro_sub": "Dates, decisions and institutions",
        "intro_spoken": "Eritrea: a short modern history. A calm look at the dates, decisions and institutions that shaped modern Eritrea.",
        "outro_title": "Thank you for watching", "outro_sub": "Based on standard references, such as Britannica and United Nations records",
        "outro_spoken": "Thank you for watching. This account is based on standard references, such as Britannica and United Nations records.",
        "analysis": "Analysis",
        "styles": {"ancient": "Modern borders shown for reference", "coast": "Italian occupation of the Red Sea coast (1880s)",
                   "italian": "Italian Colony of Eritrea (1890-1941)", "british": "British Military Administration (1941-1952)",
                   "federation": "UN federation with Ethiopia (1952-1962)", "province": "Province of Ethiopia (1962-1991)",
                   "war": "War of independence (1961-1991)", "independent": "Independent Eritrea (recognized 1993)"}},
 "am": {"title": ["ኤርትራ፦", "አጭር ዘመናዊ ታሪክ"], "intro_sub": "ቀኖች፣ ውሳኔዎችና ተቋማት",
        "intro_spoken": "ኤርትራ፣ አጭር ዘመናዊ ታሪክ። ዘመናዊቷን ኤርትራ የቀረጹ ቀኖችን፣ ውሳኔዎችንና ተቋማትን በረጋ መንፈስ የሚቃኝ ዘገባ።",
        "outro_title": "ስለተመለከቱ እናመሰግናለን", "outro_sub": "በመደበኛ ምንጮች ላይ የተመሠረተ፣ ለምሳሌ ብሪታኒካና የተባበሩት መንግሥታት መዛግብት",
        "outro_spoken": "ስለተመለከቱ እናመሰግናለን። ይህ ዘገባ እንደ ብሪታኒካና የተባበሩት መንግሥታት መዛግብት ባሉ መደበኛ ምንጮች ላይ የተመሠረተ ነው።",
        "analysis": "ትንተና",
        "styles": {"ancient": "ዘመናዊ ድንበሮች ለማጣቀሻ ብቻ ታይተዋል", "coast": "የጣሊያን የቀይ ባሕር ዳርቻ ወረራ (1880ዎቹ)",
                   "italian": "የኤርትራ የጣሊያን ቅኝ ግዛት (1890-1941)", "british": "የብሪታንያ ወታደራዊ አስተዳደር (1941-1952)",
                   "federation": "ከኢትዮጵያ ጋር የተባበሩት መንግሥታት ፌዴሬሽን (1952-1962)", "province": "የኢትዮጵያ ክፍለ ሀገር (1962-1991)",
                   "war": "የነጻነት ጦርነት (1961-1991)", "independent": "ነጻ ኤርትራ (እውቅና 1993)"}},
 "ti": {"title": ["ኤርትራ፦", "ሓጺር ዘመናዊ ታሪኽ"], "intro_sub": "ዕለታት፣ ውሳነታትን ትካላትን",
        "intro_spoken": "ኤርትራ፣ ሓጺር ዘመናዊ ታሪኽ። ንዘመናዊት ኤርትራ ዝቐረጹ ዕለታት፣ ውሳነታትን ትካላትን ብህድኣት ዝርኢ ጸብጻብ።",
        "outro_title": "የቐንየልና ስለ ዝተኸታተልኩም", "outro_sub": "ኣብ መሰረታዊ ምንጭታት ዝተመስረተ፣ ከም ብሪታኒካን ሰነዳት ሕቡራት ሃገራትን",
        "outro_spoken": "የቐንየልና ስለ ዝተኸታተልኩም። እዚ ጸብጻብ ኣብ ከም ብሪታኒካን ሰነዳት ሕቡራት ሃገራትን ዝኣመሰሉ መሰረታዊ ምንጭታት ዝተመስረተ እዩ።",
        "analysis": "ትንታነ",
        "styles": {"ancient": "ዘመናዊ ዶባት ንማጣቐሲ ጥራይ ተራእዩ", "coast": "ወራር ጣልያን ኣብ ገምገም ቀይሕ ባሕሪ (1880ታት)",
                   "italian": "ቅኝ ግዛት ኤርትራ ጣልያን (1890-1941)", "british": "ወተሃደራዊ ምምሕዳር ብሪጣንያ (1941-1952)",
                   "federation": "ፈደረሽን ሕቡራት ሃገራት ምስ ኢትዮጵያ (1952-1962)", "province": "ክፍለ ሃገር ኢትዮጵያ (1962-1991)",
                   "war": "ኲናት ናጽነት (1961-1991)", "independent": "ናጻ ኤርትራ (እውቅና 1993)"}}}

# ---------- YouTube upload texts (DRAFT Amharic/Tigrinya) ----------
HIST["en"].update({
 "video_title": "Eritrea: A Short Modern History (1890-1993)",
 "desc": "A calm, date-by-date look at how modern Eritrea came to be: Italian colonization (1890), British administration, the UN federation with Ethiopia (1952), its end in 1962, the war of independence, and the 1993 referendum. Based on standard references.",
 "sources": "Sources: Britannica; United Nations records (for example, UN General Assembly Resolution 390 (V), 1950).",
 "disclosure": "Notes: narration uses a synthetic (AI) voice. Maps show modern borders for orientation only. Subtitles are available in English, Amharic and Tigrinya.",
 "chapters": "Chapters", "chapter_intro": "Introduction", "chapter_outro": "Sources and thanks"})
HIST["am"].update({
 "video_title": "ኤርትራ፦ አጭር ዘመናዊ ታሪክ (1890-1993)",
 "desc": "ዘመናዊቷ ኤርትራ እንዴት እንደተፈጠረች በቀኖችና በተቋማት የሚቃኝ ረጋ ያለ ዘገባ፦ የጣሊያን ቅኝ ግዛት (1890)፣ የብሪታንያ አስተዳደር፣ ከኢትዮጵያ ጋር የተባበሩት መንግሥታት ፌዴሬሽን (1952)፣ በ1962 መፍረሱ፣ የነጻነት ጦርነትና የ1993 ሕዝበ ውሳኔ። በመደበኛ ምንጮች ላይ የተመሠረተ።",
 "sources": "ምንጮች፦ ብሪታኒካ፤ የተባበሩት መንግሥታት መዛግብት (ለምሳሌ የጠቅላላ ጉባኤ ውሳኔ 390 (V)፣ 1950)።",
 "disclosure": "ማስታወሻ፦ ይህ ቪዲዮ ሰው ሠራሽ (AI) ድምፅ ይጠቀማል። ካርታዎች ዘመናዊ ድንበሮችን ለማመልከቻ ብቻ ያሳያሉ። የትርጉም ጽሑፎች በእንግሊዝኛ፣ በአማርኛና በትግርኛ ይገኛሉ።",
 "chapters": "ምዕራፎች", "chapter_intro": "መግቢያ", "chapter_outro": "ምንጮችና ምስጋና"})
HIST["ti"].update({
 "video_title": "ኤርትራ፦ ሓጺር ዘመናዊ ታሪኽ (1890-1993)",
 "desc": "ከመይ ኢላ ዘመናዊት ኤርትራ ከም ዝተፈጥረት ብዕለታትን ትካላትን ዝርኢ ህዱእ ጸብጻብ፦ ቅኝ ግዛት ጣልያን (1890)፣ ምምሕዳር ብሪጣንያ፣ ፈደረሽን ሕቡራት ሃገራት ምስ ኢትዮጵያ (1952)፣ ኣብ 1962 ምፍራሱ፣ ኲናት ናጽነትን ርእይቶ ህዝቢ 1993ን። ኣብ መሰረታዊ ምንጭታት ዝተመስረተ።",
 "sources": "ምንጭታት፦ ብሪታኒካ፤ ሰነዳት ሕቡራት ሃገራት (ንኣብነት ውሳነ ሓባራዊ ጉባኤ 390 (V)፣ 1950)።",
 "disclosure": "ምልክታ፦ ካርታታት ዘመናዊ ዶባት ንምርኣይ ጥራይ የርእዩ። ትሕተ-ጽሑፋት ብእንግሊዝኛ፣ ኣምሓርኛን ትግርኛን ይርከቡ።",
 "chapters": "ምዕራፋት", "chapter_intro": "መእተዊ", "chapter_outro": "ምንጭታትን የቐንየልናን"})

# ---------- PROJECT: We Forgive but don't forget! Remembering the Eritrean War Years (English first; am/ti still need translating) ----------
_SRC = ("Sources:\n"
        "- Human Rights Watch / Africa Watch, Evil Days: 30 Years of War and Famine in Ethiopia (1991), ch. 2 'Scorched Earth in Eritrea, 1961-77': https://www.hrw.org/reports/pdfs/e/ethiopia/ethiopia.919/c2eritre.pdf\n"
        "- Same book, ch. 14 'The Road to Asmara: Eritrea, 1988-91': https://www.hrw.org/reports/pdfs/e/ethiopia/ethiopia.919/d4afabet.pdf\n"
        "- Africa Watch, 'Mengistu has Decided to Burn Us like Wood' (24 July 1990): https://www.hrw.org/reports/pdfs/e/ethiopia/ethiopia907.pdf\n"
        "- UCA Dynamics of Asymmetric Democratization project, Ethiopia/Eritrea 1950-1993: https://uca.edu/politicalscience/dadm-project/sub-saharan-africa-region/ethiopiaeritrea-1950-1993\n"
        "- Eritrean oral-history accounts (Ona, Besikdira): https://zantana.net/stories/the-massacre-at-ona")
HIST["en"].update({
 "title": ["We Forgive but don't forget!", "Remembering the Eritrean War Years"], "intro_sub": "1961 - 1991",
 "intro_spoken": "We Forgive but don't forget! Remembering the Eritrean war years, 1961 to 1991. A careful account for young viewers, based on human rights reports and historical research.",
 "outro_title": "Thank you for watching", "outro_sub": "Sources: Human Rights Watch, Africa Watch and historical research",
 "outro_spoken": "Thank you for watching. The sources are listed in the description. Figures are estimates, and sources sometimes disagree.",
 "video_title": "We Forgive but don't forget! Remembering the Eritrean War Years, 1961-1991 (for young viewers)",
 "desc": "A careful, non-graphic account of major attacks on civilians by the Ethiopian military during Eritrea's war of independence, from 1 September 1961 to 24 May 1991, for young people who did not live through it. Figures are estimates and sources sometimes disagree; each scene says where the numbers come from.",
 "sources": _SRC,
 "disclosure": "Notes: narration uses a synthetic (AI) voice. Maps show modern borders for orientation only. This video describes violence against civilians but shows no graphic images. Human Rights Watch also documented abuses by the Eritrean fronts; this video focuses on the Ethiopian military's actions.",
 "chapters": "Chapters", "chapter_intro": "Introduction", "chapter_outro": "Sources and thanks"})
HIST["en"]["styles"]["memorial"] = "Eritrea under Ethiopian rule (1962-1991)"
for _c in ("am", "ti"):   # placeholders: translate before building these languages
    HIST[_c] = dict(HIST["en"])
