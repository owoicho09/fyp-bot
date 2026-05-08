print("[intake_agent.py] Loading intake agent prompts...")


def get_intake_welcome_message(first_name: str) -> str:
    """
    The very first message the student sees after /start.
    Sets the tone — warm, smart, professional.
    """
    return (
        f"Hello {first_name}! 👋 Welcome to *FYP Mentor*.\n\n"
        "I'm your AI research assistant. I'll help you write your final year "
        "project chapter by chapter — with real verified citations, Nigerian "
        "data, and writing that sounds like *you* wrote it.\n\n"
        "*Chapters 1 and 2 are completely free.*\n\n"
        "Let's start by understanding your project. "
        "First — what level are you?"
    )


def get_faculty_prompt_message() -> str:
    return (
        "Which faculty are you in?\n\n"
        "Pick the closest match — you'll describe your specific "
        "department in your own words after."
    )


def get_department_prompt_message(faculty: str) -> str:
    return (
        f"Good. Now tell me your *specific department* and any specialisation.\n\n"
        "For example:\n"
        "• _Accounting — forensic accounting focus_\n"
        "• _Computer Science — software engineering track_\n"
        "• _Nursing Science — community health_\n"
        "• _Civil Engineering — structural_\n\n"
        "Just type it:"
    )


def get_university_prompt_message() -> str:
    return (
        "What university are you in?\n\n"
        "Type the full name — for example:\n"
        "• _University of Lagos_\n"
        "• _Covenant University_\n"
        "• _Ahmadu Bello University_"
    )


def get_topic_opening_message() -> str:
    return (
        "Now the most important part — your *research topic and what you're trying to find out*.\n\n"
        "Don't worry about getting it perfect. Just tell me:\n"
        "• What is your topic area?\n"
        "• What problem are you trying to solve or understand?\n"
        "• Who or what are you studying?\n\n"
        "You can *type* your answer or send a *🎙️ voice note* — "
        "I'll transcribe and understand either.\n\n"
        "Take your time and be as detailed as you can:"
    )


def get_voice_note_processing_message() -> str:
    return "🎙️ Got your voice note — transcribing now..."


def get_voice_note_error_message() -> str:
    return (
        "I had trouble processing that voice note. "
        "Could you try again or type your answer instead?"
    )


def get_followup_transition_message() -> str:
    return (
        "Good — I'm getting a clear picture of your project. "
        "A few more questions to make sure the output is exactly right for you."
    )


def get_research_design_prompt_message(recommendation: str = None) -> str:
    if recommendation:
        return (
            f"Based on your topic, here's my recommendation:\n\n"
            f"_{recommendation}_\n\n"
            "Does this work for you, or would you prefer a different approach?"
        )
    return (
        "What research design do you want to use?\n\n"
        "If you're not sure, pick *Recommend one for my topic* "
        "and I'll suggest the best fit."
    )


def get_citation_prompt_message() -> str:
    return (
        "Which citation style does your department use?\n\n"
        "If your supervisor hasn't confirmed yet, pick the last option "
        "and I'll use the standard style for your discipline."
    )


def get_turnitin_prompt_message() -> str:
    return (
        "Does your university or department use *Turnitin* or any "
        "other plagiarism checker?\n\n"
        "This helps me calibrate the writing style to be more "
        "authentically student-like."
    )


def get_supervisor_prompt_message() -> str:
    return (
        "Almost done. Does your supervisor have any known preferences "
        "or requirements I should know about?\n\n"
        "For example:\n"
        "• _Strict about word count per chapter_\n"
        "• _Prefers Harvard citations_\n"
        "• _Requires a specific chapter structure_\n"
        "• _Our school uses a custom title page format_\n\n"
        "Type what you know, or tap *Skip* if you're not sure yet:",
    )


def get_brief_complete_transition() -> str:
    return (
        "I have everything I need to build your project properly. "
        "Let me put together your project brief for you to confirm..."
    )


def get_brief_confirmation_message(brief_card: str) -> str:
    return (
        f"{brief_card}\n\n"
        "Does this look right? If everything is correct, tap below to "
        "generate your first chapter. If your topic needs adjusting, "
        "tap *Change my topic*."
    )


def get_topic_too_short_message() -> str:
    return (
        "That's a bit too brief for a research topic. "
        "A good topic needs at least 5–8 words and a clear research angle.\n\n"
        "Try adding: *who* you're studying, *where* (Nigerian state/city), "
        "and *what* you're measuring or examining.\n\nPlease try again:"
    )


def get_topic_too_long_message() -> str:
    return (
        "That topic is quite long. Try to keep it under 60 words — "
        "be specific but concise.\n\nPlease try again:"
    )


def get_topic_looks_like_question_message() -> str:
    return (
        "That looks like a research question rather than a topic title. "
        "A topic is a statement, not a question.\n\n"
        "*Example question (wrong):* _How does inflation affect SMEs in Lagos?_\n"
        "*Example topic (right):* _Effect of inflation on small and medium enterprises "
        "in Lagos State, Nigeria (2019–2024)_\n\n"
        "Please rephrase it as a topic title:"
    )


def get_validation_failed_message(feedback: str, suggestions: list) -> str:
    suggestions_text = "\n".join(f"• _{s}_" for s in suggestions)
    return (
        f"Let's refine that topic a bit.\n\n"
        f"{feedback}\n\n"
        f"*Here are some suggestions:*\n"
        f"{suggestions_text}\n\n"
        "You can use one of these, modify it, or type a completely new topic:"
    )


def get_generating_message(chapter_number: int, chapter_name: str) -> str:
    return (
        f"⚙️ Generating *Chapter {chapter_number}: {chapter_name}*...\n\n"
        "This takes 30–90 seconds. I'm:\n"
        f"{'• Searching for verified academic citations' + chr(10) if chapter_number == 2 else ''}"
        f"{'• Fetching live Nigerian statistics' + chr(10) if chapter_number in [1, 2] else ''}"
        "• Writing your chapter with your project context\n"
        "• Ensuring consistency with previous chapters\n\n"
        "Please wait ⏳"
    )


def get_chapter_2_citation_update(found: int, source: str) -> str:
    source_names = {
        "openalex":        "OpenAlex",
        "crossref":        "Crossref",
        "semantic_scholar":"Semantic Scholar",
        "none":            "fallback sources",
    }
    source_label = source_names.get(source, source)
    return (
        f"📚 Found *{found} verified citations* from {source_label}.\n"
        "Writing your literature review now..."
    )


def get_error_message(context: str = "") -> str:
    context_note = f" while {context}" if context else ""
    return (
        f"Something went wrong{context_note}. "
        "Please try again in a moment. If this keeps happening, "
        "send /start to restart your session."
    )


def get_returning_user_message(first_name: str, topic: str, chapters_done: int) -> str:
    return (
        f"Welcome back, {first_name}! 👋\n\n"
        f"Your active project:\n_{topic}_\n\n"
        f"You've completed *{chapters_done}* chapter(s). "
        "Ready to continue?"
    )


print("[intake_agent.py] Intake agent prompts loaded.")