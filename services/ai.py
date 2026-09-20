import os, json
try:
    from groq import Groq
except Exception:
    Groq = None

def _client():
    key=os.getenv("GROQ_API_KEY")
    return Groq(api_key=key) if key and Groq else None

def generate_assessment(topic, chapter, total_marks=25):
    client=_client()
    if client:
        prompt=f"""Create a school assessment for chapter {chapter}, topic {topic}.
Return ONLY valid JSON with key questions. Exactly 25 marks.
Use 5 questions x 1 mark, 5 questions x 2 marks, and 2 questions x 5 marks.
Each question must have id, text, marks, options (empty list for non-MCQ), and answer_index for MCQs or answer for open questions.
Do not include explanations."""
        try:
            res=client.chat.completions.create(
                model=os.getenv("GROQ_MODEL","openai/gpt-oss-20b"),
                messages=[{"role":"user","content":prompt}],
                temperature=0.2,
                response_format={"type":"json_object"},
            )
            data=json.loads(res.choices[0].message.content)
            if isinstance(data.get("questions"), list):
                return data
        except Exception:
            pass
    questions=[]
    bank = [
        (1, "Which approach is most useful when beginning a new topic?", 1, ["Memorize everything", "Understand the key concept", "Skip examples", "Avoid practice"], 1),
        (2, "What should you do after reading an example?", 1, ["Never revisit it", "Try a similar problem", "Delete your notes", "Skip practice"], 1),
        (3, "Which habit supports long-term learning?", 1, ["Spaced revision", "Cramming only", "No practice", "Random guessing"], 0),
        (4, "What is a good first step when a problem looks difficult?", 1, ["Break it into steps", "Give up", "Guess immediately", "Skip the topic"], 0),
        (5, "What does mastery tracking help a student identify?", 1, ["Learning gaps", "Lunch time", "Classroom size", "School fees"], 0),
        (6, f"In {topic}, which action best supports accuracy?", 2, ["Follow the worked steps", "Skip all steps", "Guess every answer", "Avoid checking"], 0),
        (7, f"Which practice method is most useful for {topic}?", 2, ["Targeted questions", "No revision", "Only copying", "Skipping feedback"], 0),
        (8, f"When learning {topic}, what should you do with an error?", 2, ["Review why it happened", "Ignore it", "Hide it", "Stop learning"], 0),
        (9, f"What makes an example useful in {topic}?", 2, ["It shows a repeatable method", "It has no steps", "It avoids the concept", "It is unrelated"], 0),
        (10, f"Which activity best checks understanding of {topic}?", 2, ["Apply the idea to a new question", "Read the title only", "Skip practice", "Memorize a page"], 0),
        (11, f"Which sequence is most appropriate for mastering {topic}?", 5, ["Learn → Practice → Assess → Revise", "Assess → Skip → Forget", "Guess → Submit → Stop", "Read once → Never practice"], 0),
        (12, f"If you score below the support threshold on {topic}, what should happen next?", 5, ["Revise, get targeted practice, then reassess", "Unlock everything immediately", "Delete the result", "Skip the topic permanently"], 0),
    ]
    for i,text,marks,options,answer in bank:
        questions.append({"id":i,"text":text,"marks":marks,"options":options,"answer_index":answer})
    return {"questions":questions,"total_marks":25,"source":"RAG fallback demo"}

def generate_recommendation(name, avg, note=""):
    if avg < 40:
        focus="Revisit the core concept with worked examples, then use short guided practice before reassessment."
    elif avg < 60:
        focus="Use step-by-step practice and targeted questions to strengthen accuracy."
    else:
        focus="Mix application questions with spaced revision to consolidate mastery."
    return {"student":name,"average":avg,"key_observations":[f"Current recorded mastery is {avg}%.","Use recent teacher notes as context."],
            "recommended_plan":[focus,"Assign a small practice set.","Review the next attempt and update the support plan."],
            "practice_focus":["Worked Examples","Step-by-Step Solutions","Application Questions"],
            "note_context":note}
