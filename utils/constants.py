print("[constants.py] Loading UI constants...")

# ─── ACADEMIC LEVELS ──────────────────────────────────────────────────────────
ACADEMIC_LEVELS = {
    "bsc":   "BSc / BA (Undergraduate)",
    "hnd":   "HND (Higher National Diploma)",
    "pgd":   "PGD (Postgraduate Diploma)",
    "msc":   "MSc / MA (Masters)",
    "mba":   "MBA",
    "mpa":   "MPA (Master of Public Admin)",
    "phd":   "PhD",
    "noun":  "NOUN (Distance Learning)",
}

# ─── FACULTIES ────────────────────────────────────────────────────────────────
# Student picks faculty from buttons, then TYPES their specific department.
# We never assume what their department covers — they tell us in their own words.
FACULTIES = {
    "social_sciences":  "Social Sciences",
    "management":       "Management Sciences",
    "arts_humanities":  "Arts & Humanities",
    "sciences":         "Natural & Applied Sciences",
    "engineering_tech": "Engineering & Technology",
    "law":              "Law",
    "health_sciences":  "Medicine, Health & Pharmacy",
    "agriculture":      "Agriculture & Veterinary Sciences",
    "education":        "Education",
    "communication":    "Communication & Media Studies",
    "environmental":    "Environmental Sciences",
    "other":            "Other — I will describe it",
}

# ─── RESEARCH DESIGNS ─────────────────────────────────────────────────────────
RESEARCH_DESIGNS = {
    "quantitative": "Quantitative",
    "qualitative":  "Qualitative",
    "mixed":        "Mixed Methods",
    "help_choose":  "Recommend one for my topic",
}

# ─── CITATION STYLES ──────────────────────────────────────────────────────────
CITATION_STYLES = {
    "apa7":      "APA 7th Edition",
    "harvard":   "Harvard",
    "ieee":      "IEEE",
    "vancouver": "Vancouver",
    "oscola":    "OSCOLA (Law)",
    "chicago":   "Chicago / Turabian",
    "mla":       "MLA",
    "not_sure":  "My supervisor will confirm",
}

# ─── FACULTIES THAT TRIGGER AN IMMEDIATE DISCLAIMER ──────────────────────────
# Everything else is reasoned dynamically by Claude from the student's context.
DISCLAIMER_FACULTIES = {
    "law": (
        "⚠️ *Law Project Notice*\n\n"
        "Law projects use OSCOLA citations and essay-style structure — "
        "not the standard 5-chapter format.\n\n"
        "This bot will *never* fabricate case law, statutes, or legal authorities. "
        "Every legal source cited will be real and verifiable. "
        "Confirm every case with your supervisor before submission."
    ),
    "health_sciences": (
        "⚠️ *Health Sciences Notice*\n\n"
        "All clinical facts, drug dosages, diagnostic criteria, and treatment "
        "protocols generated here *must* be verified against current guidelines "
        "by your supervisor before submission. "
        "This bot does not provide clinical recommendations."
    ),
    "engineering_tech": (
        "⚠️ *Engineering Project Notice*\n\n"
        "Chapter 4 requires your actual experimental data, lab results, or "
        "simulation outputs. This bot will structure and write around your data "
        "— but it will *never* fabricate results or measurements."
    ),
}

# ─── STANDARD CHAPTER NAMES (5-chapter Nigerian university format) ────────────
# Claude will adapt this if the student's university uses a different structure.
CHAPTER_NAMES = {
    1: "Introduction",
    2: "Review of Related Literature",
    3: "Research Methodology",
    4: "Data Presentation, Analysis and Discussion of Findings",
    5: "Summary, Conclusion and Recommendations",
}

# Standard sections per chapter — used to guide Claude, not enforce rigidly.
# Claude adapts based on department, level, and supervisor context.
CHAPTER_SECTIONS = {
    1: [
        "Background to the Study",
        "Statement of the Problem",
        "Objectives of the Study",
        "Research Questions",
        "Research Hypotheses",
        "Significance of the Study",
        "Scope of the Study",
        "Limitations of the Study",
        "Definition of Terms",
        "Organisation of the Study",
    ],
    2: [
        "Introduction",
        "Conceptual Framework",
        "Theoretical Framework",
        "Empirical Review",
        "Review of Related Studies",
        "Gap in Literature",
        "Summary of Literature Review",
    ],
    3: [
        "Introduction",
        "Research Design",
        "Area of Study",
        "Population of the Study",
        "Sample Size and Sampling Technique",
        "Instrument for Data Collection",
        "Validity of the Instrument",
        "Reliability of the Instrument",
        "Method of Data Collection",
        "Method of Data Analysis",
    ],
    4: [
        "Introduction",
        "Presentation of Data",
        "Analysis of Data",
        "Test of Hypotheses",
        "Discussion of Findings",
    ],
    5: [
        "Introduction",
        "Summary of Findings",
        "Conclusion",
        "Recommendations",
        "Contributions to Knowledge",
        "Suggestions for Further Studies",
    ],
}

# ─── REFERENCE LIST HEADING BY CITATION STYLE ────────────────────────────────
REFERENCE_HEADINGS = {
    "apa7":      "References",
    "harvard":   "References",
    "ieee":      "References",
    "vancouver": "References",
    "oscola":    "Bibliography",
    "chicago":   "Bibliography",
    "mla":       "Works Cited",
    "not_sure":  "References",
}

# ─── FREE VS PAID CHAPTERS ────────────────────────────────────────────────────
FREE_CHAPTERS = {1, 2}
PAID_CHAPTERS = {3, 4, 5}

# ─── TECHNICAL LIMITS ─────────────────────────────────────────────────────────
TELEGRAM_MAX_LENGTH = 4096
MIN_TOPIC_WORDS     = 5
MAX_TOPIC_WORDS     = 60
MAX_TOPIC_RETRIES   = 2

# ─── INTAKE CONVERSATION STATES ───────────────────────────────────────────────
# These are the states the onboarding ConversationHandler moves through.
# Defined here so both onboarding.py and bot.py can import them without
# circular imports.
(
    ASK_LEVEL,
    ASK_FACULTY,
    ASK_DEPARTMENT,
    ASK_UNIVERSITY,
    ASK_TOPIC_OPEN,
    ASK_FOLLOWUP_1,
    ASK_FOLLOWUP_2,
    ASK_FOLLOWUP_3,
    ASK_SUPERVISOR,
    ASK_RESEARCH_DESIGN,
    ASK_CITATION,
    CONFIRM_BRIEF,
    AWAIT_CHAPTER_1,
) = range(13)

print(
    f"[constants.py] Loaded "
    f"{len(ACADEMIC_LEVELS)} levels, "
    f"{len(FACULTIES)} faculties, "
    f"{len(CITATION_STYLES)} citation styles, "
    f"{len(CHAPTER_NAMES)} chapters defined."
)