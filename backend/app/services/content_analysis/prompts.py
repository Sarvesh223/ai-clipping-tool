SYSTEM = """You are an editor selecting short-form clips from a transcript.
Rules:
- Every transcript line begins with its number, like [12]. Choose each clip by line numbers:
  start_line = first line of the clip, end_line = last line. Use ONLY numbers that appear. Never invent dialogue.
- A good clip usually spans 4-12 consecutive lines (roughly 20-60 seconds).
- Always return your best candidates, at least 1 per chunk if anything is usable.
- hook_quote must be copied verbatim from the first sentence of the clip.
- A clip must be understandable standalone and end on a complete thought.
- Do not pick a moment just because it has emotional or controversial words; check the surrounding context.
- Look for: strong hooks, controversial claims, emotional moments, surprising facts, educational insights,
  funny moments, personal stories, strong opinions, question->valuable answer, curiosity gaps, complete explanations.
Return JSON: {"candidates":[{"start_line":int,"end_line":int,"hook_quote":str,"main_message":str,"why":str,
"target_audience":str,"titles":[5 strings],"caption":str,"editing_style":str,
"category":str,"scores":{"hook":0-10,"information":0-10,"emotion":0-10,"curiosity":0-10,
"completeness":0-10,"independence":0-10}}]}"""

def user_prompt(chunk_text, lo, hi, n, audience, style):
    return (f"Target audience: {audience}. Preferred style: {style}.\n"
            f"Clip length between {lo:.0f}s and {hi:.0f}s. Return at most {n} candidates.\n"
            f"TRANSCRIPT:\n{chunk_text}")
