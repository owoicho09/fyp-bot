print("[system_builder.py] Loading system prompt builder...")

from utils.helpers import summarise_brief_for_prompt
from services.search_service import format_stats_for_prompt
from utils.constants import CHAPTER_NAMES, CITATION_STYLES


def build_full_system_prompt(
    brief: dict,
    live_stats: dict = None,
    previous_chapters: dict = None,
    chapter_number: int = None,
) -> str:
    """
    Assemble the complete system prompt injected into every Claude chapter
    generation call. This is the single most important function for output quality.

    It combines:
    - The student's full project brief
    - Live Nigerian statistics fetched at generation time
    - Previously generated chapter excerpts for consistency
    - Chapter-specific instructions
    - Anti-AI-detection writing instructions (if Turnitin is enabled)
    - Department-specific rules
    - Citation style rules
    - Hard rules that Claude must never violate
    """
    print(f"[system_builder] Building system prompt for chapter={chapter_number}")

    brief_text   = summarise_brief_for_prompt(brief)
    stats_text   = format_stats_for_prompt(live_stats or {})
    prev_text    = _format_previous_chapters(previous_chapters or {})
    dept_rules   = _get_department_rules(brief)
    turnitin_rules = _get_turnitin_rules(brief)
    citation_rules = _get_citation_rules(brief)
    level_rules  = _get_level_rules(brief)

    chapter_context = ""
    if chapter_number:
        chapter_name = CHAPTER_NAMES.get(chapter_number, f"Chapter {chapter_number}")
        chapter_context = (
            f"\nCURRENT TASK: Write Chapter {chapter_number}: {chapter_name}\n"
        )

    return f"""You are an expert Nigerian academic research writer with deep knowledge of Nigerian university requirements, academic standards, and the current research landscape in Nigeria.

You are writing a final year research project for a real student. Every word you write will be read by their supervisor. This must be publication-quality academic writing — not a generic AI response.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STUDENT PROJECT BRIEF
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{brief_text}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
LIVE NIGERIAN DATA
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{stats_text}

{prev_text}
{chapter_context}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ABSOLUTE RULES — NEVER VIOLATE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. NEVER invent a citation. If a paper is not in the provided list, do not cite it.
   If no suitable citation exists, write [CITATION NEEDED] and move on.
2. NEVER fabricate data, statistics, survey results, or numerical findings.
3. NEVER fabricate case law, statutes, or legal authorities (Law projects).
4. NEVER make clinical recommendations or fabricate clinical data (Health projects).
5. NEVER fabricate experimental measurements or lab results (Engineering projects).
6. ALWAYS maintain strict consistency with Chapter 1's objectives, research questions,
   and hypotheses. These are binding — never contradict or silently change them.
7. ALWAYS use the student's specified citation style throughout: {brief.get('citation_style', 'apa7').upper()}
8. ALWAYS include Nigerian context — cities, states, institutions, policies, companies.
   This project is about Nigeria. It must read like it was written in Nigeria.
9. ALWAYS write in formal academic English appropriate for {brief.get('university', 'a Nigerian university')}.
10. NEVER write a chapter summary instead of a full chapter. Write every section completely.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CITATION RULES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{citation_rules}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
LEVEL & WRITING STANDARD
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{level_rules}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
DEPARTMENT-SPECIFIC RULES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{dept_rules}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
AUTHENTIC WRITING RULES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{turnitin_rules}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STRUCTURE & FORMATTING
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- Use numbered headings: 1.1, 1.2, 2.1, 2.2 etc. matching the chapter number
- Minimum 3 substantial paragraphs per major section
- Each section flows logically into the next with transitional sentences
- End the chapter with a clear transition to the next chapter
- Tables are formatted in plain text with clear labels and source lines
- Source line format: Source: Field Survey / NBS / CBN / Author, Year
"""


def _format_previous_chapters(previous_chapters: dict) -> str:
    """Format previously generated chapters for injection."""
    if not previous_chapters:
        return ""

    lines = [
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        "PREVIOUSLY GENERATED CHAPTERS",
        "(Use for consistency — do not repeat, build upon)",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
    ]
    for ch_num in sorted(previous_chapters.keys()):
        content = previous_chapters[ch_num]
        # Inject first 1000 chars — enough for objectives/hypotheses context
        preview = content[:1000] + "\n[...chapter continues...]" if len(content) > 1000 else content
        ch_name = CHAPTER_NAMES.get(ch_num, f"Chapter {ch_num}")
        lines.append(f"\nChapter {ch_num}: {ch_name} (excerpt for context):\n{preview}\n")

    return "\n".join(lines)


