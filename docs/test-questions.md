# Test Questions

Questions with known right answers, used to check whether a change actually improves the assistant. Run all of them before and after each change and note the results.

**Scoring:** ✅ right answer and right source · ⚠️ partly right, or right answer with wrong or extra sources · ❌ wrong, made up, or missed

**Method (updated Nov 4):** answers vary from run to run. The agent writes a fresh search query each time, and the model doesn't answer identically. Ask each question **2–3 times** and record consistency (e.g., "✅ 3/3", "✅ 1/3"). For wrong answers, save the "How I found this" contents to tell search problems (wrong passages) from answer problems (right passages, wrong answer). Copy the whole answer, including its "Sources:" list.

## The question set (Nick's 10, Nov 2, 2026)

| # | Question | What a right answer says | In the documents? | Notes |
|---|---|---|---|---|
| 1 | When is the next library board meeting? | Ideally: no confirmed date found; the Library Board usually meets the third Monday of the month (so likely Nov 16); check the city meeting calendar | Only the rule (Boards & Commissions page: "usually meets the third Monday"; bylaws: ten meetings a year, dates set at the annual meeting); no official calendar of upcoming meetings | **Source gap** (CivicClerk). "Couldn't find it" is acceptable; must never use another board's schedule. **A confident wrong date is the worst outcome.** |
| 2 | Does the library offer language learning classes? | Yes. ESL class (Tuesdays) and Mango language learning (online) | Yes (Resources page; Digital Resources video). The ESL class was only in the calendar snapshot, removed Nov 25. | Until the RSS events tool, a right answer names the online options (Mango, LingQ) and doesn't claim an ESL class. |
| 3 | When is the next storytime? | Next date from the calendar | **No, since Nov 25** (calendar snapshot removed: WhoFi's robots.txt blocks automated access) | **Source gap** until the RSS events tool. Right answer for now: "couldn't find" plus "ask library staff." Must not present StoryWalk as storytime or give a date. |
| 4 | Can I reserve a study room online? | Yes, through the Room Reservations page | Yes (Room Reservations page; policy manual) | The Proctoring policy also says students book study rooms "using the library's online booking software available on the library website." Check whether that's still accurate. |
| 5 | Who is on the library board? | The trustees' names (Scott Kramer, Brandy Greene, Scott Clemons, …) | Yes (Boards & Commissions page) | |
| 6 | What is the StoryWalk? | Description from the web page | Yes (web page) | |
| 7 | Can I get something notarized? | Yes, with exceptions (no subpoenas, wills, or estates; call ahead) | Yes (staff FAQ) | |
| 8 | Can I fax something at the library? | Yes, at no cost | Only inside the Proctoring policy (Policy Manual p. 23) | **Source issue:** fax is documented only in one sentence of the exam-proctoring section, so answers tie it to proctoring. Fix at the source (policy manual or services page), not the FAQ. |
| 9 | How much does it cost to print? | $3 free per day, then $.10/page black and white, $.50/page color; scanning to email is free | Yes (Policy Manual p. 10, "Equipment Use") | |
| 10 | What about programs for kids? | Specific programs from the calendar: Baby, Toddler, and Saturday Storytime, Lego Creations, Super Tuesday, T&T | **Partly, since Nov 25:** ongoing programs on web pages (1000 Books Before Kindergarten, Summer Reading, StoryWalk); the dated programs were only in the calendar snapshot, removed Nov 25 | Full answer waits for the RSS events tool. For now: the ongoing programs, with no event dates. |

Earlier questions, still worth running:

| # | Question | What a right answer says |
|---|---|---|
| A | Where can I reserve a meeting room? | The Room Reservations page: book online, up to 3 hours, first-come, first-served, nonprofit/educational/civic use |
| E | What did the city council discuss about the pool? | **Routing test:** should search meeting records. |
| F | Did the library board change the meeting room rules, and what are they now? | **Routing test:** should search both (meetings for the discussion, official for the current rule). **Also a stick-to-the-documents test:** the manual calls the board "advisory" (p. 4) but lists policies as "Reviewed/Approved" by it, and the director has final authority over meeting rooms (p. 21). A good answer reports this without deciding who has authority. |
| C | Can I renew my driver's license at the library? | **No.** The kiosk is gone; renewals are handled online (staff FAQ, added Nov 13). |
| D | Can I renew my license? (ambiguous) | Ideally asks: library card or driver's license? Test case for the planned "ask when unclear" rule. On Nov 13 it assumed library card. |
| B | Can I complain about a book in the collection? | **No.** No reconsideration process, and titles aren't removed because someone objects. Must not invent a complaint form or Board process. |

Not-found checks (the documents don't cover these; the answer should start "I couldn't find anything about…" and suggest asking staff, never "no"):

| # | Question | Notes |
|---|---|---|
| N1 | Can I rent a telescope? | **Weak test:** this is the worked example in the system prompt. Replacement still to be chosen (e.g., "Do you sell stamps?"; Nick to confirm it's in no document). "Can I renew my license?" was tried Nov 13 but now has an FAQ answer. |
| N2 | Do you offer passport photos? | |

## Results log

| Date | Change tested | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | Score |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Nov 2, 2026 | Baseline (gpt-oss-120b, original search) | ⚠️ | ❌ | ✅ | ✅ | ⚠️ | ✅ | ❌ | ⚠️ | ⚠️ | ⚠️ | 3 ✅ · 5 ⚠️ · 2 ❌ |
| Nov 2, 2026 | Quick fixes ($ display, today's date, "not found isn't no") + ESL on calendar + boards page | ✅ | ✅ | ✅ | ✅ | ⚠️ | ✅ | ❌ | ⚠️ | ✅ | ⚠️ | 6 ✅ · 3 ⚠️ · 1 ❌ |
| Nov 2, 2026 | Spot check (Nick) | | | | | | | | ✅ | | | Fax answered correctly from the policy manual |
| Nov 4, 2026 | Hybrid search + reranker + passages to model (PR #2), plus FAQ, web cleanup, heading chunks | ❌ | ✅ | ❌ | ❌ | ✅ | ✅ | ✅ | ⚠️ | ❌ | ⚠️ | 4 ✅ · 2 ⚠️ · 4 ❌ |
| Nov 4, 2026 | Re-test of regressed questions, with "How I found this" (PR #3) and date rule | ✅* | | ✅ | ✅ | | | | | ✅ | | *Q1 said "couldn't find it" (acceptable: source gap) |
| Nov 4, 2026 | **Full baseline, 2 runs each** (main at f07ba85: hybrid search, reranker, "How I found this," date rule) | ❌❌ | ✅✅ | ✅✅ | ⚠️⚠️ | ✅✅ | ✅✅ | ❌❌ | ⚠️⚠️ | ✅ ? | ⚠️⚠️ | **5 ✅ · 3 ⚠️ · 2 ❌** (scored by Claude from Nick's notes; Q9 run 2 not captured; N1/N2 not recorded) |
| Nov 13, 2026 | Notary FAQ wording + short-query tool description + no citation marks + Room Reservations page fixed | | | | ✅ | | | ✅ | | | | Q4 ran on the old index (manual not yet live); Q7 ✅ after the query fix. Also: "Sources:" list ✅, citation marks gone ✅, N2 ✅. Driver's license (C) ❌ in the app only because the app was still on the old index (search finds it #1). |
| Nov 16, 2026 | Official documents and meeting transcripts searched separately (PR #4) + example queries in tool descriptions | ✅ | | | ✅ | | | ✅ | | ✅ | ✅ | Q1 first said "couldn't find" twice (query dropped "library"); ✅ after example queries. Q10 better (1000 Books, Summer Reading); the program Nick thought was discontinued is annual, so ✅. Pool (E) routed to meeting records. |

**Baseline notes (Nick):** Q1 gave a good date but in the past. Q2 said no, but the library does offer them. Q3 correct: tomorrow, 11/3. Q6 an excellent answer. Q7 said no, but the library does notarize. Q8 had no info. Q9 said "3 worth of copies" instead of "$3 worth." Q10 had good language but didn't name the most common programs.

**Quick-fix round notes (Nick):** Q1 good, but needs more info moving forward. Q2 correct, good answer. Q9 correct, good answer. Q5 still had no data on who. Q7 still said no. Q8 still had no info. Q10 picked odd responses, mostly from web pages rather than the calendar.

**Nov 4 round notes (Nick):** "Feels like we went backwards in quality."
- Q1 bad: grabbed the wrong commission. Q2 correct, great answer. Q3 bad: skipped over upcoming events. Q4 bad: added a bit about proctoring exams and said it was the same system. Q5 great answer. Q6 good answer. Q7 great answer. Q8 right, but saying it comes from the Proctoring Policy would make people doubt it. Q9 bad: couldn't find an answer. Q10 right, but only highlighted the summer reading program.

**Nov 4 re-test (with "How I found this"):**
- **Q3 storytime ✅:** "The next storytime is Friday, November 6, 2026, from 10:30 a.m. to 11:00 a.m. It's an in-person Toddler Storytime for children ages 0-5." Searched for "storytime schedule next storytime North Liberty Library"; passages were in relevance order, not date order (Nov 24, Nov 6, Dec 1, …), and some calendar chunks start mid-event with the title cut off.
- **Q4 study room ✅:** searched for "reserve study room online North Liberty Library"; passages: Room Reservations page (opening paragraph only), Meeting Room Use Policy, Digital Resources video, Proctoring policy, Meeting Room policy p. 21. The Room Reservations "Reservation Details" section is a separate chunk (from the heading split) and wasn't included.
- **Q9 printing ✅:** searched for "printing cost"; the "$3 free" Equipment Use passage was #1; only 3 passages passed the cutoff (the other two were board-meeting talk about e-book costs, correctly ignored).
- **Q1 next board meeting:** searched for "library board meeting date next meeting"; got only meeting transcripts (Tree & Storm Water and Parks "next meeting" announcements, past Library Board meetings). Answered "couldn't find it," which is acceptable, and it didn't use another board's date. The Boards & Commissions "third Monday" chunk wasn't retrieved; transcripts that say "next meeting" crowd it out.

**Nov 4 full baseline (2 runs each): Nick's notes and diagnosis**
- **Consistency:** every question scored the same on both runs. The misses are systematic, not random, which makes them fixable.
- **Q1 ❌❌ (Nick: "Bad data on both, drew on another commission"):** both runs said "November 11, 2026 at 7:00 p.m." with confidence. Nov 11 is a Wednesday; the Library Board usually meets the third Monday (Nov 16). Worse than the earlier re-test ("couldn't find"). Why: the "third Monday" sentence sits inside the trustees chunk (`web_9`, mostly names), which wins for "who is on the board" but loses to transcripts full of "next meeting" talk for "when is the next meeting." Transcripts also use relative dates ("the 11th," "next month") that mean something different months later. Q5 even answered the schedule better than Q1 did (Nick's observation).
- **Q2 ✅✅:** run 1 better worded. Run 2 included `【1】`/`【3】` citation marks.
- **Q3 ✅✅:** Friday, Nov 6, Toddler Storytime. Run 2 also listed later dates (Nov 17, Nov 24).
- **Q4 ⚠️⚠️:** asked as "can I reserve a study room." Both answers mixed in the meeting-room policy ("first-come, first-served," four reservations at once, no private parties) and never said *how* to book (online). Full of citation marks like `【2†L19-L22】`.
- **Q5 ✅✅:** all six trustees with terms, plus "third Monday."
- **Q6 ✅✅.**
- **Q7 ❌❌ (Nick: "missed the FAQ"):** both "I couldn't find anything about notarization services." The FAQ **is** in the index (checked). Keyword search finding: the stemmer (the step that trims words to their root so "faxing" matches "fax") trims "notarized," "notarize," and "notarization" to `notar` but "notary" to `notari`, so they don't match. A query of "notarization services" ranks the FAQ #1 in keyword search; "notary services at the library" ranks it only #8 with a near-zero score. Needs the "How I found this" contents to confirm the agent's query and whether it's a search miss or an answer miss.
- **Q8 ⚠️⚠️ (Nick: "it's actually wrong to say it's part of that process"):** free is right, but both answers tied faxing to proctoring. The only fax passage in the index is the Proctoring policy ("Faxing services are provided at no cost"), so the model's reading is understandable. Fix (revised Nov 10): at the source, not the FAQ.
- **Q9 ✅ / ?:** run 1 correct ($3 free, then $.10 and $.50). Run 2 slot held a fax answer (copy/paste slip).
- **Q10 ⚠️⚠️:** Summer Reading kickoff, family/intergenerational programs, teen board-game nights; no storytimes or Lego. Keyword search for "kids programs at the library" returns only transcripts (a Library Board meeting about 55+ and intergenerational programs, City Council, Parks); the calendar snapshot doesn't make the top 8.
- **New issue: citation marks.** `【1】`, `【2†L19-L22】`, `【4†source】` appeared in Q2, Q4, and Q10. These are gpt-oss's trained habit (it learned to cite web-browsing results this way) and mean nothing to patrons. Also, none of the pasted answers end with a "Sources:" list; check whether that's missing in the app or just wasn't copied.
- **Testing note:** Claude's workspace couldn't download the models from Hugging Face on Nov 4, so full search checks (meaning search + reranker) must run in Codespaces. Keyword-only checks still work there.

**Conclusions:**
- The first Nov 4 failures on Q3, Q4, Q9 most likely reflect run-to-run variation; they couldn't be diagnosed because "How I found this" didn't exist yet. Repeated runs are now part of the method.
- Search and the cutoff are working as designed on these questions: right passages on top, junk dropped.
- **Nov 4 full baseline:** two themes. (1) **Meeting transcripts crowd out official sources** (Q1, Q10), and in Q1 that now produces a confident wrong date. (2) **Answers to service questions depend on the staff FAQ** (Q4, Q7, Q8), and FAQ entries need the words patrons actually use.
- **Remaining improvements, in order (revised Nov 10):** (1) notary FAQ entry: `##` heading and an "Also asked as" line (Q7); (2) separate meeting transcripts from official documents (Q1, Q10, helps Q4); (3) a "source line" on each chunk (Q4: keeps "Reservation Details" with the Room Reservations page); (4) a prompt line against citation marks; (5) the RSS events tool for calendar questions. Q8 (fax) waits on a source fix.
- **Nov 10 (Nick):** the FAQ is only for information that exists nowhere else. Study rooms and fax are in official documents, so no FAQ entries for them; duplicating would create a second version to keep current. Theme (2) above is corrected: Q4 is a search problem and Q8 is a source-wording problem; only Q7 is an FAQ question.
- **Source typo found:** the Room Reservations page says "up to four (3) reservations."
- **Lesson:** `check_search.py` tests search with our exact wording, but the app adds two more steps (the agent's own query and the model's answer), so end-to-end tests are essential. PR #2 also bundled several changes, which made the first failures hard to attribute.
- **Nov 13 lessons:** (1) The assistant writes its own search query; padding it with "North Liberty Library" buried the FAQ, while `check_search.py` with Nick's wording found it at #1. **Always compare the app's "Searched for" line with `check_search.py` on that exact query.** (2) An index-only push isn't picked up until the app reloads; if "How I found this" cites a deleted file, the app is on the old index.
- **Lesson (keyword search):** keyword search only matches words that trim to the same root. Writing FAQ entries with the common variants ("notary," "notarize," "notarization") is a lasting fix that also helps patrons scanning the FAQ.

## Diagnosis and plan (Nov 2)

1. **Display bug (Q9).** ✅ Fixed.
2. **Says "no" when it should say "I couldn't find it" (Q7).** ✅ Fixed with stronger wording plus the staff FAQ.
3. **Doesn't know today's date (Q1).** ✅ Fixed (plus Nov 4 rule: check all passage dates; passages aren't in date order).
4. **Search misses (Q5).** ✅ Fixed Nov 4.
5. **Content gaps (Q7 notary).** ✅ Staff FAQ.

**Calendar data note:** the ESL listing says 3:00–4:00 pm, but its description says "every Tuesday evening at 7pm." Fix in WhoFi.
