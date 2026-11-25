"""Split a city's code of ordinances into one text file per chapter.

Used by intake.py. Each chapter becomes a document with a heading for every
section, so search cuts it into one chunk per section:

    # Chapter 22 - Public Library
    ## 22.01 Purpose
    The purpose of this chapter is ...
    ## 22.02 Established
    ...

Built for the layout of Iowa Codification codes (common for Iowa cities),
saved as plain text:
  - a table of contents near the top:  CHAPTER 22 - PUBLIC LIBRARY
  - each chapter starts with a line   CHAPTER 22   then its title
  - then a two-column list of its sections (dropped here: it's only a list)
  - then sections like                 22.03 LIBRARY BOARD OF TRUSTEES.
Codes from other publishers may need their own rules.
"""
import re

CHAPTER_LINE = re.compile(r"^\s*\**\s*CHAPTER\s+(\d+[A-Z]?)\s*\**\s*$")   # some are marked *****
CONTENTS_LINE = re.compile(r"^\s*CHAPTER\s+(\d+[A-Z]?)\s*[-–—]\s*(\S.*?)\s*$")
SECTION_START = re.compile(r"^(\d+[A-Z]?)\.(\d+[A-Z]?)\s+(\S.*)$")
BARE_LINK = re.compile(r"^\s*\[?https?://\S+\]?\s*$")   # image links left by the export
EMPTY_CHAPTER = re.compile(r"^\(?\s*(repealed|reserved)\b", re.IGNORECASE)
SMALL_WORDS = {"a", "an", "and", "as", "at", "by", "for", "from", "in", "into", "of",
               "on", "or", "the", "to", "with"}


NAMES_A_CODE = re.compile(r"\b(code of ordinances|municipal code|code of the (city|town|village)"
                          r"|(city|town|village|county) code)\b", re.IGNORECASE)


def names_a_code(start):
    """Does the start of a document call itself a code of ordinances? Used to
    catch codes whose layout looks_like_city_code() doesn't know (another
    publisher's), so they aren't filed as one huge official document."""
    return bool(NAMES_A_CODE.search(start[:3000]))


def looks_like_city_code(text):
    """Does this text have the layout above? (Checked on its first part.)"""
    sample = text[:300_000]
    return ("CODE OF ORDINANCES" in sample[:2000].upper()
            and sum(1 for l in sample.splitlines() if CHAPTER_LINE.match(l)) >= 3
            and sum(1 for l in sample.splitlines() if is_heading(l)) >= 10)


def is_heading(line):
    """A section heading: '22.03 LIBRARY BOARD OF TRUSTEES.' (all capitals,
    and not a row of the two-column section list, which has wide gaps)."""
    stripped = line.strip()
    return (bool(SECTION_START.match(stripped)) and stripped == stripped.upper()
            and any(c.isalpha() for c in stripped) and not re.search(r"\S\s{3,}\S", stripped))


def nice_title(text):
    """'LIBRARY BOARD OF TRUSTEES.' -> 'Library Board of Trustees'"""
    words = text.strip(" *").rstrip(".").split()
    out = []
    for n, word in enumerate(words):
        lower = word.lower()
        out.append(lower if n and lower in SMALL_WORDS else lower[:1].upper() + lower[1:])
    return " ".join(out)


def contents_titles(lines):
    """Chapter titles from the table of contents near the top (the body
    sometimes wraps a long title onto a second line)."""
    titles = {}
    for line in lines[:3000]:
        match = CONTENTS_LINE.match(line)
        if match and match.group(1) not in titles:
            titles[match.group(1)] = match.group(2)
    return titles


def clean(lines):
    """Tidy body lines: no-break spaces, trailing spaces, image links, extra blank lines."""
    out = []
    for line in lines:
        line = line.replace(" ", " ").rstrip()
        if BARE_LINK.match(line):
            continue
        if not line and (not out or not out[-1]):
            continue
        out.append(line)
    while out and not out[-1]:
        out.pop()
    return out


def split_chapters(text):
    """Every chapter in the code: a list of dicts with number, title, text
    (None for a repealed or reserved chapter), and section count."""
    lines = text.replace("\r\n", "\n").split("\n")
    titles = contents_titles(lines)
    starts = [i for i, l in enumerate(lines) if CHAPTER_LINE.match(l)]
    chapters = []
    for n, start in enumerate(starts):
        end = starts[n + 1] if n + 1 < len(starts) else len(lines)
        number = CHAPTER_LINE.match(lines[start]).group(1)
        title = nice_title(titles.get(number) or lines[start + 1])
        body = lines[start + 2:end]

        # Join a heading that wraps onto a second line
        joined, i = [], 0
        while i < len(body):
            line = body[i]
            stripped = line.strip()
            if (SECTION_START.match(stripped) and stripped == stripped.upper()
                    and not stripped.endswith(".") and i + 1 < len(body)
                    and body[i + 1].strip().endswith(".")
                    and body[i + 1].strip() == body[i + 1].strip().upper()
                    and is_heading(f"{stripped} {body[i + 1].strip()}")):
                joined.append(f"{stripped} {body[i + 1].strip()}")
                i += 2
                continue
            joined.append(line)
            i += 1
        body = joined

        # Sections of this chapter start with its number: "22.03 ..."
        heads = [i for i, l in enumerate(body)
                 if is_heading(l) and SECTION_START.match(l.strip()).group(1) == number]
        text_lines = [f"# Chapter {number} - {title}", ""]
        if heads:
            intro = clean(body[:heads[0]])
            if intro and not any(re.match(rf"^\s*{re.escape(number)}\.\d", l)
                                 or re.search(rf"\s{{3,}}{re.escape(number)}\.\d", l) for l in intro):
                text_lines += intro + [""]   # real text before the first section (not the section list)
            for h, start_line in enumerate(heads):
                stop = heads[h + 1] if h + 1 < len(heads) else len(body)
                num, sub, name = SECTION_START.match(body[start_line].strip()).groups()
                text_lines += [f"## {num}.{sub} {nice_title(name)}", ""]
                text_lines += clean(body[start_line + 1:stop]) + [""]
        else:
            content = clean(body)
            if not content or (EMPTY_CHAPTER.match(content[0].strip()) and len(content) <= 2):
                chapters.append({"number": number, "title": title, "text": None, "sections": 0})
                continue
            text_lines += content + [""]
        chapters.append({"number": number, "title": title,
                         "text": "\n".join(text_lines).rstrip() + "\n", "sections": len(heads)})
    return chapters


def chapter_numbers(spec):
    """'22' or '22,23' or '20-26' -> a test for chapter numbers (None = every chapter)."""
    if not spec:
        return None
    wanted = []
    for part in spec.split(","):
        part = part.strip()
        if "-" in part:
            low, high = part.split("-", 1)
            wanted.append((int(low), int(high)))
        elif part:
            wanted.append((int(part), int(part)))

    def match(number):
        digits = int(re.match(r"\d+", number).group())
        return any(low <= digits <= high for low, high in wanted)
    return match