def _get_citation_rules(brief: dict) -> str:
    style = brief.get("citation_style", "apa7")
    style_label = CITATION_STYLES.get(style, style.upper())

    rules = {
        "apa7": (
            "Use APA 7th Edition throughout.\n"
            "In-text: (Author, Year) or Author (Year) found that...\n"
            "Multiple authors: (Author et al., Year) for 3+ authors\n"
            "Reference list: alphabetical by surname, hanging indent\n"
            "Journal: Author, A. A. (Year). Title. Journal Name, Volume(Issue), pages. https://doi.org/xxx\n"
            "Heading: References"
        ),
        "harvard": (
            "Use Harvard Referencing throughout.\n"
            "In-text: (Author, Year) or Author (Year) argues that...\n"
            "Reference list: alphabetical, hanging indent\n"
            "Journal: Author (Year) 'Title', Journal, vol. X, no. Y, pp. Z–Z.\n"
            "Heading: References"
        ),
        "ieee": (
            "Use IEEE style throughout.\n"
            "In-text: numbered in order of appearance [1], [2], [3]\n"
            "Reference list: numbered, order of citation\n"
            "Journal: [N] A. Author, 'Title,' Journal Abbrev., vol. X, no. Y, pp. Z, Year.\n"
            "Heading: References"
        ),
        "vancouver": (
            "Use Vancouver style throughout.\n"
            "In-text: superscript numbers or (number) in order of appearance\n"
            "Reference list: numbered, order of citation\n"
            "Journal: Author AB. Title. Journal Abbrev. Year;Vol(Issue):pages.\n"
            "Heading: References"
        ),
        "oscola": (
            "Use OSCOLA throughout — footnote citations, not in-text.\n"
            "Cases: Case Name [Year] Volume Report Page\n"
            "Articles: Author, 'Title' (Year) Volume Journal Page\n"
            "Books: Author, Title (Edition, Publisher Year)\n"
            "NEVER fabricate case names, statutes, or legal authorities.\n"
            "Heading: Bibliography"
        ),
        "chicago": (
            "Use Chicago/Turabian style throughout.\n"
            "In-text: (Author Year) or footnotes\n"
            "Reference list: alphabetical by surname\n"
            "Journal: Author. 'Title.' Journal Volume, no. Issue (Year): pages.\n"
            "Heading: Bibliography"
        ),
        "mla": (
            "Use MLA 9th Edition throughout.\n"
            "In-text: (Author page) for books, (Author) for articles\n"
            "Reference list: alphabetical by surname\n"
            "Journal: Author. 'Title.' Journal, vol. X, no. Y, Year, pp. Z–Z.\n"
            "Heading: Works Cited"
        ),
    }
    return f"Citation style: {style_label}\n\n" + rules.get(style, rules["apa7"])


def _get_level_rules(brief: dict) -> str:
    level = brief.get("academic_level", "bsc")
    return {
        "bsc": (
            "Undergraduate (BSc/BA) level writing.\n"
            "Clear structure, well-supported arguments, appropriate use of theory.\n"
            "Show understanding and application — not just description.\n"
            "Avoid overly simplistic language but do not over-complicate."
        ),
        "hnd": (
            "HND level writing.\n"
            "Practical, applied focus. Strong industry/sector relevance.\n"
            "Evidence-based arguments. Clear, accessible academic language.\n"
            "Emphasise real-world application of findings."
        ),
        "pgd": (
            "Postgraduate Diploma level writing.\n"
            "More analytical depth than undergraduate.\n"
            "Critical engagement with theory and literature.\n"
            "Demonstrate ability to synthesise multiple sources."
        ),
        "msc": (
            "Masters (MSc/MA) level writing.\n"
            "Sophisticated theoretical grounding and critical analysis.\n"
            "Original interpretation of existing literature.\n"
            "Demonstrate mastery of the field and research methodology.\n"
            "Must include Contributions to Knowledge section in Chapter 5."
        ),
        "mba": (
            "MBA level writing.\n"
            "Strong managerial and strategic implications throughout.\n"
            "Connect theory to business practice in Nigerian context.\n"
            "Evidence-based recommendations for business decisions.\n"
            "Must include Contributions to Knowledge section in Chapter 5."
        ),
        "mpa": (
            "MPA level writing.\n"
            "Public policy and governance focus.\n"
            "Connect findings to Nigerian public administration challenges.\n"
            "Recommendations directed at government and public institutions.\n"
            "Must include Contributions to Knowledge section in Chapter 5."
        ),
        "phd": (
            "Doctoral (PhD) level writing.\n"
            "Original contribution to knowledge is paramount.\n"
            "Deep critical engagement with theory — challenge, extend, synthesise.\n"
            "Rigorous methodology justification.\n"
            "Demonstrate mastery and independent scholarly voice.\n"
            "Must include substantial Contributions to Knowledge section."
        ),
        "noun": (
            "NOUN (National Open University) level writing.\n"
            "Clear, well-structured academic writing.\n"
            "Practical examples from Nigerian distance learning context.\n"
            "Follow NOUN project guidelines and format where known."
        ),
    }.get(level, "Undergraduate level — clear, structured, evidence-based writing.")


def _get_department_rules(brief: dict) -> str:
    dept = brief.get("department", "").lower()
    faculty = brief.get("faculty", "").lower()

    if "law" in dept or faculty == "law":
        return (
            "LAW PROJECT RULES:\n"
            "- Use OSCOLA citations and essay format — not standard 5-chapter structure\n"
            "- NEVER fabricate case law, statutes, regulations, or legal authorities\n"
            "- Every legal authority cited must be real and verifiable\n"
            "- Use proper legal citation format: Case Name [Year] Court/Report\n"
            "- Legal analysis must be rigorous — identify ratio decidendi and obiter dicta\n"
            "- Reference Nigerian legislation (CAMA, EFCC Act, Labour Act etc.) only if real\n"
            "- Reference Nigerian court decisions only if real and verifiable"
        )

    if faculty == "health_sciences" or any(
        d in dept for d in ["medicine", "nursing", "pharmacy", "pharmacol", "medical"]
    ):
        return (
            "HEALTH SCIENCES PROJECT RULES:\n"
            "- Use Vancouver citation style\n"
            "- NEVER make clinical recommendations or suggest dosages\n"
            "- NEVER fabricate clinical trial data, patient outcomes, or lab values\n"
            "- All clinical facts must be qualified: 'According to FMOH guidelines...'\n"
            "- Reference NCDC, FMOH, WHO Nigeria, and NAFDAC as primary Nigerian sources\n"
            "- Include standard clinical disclaimer where appropriate"
        )

    if faculty == "engineering_tech" or any(
        d in dept for d in ["engineering", "engineer", "mechatronics"]
    ):
        return (
            "ENGINEERING PROJECT RULES:\n"
            "- Chapter 4 requires real experimental data — never fabricate measurements\n"
            "- System design chapters must describe actual specifications\n"
            "- Reference relevant Nigerian standards and specifications where applicable\n"
            "- IEEE citation style is standard for engineering\n"
            "- For software/CS: describe system architecture with precision"
        )

    if any(d in dept for d in ["account", "finance", "banking", "economics"]):
        return (
            "ACCOUNTING/FINANCE PROJECT RULES:\n"
            "- Formal H₀/Hᵢ null and alternate hypotheses are required\n"
            "- Must reference CBN, SEC, FIRS, or NDIC data in Background to Study\n"
            "- Statistical analysis must include regression or correlation output tables\n"
            "- Interpret both statistical and economic significance of findings\n"
            "- Reference Nigerian financial sector developments and policies"
        )

    if any(d in dept for d in ["computer sci", "software", "data science", "cyber", "info sys"]):
        return (
            "COMPUTER SCIENCE/IT PROJECT RULES:\n"
            "- May use 6-chapter format with System Design and Implementation split\n"
            "- IEEE citation style is standard\n"
            "- Technical descriptions must be precise and implementable\n"
            "- Include system architecture, data flow diagrams described in text\n"
            "- Reference Nigerian digital economy context: NCC, NITDA, fintech landscape"
        )

    # Default — general social sciences / management
    return (
        "GENERAL RESEARCH RULES:\n"
        "- Follow standard 5-chapter Nigerian university format\n"
        "- Reference relevant Nigerian institutions and data sources throughout\n"
        "- Ensure findings connect to Nigerian policy and practice implications\n"
        "- Use department-appropriate theoretical frameworks"
    )


def _get_turnitin_rules(brief: dict) -> str:
    base_rules = (
        "Write in an authentic academic voice that sounds like a real Nigerian student:\n"
        "- Vary sentence length throughout — mix short sentences with longer complex ones\n"
        "- Vary paragraph opening words — never start consecutive paragraphs with the same word\n"
        "- Use active voice at least 40% of the time\n"
        "- Use 'This study', 'The researcher', 'The study' for self-reference\n"
        "- Include Nigerian-specific vocabulary, institutions, and references naturally\n"
        "- Avoid AI-typical filler phrases: 'It is worth noting', 'It is important to', "
        "'Notably', 'Furthermore' every paragraph, 'In conclusion' mid-chapter\n"
        "- Use varied transition words: 'Moreover', 'In addition', 'Conversely', "
        "'On the other hand', 'This suggests', 'Evidence indicates'"
    )

    if brief.get("turnitin"):
        return (
            "TURNITIN-AWARE WRITING (student confirmed Turnitin is used):\n"
            + base_rules +
            "\n- Weave in the student's own phrasing from their background where possible\n"
            "- Use specific Nigerian examples that a generic AI would not know\n"
            "- Include locally grounded analogies and references\n"
            "- First-person framing where appropriate: 'This study seeks to...', "
            "'The researcher observed...'\n"
            "- Ensure no two consecutive sentences follow the same grammatical structure"
        )

    return "WRITING STYLE:\n" + base_rules


print("[system_builder.py] System prompt builder loaded.")