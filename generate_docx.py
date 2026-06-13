"""
generate_docx.py
Generates the university assignment Word document (.docx) for the
Agentic SonarQube Pipeline project, following the assignment-template.docx
formatting (University of Peloponnese — MSc Computer Science).
"""

from docx import Document
from docx.shared import Pt, Cm, RGBColor, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.style import WD_STYLE_TYPE
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
import copy

OUTPUT_FILE = "Agentic_SonarQube_Pipeline_Documentation.docx"

# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def set_run_font(run, name="Times New Roman", size=12, bold=False,
                 italic=False, color=None):
    run.font.name = name
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.italic = italic
    if color:
        run.font.color.rgb = RGBColor(*color)


def add_paragraph(doc, text="", style="Normal", alignment=WD_ALIGN_PARAGRAPH.JUSTIFY,
                  space_before=0, space_after=6, font_size=12, bold=False,
                  italic=False, font_name="Times New Roman", color=None):
    p = doc.add_paragraph(style=style)
    p.alignment = alignment
    p.paragraph_format.space_before = Pt(space_before)
    p.paragraph_format.space_after = Pt(space_after)
    if text:
        run = p.add_run(text)
        set_run_font(run, name=font_name, size=font_size, bold=bold,
                     italic=italic, color=color)
    return p


def add_heading(doc, text, level=1):
    """Add a heading that matches the template's style."""
    style_map = {1: "Heading 1", 2: "Heading 2", 3: "Heading 3"}
    h = doc.add_heading(text, level=level)
    h.paragraph_format.space_before = Pt(12)
    h.paragraph_format.space_after = Pt(6)
    return h


def add_code_block(doc, code):
    """Add a code block with Courier New monospace font."""
    for line in code.split("\n"):
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(0)
        p.paragraph_format.space_after = Pt(0)
        p.paragraph_format.left_indent = Cm(1)
        run = p.add_run(line if line else " ")
        run.font.name = "Courier New"
        run.font.size = Pt(9)
        run.font.color.rgb = RGBColor(0x1a, 0x1a, 0x2e)


def add_table(doc, headers, rows, caption=""):
    """Add a styled table with header row."""
    table = doc.add_table(rows=1 + len(rows), cols=len(headers))
    table.style = "Table Grid"

    # Header row
    hdr = table.rows[0]
    for i, h in enumerate(headers):
        cell = hdr.cells[i]
        cell.text = h
        for run in cell.paragraphs[0].runs:
            run.font.bold = True
            run.font.size = Pt(10)
            run.font.name = "Times New Roman"
        # Grey background
        tc = cell._tc
        tcPr = tc.get_or_add_tcPr()
        shd = OxmlElement("w:shd")
        shd.set(qn("w:fill"), "D9D9D9")
        shd.set(qn("w:color"), "auto")
        shd.set(qn("w:val"), "clear")
        tcPr.append(shd)

    # Data rows
    for r_idx, row_data in enumerate(rows):
        row = table.rows[r_idx + 1]
        for c_idx, cell_text in enumerate(row_data):
            cell = row.cells[c_idx]
            cell.text = cell_text
            for run in cell.paragraphs[0].runs:
                run.font.size = Pt(10)
                run.font.name = "Times New Roman"

    if caption:
        cap = doc.add_paragraph()
        cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
        cap.paragraph_format.space_before = Pt(2)
        cap.paragraph_format.space_after = Pt(10)
        run = cap.add_run(caption)
        run.font.italic = True
        run.font.size = Pt(10)
        run.font.name = "Times New Roman"

    return table


def add_ascii_diagram(doc, lines):
    """Add an ASCII diagram block."""
    for line in lines.split("\n"):
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(0)
        p.paragraph_format.space_after = Pt(0)
        p.paragraph_format.left_indent = Cm(0.5)
        run = p.add_run(line if line else " ")
        run.font.name = "Courier New"
        run.font.size = Pt(8.5)
    doc.add_paragraph()


def figure_caption(doc, text):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(2)
    p.paragraph_format.space_after = Pt(12)
    run = p.add_run(text)
    run.font.italic = True
    run.font.size = Pt(10)
    run.font.name = "Times New Roman"


def body(doc, text, indent=0):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    p.paragraph_format.space_before = Pt(0)
    p.paragraph_format.space_after = Pt(6)
    if indent:
        p.paragraph_format.left_indent = Cm(indent)
    run = p.add_run(text)
    run.font.name = "Times New Roman"
    run.font.size = Pt(12)
    return p


def bold_inline(doc, label, rest, indent=0):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    p.paragraph_format.space_after = Pt(6)
    if indent:
        p.paragraph_format.left_indent = Cm(indent)
    r1 = p.add_run(label)
    r1.font.bold = True
    r1.font.name = "Times New Roman"
    r1.font.size = Pt(12)
    r2 = p.add_run(rest)
    r2.font.name = "Times New Roman"
    r2.font.size = Pt(12)
    return p


def page_break(doc):
    doc.add_page_break()


# ─────────────────────────────────────────────────────────────────────────────
# Document setup
# ─────────────────────────────────────────────────────────────────────────────

doc = Document()

# Page margins (matching template: 2.5cm all sides)
section = doc.sections[0]
section.top_margin    = Cm(2.5)
section.bottom_margin = Cm(2.5)
section.left_margin   = Cm(2.5)
section.right_margin  = Cm(2.5)

# Default paragraph font
style = doc.styles["Normal"]
style.font.name = "Times New Roman"
style.font.size = Pt(12)
style.paragraph_format.line_spacing = Pt(18)  # 1.5 line spacing

# ─────────────────────────────────────────────────────────────────────────────
# COVER PAGE
# ─────────────────────────────────────────────────────────────────────────────

def center(doc, text, size=12, bold=False, space_after=6):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_after = Pt(space_after)
    r = p.add_run(text)
    r.font.name = "Times New Roman"
    r.font.size = Pt(size)
    r.font.bold = bold
    return p

center(doc, "ΠΑΝΕΠΙΣΤΗΜΙΟ ΠΕΛΟΠΟΝΝΗΣΟΥ", 13, bold=True)
center(doc, "ΣΧΟΛΗ ΟΙΚΟΝΟΜΙΑΣ ΚΑΙ ΤΕΧΝΟΛΟΓΙΑΣ", 12, bold=True)
center(doc, "ΤΜΗΜΑ ΠΛΗΡΟΦΟΡΙΚΗΣ ΚΑΙ ΤΗΛΕΠΙΚΟΙΝΩΝΙΩΝ", 12, bold=True)
center(doc, "ΠΜΣ ΣΤΗΝ ΕΠΙΣΤΗΜΗ ΥΠΟΛΟΓΙΣΤΩΝ", 12, bold=True)
center(doc, "", space_after=24)
center(doc, "ΕΡΓΑΣΙΑ ΣΤΟ ΜΑΘΗΜΑ", 12)
center(doc, "«ΘΕΜΑΤΑ ΠΛΗΡΟΦΟΡΙΑΚΩΝ ΣΥΣΤΗΜΑΤΩΝ»", 13, bold=True)
center(doc, "", space_after=36)
center(doc, "ΤΙΤΛΟΣ ΕΡΓΑΣΙΑΣ:", 12, bold=True, space_after=6)
center(doc,
       "Agentic SonarQube Pipeline:\n"
       "Σύστημα Πολλαπλών Πρακτόρων για\n"
       "Αυτοματοποιημένη Επιδιόρθωση Ευπαθειών Κώδικα",
       14, bold=True, space_after=48)
center(doc, "", space_after=48)
center(doc, "ΟΝΟΜΑΤΕΠΩΝΥΜΟ: ________________________________________", 12)
center(doc, "Α.Μ.: ____________________", 12)
center(doc, "", space_after=48)
center(doc, "Τρίπολη | Ιούνιος 2026", 12)

page_break(doc)

# ─────────────────────────────────────────────────────────────────────────────
# ABSTRACT
# ─────────────────────────────────────────────────────────────────────────────

add_heading(doc, "Περίληψη", 1)

body(doc,
     "Η παρούσα εργασία παρουσιάζει τον σχεδιασμό και την υλοποίηση ενός συστήματος πολλαπλών "
     "πρακτόρων (multi-agent system) για την αυτοματοποιημένη ανίχνευση και επιδιόρθωση "
     "ευπαθειών κώδικα. Το σύστημα, με τίτλο Agentic SonarQube Pipeline, ενσωματώνει τεχνολογίες "
     "στατικής ανάλυσης κώδικα (SonarQube) με μεγάλα γλωσσικά μοντέλα (LLMs) σε μια πλήρως "
     "ενορχηστρωμένη αλυσίδα εργασιών (pipeline).")

body(doc,
     "Η αρχιτεκτονική βασίζεται σε πέντε εξειδικευμένους πράκτορες: τον Fixer Agent που εφαρμόζει "
     "χειρουργικές διορθώσεις μέσω tool calling, τον Tester Agent που παράγει και εκτελεί unit tests "
     "σε πραγματικό χρόνο, τον Reviewer Agent που αξιολογεί την ποιότητα του κώδικα μέσω structured "
     "outputs, τον Evaluator Agent που βαθμολογεί κάθε διόρθωση και αποφασίζει αν γίνει δεκτή "
     "(PASS/RETRY/FAIL), και τον Coordinator που ενορχηστρώνει τη συνολική ροή με μηχανισμό "
     "αυτο-βελτίωσης (AI reflection loop).")

body(doc,
     "Η μεθοδολογία ακολούθησε σταδιακή ανάπτυξη σε τέσσερις φάσεις: (1) θεμελίωση υποδομής και "
     "διασύνδεση API, (2) ενσωμάτωση LLM και τηλεμετρία, (3) πράκτορες διασφάλισης ποιότητας, "
     "και (4) ενορχήστρωση και αυτο-βελτίωση. Το σύστημα παρέχει τρεις τρόπους χρήσης: γραμμή "
     "εντολών (CLI), REST API (FastAPI), και γραφική διεπαφή (Streamlit dashboard). Η ανάπτυξη "
     "γίνεται μέσω Docker Compose, ενσωματώνοντας την εφαρμογή μαζί με τον SonarQube server "
     "σε ένα ενιαίο containerized περιβάλλον.")

p = doc.add_paragraph()
p.paragraph_format.space_after = Pt(6)
r1 = p.add_run("Λέξεις – κλειδιά: ")
r1.font.bold = True
r1.font.name = "Times New Roman"
r1.font.size = Pt(12)
r2 = p.add_run("multi-agent systems, LLM, SonarQube, automated code repair, tool calling, "
               "structured outputs, AI reflection, static code analysis, Python, FastAPI, Docker")
r2.font.italic = True
r2.font.name = "Times New Roman"
r2.font.size = Pt(12)

page_break(doc)

# ─────────────────────────────────────────────────────────────────────────────
# CHAPTER 1 — INTRODUCTION
# ─────────────────────────────────────────────────────────────────────────────

add_heading(doc, "1. Εισαγωγή", 1)
add_heading(doc, "1.1 Γενική Τοποθέτηση", 2)

body(doc,
     "Η ποιότητα λογισμικού αποτελεί κρίσιμη παράμετρο σε κάθε κύκλο ανάπτυξης. Εργαλεία "
     "στατικής ανάλυσης κώδικα, όπως το SonarQube (SonarSource, 2024), εντοπίζουν αυτοματοποιημένα "
     "bugs, ευπάθειες ασφαλείας (vulnerabilities) και κακοσχεδιασμένο κώδικα (code smells) ακόμα "
     "και πριν αυτός εκτελεστεί. Ωστόσο, η διαδικασία επιδιόρθωσης αυτών των ζητημάτων παραμένει "
     "σε μεγάλο βαθμό χειροκίνητη, απαιτώντας χρόνο και εξειδίκευση από τους προγραμματιστές.")

body(doc,
     "Παράλληλα, η ραγδαία εξέλιξη των Μεγάλων Γλωσσικών Μοντέλων (Large Language Models — LLMs) "
     "έχει δημιουργήσει νέες δυνατότητες στον αυτοματισμό εργασιών κωδικοποίησης (Chen et al., 2021). "
     "Μοντέλα όπως τα GPT-4o (OpenAI, 2024), Claude (Anthropic, 2024) και LLaMA (Touvron et al., 2023) "
     "μπορούν να κατανοήσουν κώδικα, να προτείνουν διορθώσεις και ακόμη να παράγουν δοκιμές "
     "μονάδας (unit tests).")

add_heading(doc, "1.2 Κίνητρα", 2)

body(doc,
     "Η κεντρική ιδέα αυτής της εργασίας είναι η γεφύρωση του χάσματος μεταξύ ανίχνευσης και "
     "επιδιόρθωσης: ένα σύστημα που όχι μόνο εντοπίζει ευπάθειες κώδικα, αλλά τις διορθώνει "
     "αυτόνομα, ελέγχει τις διορθώσεις με αυτοματοποιημένα τεστ, αξιολογεί την ποιότητά τους, "
     "και αν κρίνει ότι δεν πληρούν τα πρότυπα, ξαναπροσπαθεί — μιμούμενο τη ροή εργασίας "
     "ενός πεπειραμένου μηχανικού λογισμικού.")

add_heading(doc, "1.3 Μεθοδολογία και Αρχιτεκτονική", 2)

body(doc,
     "Η ανάπτυξη ακολούθησε αρχιτεκτονική πολλαπλών πρακτόρων (multi-agent architecture), "
     "στην οποία κάθε πράκτορας (agent) εξειδικεύεται σε μία λειτουργία. Παρακάτω παρουσιάζεται "
     "η αρχιτεκτονική του συστήματος:")

add_ascii_diagram(doc, """
                         ┌──────────────┐
                         │  SonarQube   │
                         │     API      │
                         └──────┬───────┘
                                │ issues + source code
                         ┌──────▼───────┐
                         │  User Issue  │
                         │  Selection   │
                         └──────┬───────┘
                                │
                    ┌───────────▼───────────┐
                    │      Coordinator      │
                    │   (retry loop, 2x)    │
                    └───────────┬───────────┘
                                │
              ┌─────────────────┼─────────────────┐
              ▼                 ▼                  ▼
     ┌────────────┐   ┌────────────────┐   ┌──────────────┐
     │   Fixer    │   │    Tester      │   │   Reviewer   │
     │   Agent    │──▶│    Agent       │   │   Agent      │
     │(tool call) │   │ (pytest exec)  │   │(Pydantic out)│
     └────────────┘   └────────┬───────┘   └──────┬───────┘
                               │                   │
                        ┌──────▼───────────────────▼──┐
                        │       Evaluator Agent        │
                        │  PASS → commit + resolve     │
                        │  RETRY → restore + feedback  │
                        │  FAIL → abort                │
                        └──────────────────────────────┘
""")

figure_caption(doc, "Εικόνα 1 — Αρχιτεκτονική Συστήματος Πολλαπλών Πρακτόρων")

add_table(doc,
    headers=["Πράκτορας", "Ρόλος", "Έξοδος"],
    rows=[
        ["Fixer Agent", "Χειρουργική επιδιόρθωση κώδικα μέσω tool calling", "Τροποποιημένο αρχείο στο disk"],
        ["Tester Agent", "Δυναμική παραγωγή και εκτέλεση unit tests (pytest)", "Pass/Fail + stdout output"],
        ["Reviewer Agent", "Αξιολόγηση ποιότητας: PEP-8, αναγνωσιμότητα", "Δομημένο ReviewResult (Pydantic)"],
        ["Evaluator Agent", "Τελική βαθμολόγηση — PASS / RETRY / FAIL", "Δομημένο EvalResult (Pydantic)"],
        ["Coordinator", "Ενορχήστρωση pipeline, retry logic, reflection", "report.json + DB records"],
    ],
    caption="Πίνακας 1 — Ρόλοι Πρακτόρων (Agents)")

add_heading(doc, "1.4 Δομή Εργασίας", 2)

body(doc, "Η υπόλοιπη εργασία οργανώνεται ως εξής:")
items = [
    ("Κεφάλαιο 2", " — Θεμελίωση υποδομής: SonarQube client, βάση δεδομένων, μοντέλα"),
    ("Κεφάλαιο 3", " — Ενσωμάτωση LLM: βασική κλάση Agent, Fixer Agent, τηλεμετρία"),
    ("Κεφάλαιο 4", " — Πράκτορες QA: Tester, Reviewer, Evaluator"),
    ("Κεφάλαιο 5", " — Ενορχήστρωση: Coordinator, retry loop, verification"),
    ("Κεφάλαιο 6", " — REST API (FastAPI) και Streamlit UI"),
    ("Κεφάλαιο 7", " — Ανάπτυξη με Docker"),
    ("Κεφάλαιο 8", " — Δοκιμές (Testing)"),
    ("Κεφάλαιο 9", " — Συμπεράσματα"),
]
for label, rest in items:
    bold_inline(doc, label, rest, indent=1)

page_break(doc)

# ─────────────────────────────────────────────────────────────────────────────
# CHAPTER 2 — INFRASTRUCTURE
# ─────────────────────────────────────────────────────────────────────────────

add_heading(doc, "2. Θεμελίωση Υποδομής, Διασύνδεση API και Διαχείριση Δεδομένων", 1)

body(doc,
     "Ο πρωταρχικός στόχος αυτής της ενότητας είναι η δημιουργία της βασικής αρχιτεκτονικής "
     "υποδομής, η οποία εξασφαλίζει την επικοινωνία με τον SonarQube server, τη μόνιμη "
     "αποθήκευση δεδομένων και τη διαχείριση του κύκλου ζωής των ζητημάτων (OPEN → FIXED | FAILED).")

add_heading(doc, "2.1 SonarQube Client — sonarcube_client.py", 2)

body(doc,
     "Η κλάση SonarCubeClient αποτελεί τον πυρήνα επικοινωνίας με τον SonarQube server. "
     "Αρχικοποιείται με ένα URL και ένα authentication token.")

add_heading(doc, "2.1.1 Ανάκτηση Ζητημάτων (Issues Fetching)", 3)

body(doc,
     "Η μέθοδος get_issues() υλοποιεί paginated fetching, ανακτώντας ζητήματα ανά σελίδα "
     "(500 ανά σελίδα) μέσω του endpoint /api/issues/search. Η σελιδοποίηση (pagination) "
     "είναι απαραίτητη καθώς τα projects μπορεί να περιέχουν χιλιάδες ζητήματα. "
     "Ανακτώνται μόνο ζητήματα με κατάσταση OPEN, CONFIRMED ή REOPENED.")

add_heading(doc, "2.1.2 Ανάκτηση Πηγαίου Κώδικα", 3)

body(doc,
     "Η μέθοδος fetch_source_code() χρησιμοποιεί το endpoint /api/sources/raw για να "
     "ανακτήσει τον πηγαίο κώδικα ενός αρχείου απευθείας από τον SonarQube server. "
     "Αυτό επιτρέπει τον Fixer Agent να δει ακριβώς τον κώδικα που αναλύθηκε.")

add_heading(doc, "2.1.3 Σήμανση Επιδιόρθωσης και Επαλήθευση", 3)

body(doc,
     "Η μέθοδος mark_issue_fixed() εκτελεί δύο ενέργειες: (1) Προσθήκη σχολίου στο issue "
     "με τη βαθμολογία του Evaluator και το reasoning, (2) Μετάβαση κατάστασης (transition) "
     "σε 'resolved' μέσω του /api/issues/do_transition.")

body(doc,
     "Για την επαλήθευση, υλοποιήθηκαν: run_scan() (εκτελεί sonar-scanner CLI), "
     "_wait_for_ce_task() (polling στο Compute Engine API μέχρι ολοκλήρωση ή timeout), "
     "και run_scan_and_wait() που τα συνδυάζει σε μια σύγχρονη λειτουργία.")

add_heading(doc, "2.2 Σχεσιακή Βάση Δεδομένων — database.py", 2)

body(doc,
     "Η αποθήκευση δεδομένων γίνεται μέσω SQLite (αρχείο pipeline.db) με τη βιβλιοθήκη "
     "SQLAlchemy ORM. Η βάση δεδομένων περιέχει τρεις πίνακες:")

add_heading(doc, "2.2.1 Πίνακας issues", 3)
add_table(doc,
    headers=["Πεδίο", "Τύπος", "Περιγραφή"],
    rows=[
        ["id", "Integer (PK)", "Αυτόματος αύξων αριθμός"],
        ["key", "String (Unique)", "Μοναδικό κλειδί SonarQube issue"],
        ["rule", "String", "Κανόνας SonarQube (π.χ. python:S1234)"],
        ["severity", "String", "BLOCKER, CRITICAL, MAJOR, MINOR, INFO"],
        ["component", "String", "Πλήρες path αρχείου με project prefix"],
        ["file_path", "String", "Σχετικό path αρχείου"],
        ["line", "Integer", "Αριθμός γραμμής"],
        ["message", "Text", "Περιγραφή ζητήματος"],
        ["type", "String", "BUG, VULNERABILITY, CODE_SMELL"],
        ["status", "String", "Κύκλος ζωής: OPEN → FIXED | FAILED"],
        ["project_key", "String", "Κλειδί project SonarQube"],
        ["first_seen_at", "DateTime", "Πρώτη εμφάνιση"],
        ["last_updated_at", "DateTime", "Τελευταία ενημέρωση"],
    ],
    caption="Πίνακας 2 — Σχήμα Βάσης Δεδομένων: Πίνακας issues")

add_heading(doc, "2.2.2 Πίνακας pipeline_runs", 3)
add_table(doc,
    headers=["Πεδίο", "Τύπος", "Περιγραφή"],
    rows=[
        ["id", "Integer (PK)", "Αυτόματος αύξων αριθμός"],
        ["issue_key", "String (FK)", "Σύνδεση με issues.key"],
        ["session_branch", "String", "Όνομα Git branch"],
        ["verdict", "String", "IN_PROGRESS → SUCCESS | FAIL"],
        ["attempts", "Integer", "Αριθμός προσπαθειών"],
        ["verified", "Integer (nullable)", "None=μη ελεγμένο, 1=επιβεβαιωμένο, 0=ακόμα ανοιχτό"],
        ["started_at", "DateTime", "Έναρξη εκτέλεσης"],
        ["completed_at", "DateTime", "Ολοκλήρωση εκτέλεσης"],
    ],
    caption="Πίνακας 3 — Σχήμα Βάσης Δεδομένων: Πίνακας pipeline_runs")

add_heading(doc, "2.2.3 Πίνακας token_usage", 3)
add_table(doc,
    headers=["Πεδίο", "Τύπος", "Περιγραφή"],
    rows=[
        ["id", "Integer (PK)", "Αυτόματος αύξων αριθμός"],
        ["run_id", "Integer (FK)", "Σύνδεση με pipeline_runs.id"],
        ["agent_name", "String", "Όνομα πράκτορα"],
        ["model_name", "String", "Μοντέλο LLM (π.χ. gpt-4o)"],
        ["prompt_tokens", "Integer", "Tokens εισόδου"],
        ["completion_tokens", "Integer", "Tokens εξόδου"],
        ["total_tokens", "Integer", "Σύνολο tokens"],
        ["estimated_cost_usd", "Float", "Εκτιμώμενο κόστος σε USD"],
        ["called_at", "DateTime", "Χρονοσήμανση κλήσης"],
    ],
    caption="Πίνακας 4 — Σχήμα Βάσης Δεδομένων: Πίνακας token_usage")

add_heading(doc, "2.2.4 Σχεσιακό Διάγραμμα (ER Diagram)", 3)

add_ascii_diagram(doc, """
┌──────────────┐       ┌──────────────────┐       ┌──────────────────┐
│    issues    │ 1───* │  pipeline_runs   │ 1───* │   token_usage    │
├──────────────┤       ├──────────────────┤       ├──────────────────┤
│ PK id        │       │ PK id            │       │ PK id            │
│ UK key  ◄────────FK──│ FK issue_key     │       │ FK run_id  ►─────┤
│ rule         │       │ session_branch   │       │ agent_name       │
│ severity     │       │ verdict          │       │ model_name       │
│ component    │       │ attempts         │       │ prompt_tokens    │
│ file_path    │       │ verified         │       │ completion_tokens│
│ line/message │       │ started_at       │       │ estimated_cost   │
│ type/status  │       │ completed_at     │       │ called_at        │
└──────────────┘       └──────────────────┘       └──────────────────┘
""")
figure_caption(doc, "Εικόνα 3 — Σχεσιακό Μοντέλο Βάσης Δεδομένων (ER Diagram)")

add_heading(doc, "2.3 Μοντέλα Δεδομένων — models.py", 2)

body(doc,
     "Τα μοντέλα δεδομένων χωρίζονται σε δύο κατηγορίες. Τα Dataclasses (Issue, FixResult, "
     "TestResult, PipelineResult) χρησιμοποιούνται για εσωτερική αναπαράσταση. Τα Pydantic "
     "BaseModels (ReviewResult, EvalResult) χρησιμοποιούνται για structured outputs από το LLM.")

body(doc,
     "Ιδιαίτερο ενδιαφέρον παρουσιάζει ο υπολογισμός overall_score στο EvalResult ως computed "
     "field Pydantic: μέσος όρος των τριών επιμέρους βαθμολογιών (correctness, safety, readability).")

page_break(doc)

# ─────────────────────────────────────────────────────────────────────────────
# CHAPTER 3 — LLM & FIXER AGENT
# ─────────────────────────────────────────────────────────────────────────────

add_heading(doc, "3. Ενσωμάτωση LLM, Πράκτορας Επιδιόρθωσης (Fixer Agent) και Τηλεμετρία", 1)

body(doc,
     "Ο στόχος αυτής της ενότητας είναι η αξιοποίηση LLMs για τη δημιουργία ενός αυτόνομου "
     "μηχανισμού επιδιόρθωσης κώδικα, με ταυτόχρονη παρακολούθηση του κόστους χρήσης.")

add_heading(doc, "3.1 Βασική Κλάση Agent — agents/agent.py", 2)

body(doc,
     "Η κλάση Agent αποτελεί αφηρημένη βασική κλάση για όλους τους πράκτορες. "
     "Κάθε agent αρχικοποιείται με model_name, url και token, δημιουργώντας εσωτερικά "
     "έναν OpenAI client. Η χρήση custom base_url επιτρέπει σύνδεση με οποιοδήποτε "
     "OpenAI-compatible API (OpenAI, Ollama, OpenRouter, LM Studio κ.λπ.).")

add_heading(doc, "3.1.1 Tracked Calls — Αυτόματη Τηλεμετρία", 3)

body(doc,
     "Κάθε κλήση LLM γίνεται μέσω δύο wrappers: _tracked_call() για κανονικές chat "
     "completions και _tracked_parse() για structured output (Pydantic) completions. "
     "Και οι δύο αυτόματα εξάγουν τα prompt_tokens και completion_tokens από το response "
     "και τα καταγράφουν στη βάση δεδομένων μέσω log_token_usage().")

add_heading(doc, "3.1.2 Generic Tool Handling", 3)

body(doc,
     "Η μέθοδος handle_tool_call() παρέχει γενικό μηχανισμό εκτέλεσης εργαλείων (tools). "
     "Κάθε υποκλάση ορίζει ένα tool_mapping dictionary που αντιστοιχίζει ονόματα εργαλείων "
     "σε μεθόδους Python. Ο agent εκτελεί αυτόματα κάθε tool call που επιστρέφει το LLM.")

add_heading(doc, "3.2 Fixer Agent — agents/fixer.py", 2)

body(doc,
     "Ο Fixer Agent εφαρμόζει χειρουργικές (surgical) διορθώσεις στον κώδικα. "
     "Λαμβάνει αυστηρές οδηγίες: FOCUS (μόνο το συγκεκριμένο ζήτημα), PRECISION "
     "(προσοχή στον αριθμό γραμμής), και SURGICAL EDITS (υποχρεωτική χρήση του "
     "εργαλείου apply_surgical_fix).")

add_heading(doc, "3.2.1 Tool: apply_surgical_fix", 3)

body(doc,
     "Η κεντρική λειτουργία του Fixer ορίζεται ως OpenAI function tool με παραμέτρους: "
     "file_path (σχετικό path αρχείου), old_code (ακριβές block κώδικα προς αντικατάσταση), "
     "new_code (νέος κώδικας), και explanation (αιτιολόγηση διόρθωσης).")

body(doc,
     "Η υλοποίηση apply_surgical_fix() εφαρμόζει αντικατάσταση κειμένου (string replacement) "
     "στο αρχείο. Περιλαμβάνει τρεις μηχανισμούς fallback: (1) Ακριβής αντιστοίχιση, "
     "(2) Newline-stripped αντιστοίχιση, (3) Fully-stripped αντιστοίχιση (μόνο αν unique).")

add_heading(doc, "3.2.2 Υποστήριξη Jupyter Notebooks", 3)

body(doc,
     "Ο Fixer μπορεί να τροποποιεί και αρχεία .ipynb μέσω της μεθόδου apply_ipynb_fix(). "
     "Αναλύει τη δομή JSON του notebook, αναζητά τον κώδικα στα code cells, εφαρμόζει "
     "την αντικατάσταση και αποθηκεύει ξανά τη δομή JSON.")

add_heading(doc, "3.2.3 Agentic Loop", 3)

body(doc,
     "Η μέθοδος fix_code_file() υλοποιεί τον agentic loop: κατασκευάζει το user prompt "
     "με τα στοιχεία του issue και τον πηγαίο κώδικα, αν υπάρχει feedback (reflection messages) "
     "το ενσωματώνει, και επαναλαμβάνει κλήσεις LLM (μέγ. 5) μέχρι να εφαρμοστεί η διόρθωση.")

add_heading(doc, "3.3 Τηλεμετρία Tokens και Κόστος", 2)

body(doc,
     "Το σύστημα διατηρεί εσωτερικό πίνακα τιμών για τον υπολογισμό κόστους. "
     "Η αντιστοίχιση γίνεται μέσω substring matching στο όνομα μοντέλου, "
     "επιτρέποντας ευελιξία στη ρύθμιση.")

add_table(doc,
    headers=["Μοντέλο", "Input ($/1K tokens)", "Output ($/1K tokens)"],
    rows=[
        ["gpt-5-nano", "$0.000150", "$0.000600"],
        ["gpt-4o-mini", "$0.000150", "$0.000600"],
        ["gpt-4o", "$0.002500", "$0.010000"],
        ["gpt-4-turbo", "$0.010000", "$0.030000"],
        ["gpt-4", "$0.030000", "$0.060000"],
        ["claude-3-5-sonnet", "$0.003000", "$0.015000"],
        ["claude-3-opus", "$0.015000", "$0.075000"],
        ["llama / mistral (local)", "$0.000000", "$0.000000"],
    ],
    caption="Πίνακας 5 — Τιμολόγηση Μοντέλων LLM")

page_break(doc)

# ─────────────────────────────────────────────────────────────────────────────
# CHAPTER 4 — QA AGENTS
# ─────────────────────────────────────────────────────────────────────────────

add_heading(doc, "4. Αυτοματοποιημένη Επικύρωση και Διασφάλιση Ποιότητας (QA Agents)", 1)

body(doc,
     "Ο στόχος αυτής της ενότητας είναι η ανάπτυξη ανεξάρτητου συστήματος QA που "
     "επαληθεύει τις AI-παραγόμενες διορθώσεις πριν αυτές γίνουν δεκτές.")

add_heading(doc, "4.1 Tester Agent — agents/tester.py", 2)

body(doc,
     "Ο Tester Agent αναλαμβάνει τη δυναμική παραγωγή και εκτέλεση unit tests σε πραγματικό "
     "χρόνο. Λειτουργεί σε τρία βήματα μέσω αντίστοιχων εργαλείων (tools).")

add_heading(doc, "4.1.1 Τρία Εργαλεία (Tools)", 3)

bold_inline(doc, "Βήμα 1 — check_testability: ",
            "Ελέγχει αν το ζήτημα μπορεί να επαληθευτεί με unit test. "
            "Ζητήματα καθαρά αισθητικής φύσης (π.χ. TODO comments, naming conventions) "
            "χαρακτηρίζονται ως not testable.", indent=1)

bold_inline(doc, "Βήμα 2 — execute_test: ",
            "Αν είναι testable, γράφει pytest κώδικα σε προσωρινό αρχείο, "
            "τον εκτελεί με subprocess.run() με timeout 60 δευτερολέπτων, "
            "και διαγράφει το αρχείο αυτόματα (finally block).", indent=1)

bold_inline(doc, "Βήμα 3 — submit_test_result: ",
            "Υποβάλλει δομημένο αποτέλεσμα με test_passed (boolean) και summary.", indent=1)

add_heading(doc, "4.1.2 Οδηγίες για Ποιοτικά Tests", 3)

body(doc,
     "Το system prompt του Tester περιλαμβάνει εξειδικευμένες οδηγίες: σωστή χρήση import "
     "paths βάσει file path, υποχρεωτική χρήση unittest.mock για εξωτερικές εξαρτήσεις, "
     "και γνώση Python name mangling (_ClassName__private) για private attributes.")

add_heading(doc, "4.2 Reviewer Agent — agents/reviewer.py", 2)

body(doc,
     "Ο Reviewer Agent αξιολογεί την ποιότητα του κώδικα μετά τη διόρθωση. Χρησιμοποιεί "
     "τη λειτουργία Pydantic structured output του OpenAI API "
     "(client.beta.chat.completions.parse()), εξασφαλίζοντας πάντα valid ReviewResult.")

body(doc, "Κριτήρια αξιολόγησης:")
bold_inline(doc, "readability_score (1-10): ", "Αναγνωσιμότητα του αλλαγμένου κώδικα.", indent=1)
bold_inline(doc, "maintainability_score (1-10): ", "Συντηρησιμότητα, PEP-8 compliance.", indent=1)
bold_inline(doc, "suggestions: ", "Λίστα προτάσεων βελτίωσης (κενή αν ο κώδικας είναι άριστος).", indent=1)
bold_inline(doc, "is_acceptable: ", "Boolean — αν η διόρθωση πληροί επαγγελματικά πρότυπα.", indent=1)

body(doc,
     "Κρίσιμος κανόνας: ο Reviewer αξιολογεί ΜΟΝΟ τις αλλαγές που έγιναν, "
     "όχι προϋπάρχοντα ζητήματα στο αρχείο.")

add_heading(doc, "4.3 Evaluator Agent — agents/evaluator.py", 2)

body(doc,
     "Ο Evaluator Agent αποτελεί τον τελικό κριτή — αποφασίζει αν μια διόρθωση "
     "γίνεται δεκτή. Συνδυάζει τέσσερα inputs: αρχικό κώδικα, διορθωμένο κώδικα, "
     "αποτελέσματα tests, και feedback Reviewer.")

body(doc, "Τρεις διαστάσεις βαθμολόγησης:")
bold_inline(doc, "correctness_score (1-10): ", "Επιλύει πραγματικά το SonarQube issue;", indent=1)
bold_inline(doc, "safety_score (1-10): ", "Εισάγει νέες ευπάθειες ή παρενέργειες;", indent=1)
bold_inline(doc, "readability_score (1-10): ", "Είναι καθαρός και PEP-8 compliant;", indent=1)

body(doc, "Τελική απόφαση βάσει μέσου όρου:")
bold_inline(doc, "PASS (μέσος ≥ 7): ",
            "Η διόρθωση γίνεται δεκτή → commit + resolve στο SonarQube.", indent=1)
bold_inline(doc, "RETRY (μέσος 4–6): ",
            "Η διόρθωση χρειάζεται βελτίωση → νέα προσπάθεια με feedback.", indent=1)
bold_inline(doc, "FAIL (μέσος < 4): ",
            "Η διόρθωση είναι εσφαλμένη → πλήρης εγκατάλειψη.", indent=1)

page_break(doc)

# ─────────────────────────────────────────────────────────────────────────────
# CHAPTER 5 — COORDINATOR & ORCHESTRATION
# ─────────────────────────────────────────────────────────────────────────────

add_heading(doc, "5. Ενορχήστρωση, Αυτο-βελτίωση (AI Reflection) και Επαλήθευση", 1)

add_heading(doc, "5.1 Coordinator — agents/coordinator.py", 2)

body(doc,
     "Ο Coordinator δεν κληρονομεί από την κλάση Agent — δεν κάνει κλήσεις LLM ο ίδιος. "
     "Αντ' αυτού, δημιουργεί εσωτερικά τους τέσσερις agents (Fixer, Tester, Reviewer, Evaluator) "
     "και ελέγχει τη συνολική ροή.")

add_heading(doc, "5.2 Retry Loop και Reflection", 2)

body(doc,
     "Η μέθοδος process_issue() υλοποιεί τον κύκλο retry με μέγιστο 2 επαναλήψεις "
     "(3 συνολικά προσπάθειες). Η ροή εκτέλεσης για κάθε προσπάθεια:")

add_ascii_diagram(doc, """
  Για attempt = 1 → max_retries+1 (3 φορές):
  ├── 1. Fetch source code από SonarQube
  ├── 2. Fixer Agent → apply_surgical_fix (tool calling)
  ├── 3. Αν fix failed → continue
  ├── 4. Read fixed code from file
  ├── 5. Tester Agent → δημιουργία & εκτέλεση tests
  ├── 6. Reviewer Agent → αξιολόγηση ποιότητας
  ├── 7. Evaluator Agent → τελική απόφαση
  │
  ├── PASS  → git commit, mark resolved, return SUCCESS
  ├── RETRY → git restore, add reflection msg, continue
  └── FAIL  → git restore, return FAIL
""")
figure_caption(doc, "Εικόνα 5 — Retry Loop και Reflection Mechanism")

add_heading(doc, "5.2.1 Reflection Messages", 3)

body(doc,
     "Το κρίσιμο στοιχείο αυτο-βελτίωσης: όταν ο Evaluator αποφασίζει RETRY, "
     "το reasoning του περνάει στον Fixer Agent ως feedback στην επόμενη προσπάθεια. "
     "Ο Fixer λαμβάνει αυτά τα μηνύματα στο prompt, επιτρέποντας στο LLM να μάθει "
     "από τα λάθη του χωρίς επαναεκπαίδευση — μηχανισμός γνωστός ως AI Reflection.")

add_heading(doc, "5.2.2 Ενιαίο Σημείο Εγγραφής στη Βάση", 3)

body(doc,
     "Η εγγραφή στη βάση δεδομένων γίνεται σε ένα μοναδικό σημείο μετά τη λήξη "
     "του loop, αποφεύγοντας inconsistent states: αν SUCCESS → FIXED, αν FAIL → FAILED.")

add_heading(doc, "5.3 Επαλήθευση μετά τη Διόρθωση (Verification)", 2)

body(doc,
     "Η μέθοδος verify_fixes() εκτελεί re-scan στο SonarQube μετά τις διορθώσεις "
     "για να επιβεβαιωθεί ότι τα issues όντως εξαφανίστηκαν. Η διαδικασία: "
     "(1) Εκτέλεση scan + αναμονή CE task, (2) Ανάκτηση issues μετά το scan, "
     "(3) Σύγκριση με τα fixed issue keys, (4) Ενημέρωση DB με verified/unverified, "
     "(5) Αποτέλεσμα: SUCCESS (όλα gone), PARTIAL (κάποια gone), FAILED (κανένα).")

page_break(doc)

# ─────────────────────────────────────────────────────────────────────────────
# CHAPTER 6 — REST API & UI
# ─────────────────────────────────────────────────────────────────────────────

add_heading(doc, "6. REST API και Διαδικτυακή Διεπαφή", 1)

add_heading(doc, "6.1 FastAPI Backend — api.py", 2)

body(doc,
     "Η εφαρμογή εκθέτει RESTful API endpoints μέσω FastAPI. "
     "Το pipeline εκτελείται ασύγχρονα σε background thread μέσω "
     "ThreadPoolExecutor(max_workers=2), επιτρέποντας πολλαπλές ταυτόχρονες εκτελέσεις.")

add_table(doc,
    headers=["Μέθοδος", "Endpoint", "Περιγραφή"],
    rows=[
        ["GET", "/issues/{project_key}", "Ανάκτηση open issues από SonarQube"],
        ["POST", "/scan", "Clone repo + εκτέλεση SonarQube scan"],
        ["POST", "/pipeline/run", "Εκκίνηση ασύγχρονου pipeline run"],
        ["GET", "/pipeline/status/{session_id}", "Παρακολούθηση προόδου pipeline"],
        ["POST", "/pipeline/verify", "Επαλήθευση διορθώσεων μέσω re-scan"],
        ["GET", "/runs", "Λίστα πρόσφατων pipeline runs"],
        ["GET", "/analytics", "Στατιστικά (tokens, κόστος, success rate)"],
    ],
    caption="Πίνακας 6 — REST API Endpoints")

body(doc,
     "Πριν ξεκινήσει ένα νέο pipeline, ελέγχεται αν κάποια issues βρίσκονται ήδη σε "
     "εξέλιξη (HTTP 409 Conflict). Μετά την ολοκλήρωση, αν υπάρχουν επιτυχείς διορθώσεις, "
     "εκτελείται αυτόματα verification scan.")

add_heading(doc, "6.2 Streamlit Dashboard — ui.py", 2)

body(doc,
     "Η γραφική διεπαφή υλοποιείται με Streamlit με custom CSS (Inter font, gradient headers, "
     "dark mode sidebar, glassmorphism metric cards, status badges) και παρέχει 4 σελίδες:")

add_heading(doc, "6.2.1 Σελίδα Dashboard", 3)

body(doc,
     "Κεντρική σελίδα με metric cards (Total Issues, Fixed, Failed, Success Rate), "
     "verification metrics, cost summary, cost by agent με progress bars, "
     "και λίστα πρόσφατων pipeline runs με color-coded badges.")

add_heading(doc, "6.2.2 Σελίδα Run Pipeline", 3)

body(doc,
     "Διαδραστική σελίδα 4 βημάτων: (1) Configure — εισαγωγή repo URL/path + project key, "
     "(2) Preview Issues — fetch issues με multiselect επιλογή, "
     "(3) Launch — εκκίνηση pipeline, "
     "(4) Live Progress — real-time progress bar με auto-refresh κάθε 5 δευτερόλεπτα.")

add_heading(doc, "6.2.3 Σελίδα Issues", 3)

body(doc,
     "Browser για SonarQube issues με color-coded severity "
     "(BLOCKER=κόκκινο, CRITICAL=πορτοκαλί, MAJOR=κίτρινο, MINOR=μπλε) "
     "και expandable details (component, message, tags).")

add_heading(doc, "6.2.4 Σελίδα Analytics", 3)

body(doc,
     "Σελίδα αναλυτικών στατιστικών: top metrics, verification stats, pipeline stats, "
     "cost breakdown ανά agent, και πλήρης πίνακας runs ως Pandas DataFrame.")

page_break(doc)

# ─────────────────────────────────────────────────────────────────────────────
# CHAPTER 7 — DOCKER
# ─────────────────────────────────────────────────────────────────────────────

add_heading(doc, "7. Ανάπτυξη με Docker", 1)

add_heading(doc, "7.1 Docker Compose Τοπολογία", 2)

body(doc,
     "Το σύστημα αναπτύσσεται με δύο Docker services που επικοινωνούν μέσω "
     "εσωτερικού Docker network:")

add_ascii_diagram(doc, """
┌────────────────────────────────────────────────────┐
│              Docker Compose Network                 │
│                                                     │
│  ┌─────────────────┐    ┌─────────────────┐        │
│  │      app        │    │   sonarqube     │        │
│  │                 │    │                 │        │
│  │ FastAPI  (:8000)│───►│ SonarQube CE    │        │
│  │ Streamlit(:8501)│    │     (:9000)     │        │
│  │ sonar-scanner   │    │                 │        │
│  └─────────────────┘    └─────────────────┘        │
│                                                     │
│  Volumes:  app_repos | app_db | sonarqube_data      │
└────────────────────────────────────────────────────┘
""")
figure_caption(doc, "Εικόνα 6 — Docker Compose Τοπολογία")

add_heading(doc, "7.2 Dockerfile", 2)

body(doc, "Βασικά χαρακτηριστικά:")
for item in [
    "Base image: python:3.12-slim",
    "Εγκατάσταση: git, default-jre-headless (για sonar-scanner), curl, unzip",
    "Download και εγκατάσταση sonar-scanner-cli v6.2.1 από binaries.sonarsource.com",
    "Git identity configuration για αυτοματοποιημένα commits (bot@agentic-pipeline.local)",
    "Lean dependencies (requirements.docker.txt) — χωρίς torch/transformers",
    "Expose ports 8000 (FastAPI) και 8501 (Streamlit)",
    "Εκκίνηση μέσω start.sh: FastAPI background + Streamlit foreground",
]:
    p = doc.add_paragraph(style="List Bullet")
    run = p.add_run(item)
    run.font.name = "Times New Roman"
    run.font.size = Pt(12)

add_heading(doc, "7.3 Εκκίνηση", 2)

body(doc, "Η πλήρης στοίβα εκκινεί με μία εντολή:")

add_code_block(doc, "docker-compose up --build")

body(doc, "Εκκινεί:")
for item in [
    "Streamlit UI → http://localhost:8501",
    "FastAPI API  → http://localhost:8000",
    "SonarQube   → http://localhost:9000",
]:
    p = doc.add_paragraph(style="List Bullet")
    run = p.add_run(item)
    run.font.name = "Times New Roman"
    run.font.size = Pt(12)

page_break(doc)

# ─────────────────────────────────────────────────────────────────────────────
# CHAPTER 8 — TESTING
# ─────────────────────────────────────────────────────────────────────────────

add_heading(doc, "8. Δοκιμές (Testing)", 1)

body(doc,
     "Οι δοκιμές βρίσκονται στο αρχείο tests/test_verification.py και καλύπτουν "
     "τέσσερις κατηγορίες με συνολικά 14 test cases.")

add_heading(doc, "8.1 SonarCubeClient Tests", 2)
for t in [
    "test_wait_for_ce_task_completes_immediately — CE χωρίς pending tasks",
    "test_wait_for_ce_task_polls_then_completes — CE ολοκληρώνεται μετά polling",
    "test_wait_for_ce_task_timeout — CE δεν ολοκληρώνεται εντός timeout",
    "test_run_scan_and_wait_success — Scan + wait επιτυχία",
]:
    p = doc.add_paragraph(style="List Bullet")
    run = p.add_run(t)
    run.font.name = "Times New Roman"
    run.font.size = Pt(12)

add_heading(doc, "8.2 Database Tests (in-memory SQLite)", 2)
for t in [
    "test_mark_run_verified_true/false — Σωστή ενημέρωση verified flag",
    "test_mark_run_verified_nonexistent — Graceful handling μη υπάρχοντος run",
    "test_get_latest_successful_runs — Ανάκτηση τελευταίου successful run",
    "test_analytics_includes_verification_stats — Verification stats στα analytics",
]:
    p = doc.add_paragraph(style="List Bullet")
    run = p.add_run(t)
    run.font.name = "Times New Roman"
    run.font.size = Pt(12)

add_heading(doc, "8.3 Coordinator Tests (mocked agents)", 2)
for t in [
    "test_verify_no_issues — Κενή λίστα → SUCCESS χωρίς scan",
    "test_verify_all_fixed — Όλα εξαφανίστηκαν → SUCCESS",
    "test_verify_partial — Μερικά εξαφανίστηκαν → PARTIAL",
    "test_verify_none_fixed — Κανένα δεν εξαφανίστηκε → FAILED",
    "test_verify_scan_failure — Scan αποτυχία → FAILED",
    "test_verify_detects_new_issues — Ανίχνευση νέων issues",
]:
    p = doc.add_paragraph(style="List Bullet")
    run = p.add_run(t)
    run.font.name = "Times New Roman"
    run.font.size = Pt(12)

add_heading(doc, "8.4 FastAPI Endpoint Tests", 2)
for t in [
    "test_verify_missing_both_repo_fields — HTTP 400 χωρίς repo",
    "test_verify_nonexistent_repo_path — HTTP 400 για ανύπαρκτο path",
    "test_verify_success — HTTP 200 με σωστά αποτελέσματα",
]:
    p = doc.add_paragraph(style="List Bullet")
    run = p.add_run(t)
    run.font.name = "Times New Roman"
    run.font.size = Pt(12)

body(doc, "\nΕκτέλεση των tests:")
add_code_block(doc, "pytest tests/ -v")

page_break(doc)

# ─────────────────────────────────────────────────────────────────────────────
# CHAPTER 9 — CONCLUSIONS
# ─────────────────────────────────────────────────────────────────────────────

add_heading(doc, "9. Συμπεράσματα", 1)

add_heading(doc, "9.1 Επιτεύγματα", 2)

body(doc,
     "Η παρούσα εργασία επέτυχε τον σχεδιασμό και την υλοποίηση ενός ολοκληρωμένου "
     "multi-agent συστήματος για αυτοματοποιημένη επιδιόρθωση ευπαθειών κώδικα. "
     "Τα βασικά επιτεύγματα περιλαμβάνουν:")

achievements = [
    ("Πλήρης αυτοματοποίηση κύκλου ζωής",
     " — Από την ανίχνευση (SonarQube) μέχρι τη διόρθωση, τον έλεγχο, την αξιολόγηση, "
     "το commit, και την επαλήθευση με ελάχιστη ανθρώπινη παρέμβαση."),
    ("Αυτο-βελτίωση μέσω AI Reflection",
     " — Ο μηχανισμός retry loop με feedback επιτρέπει στον Fixer να μάθει "
     "από τα λάθη του χωρίς επαναεκπαίδευση."),
    ("Τηλεμετρία και διαχείριση κόστους",
     " — Κάθε LLM κλήση καταγράφεται με ακριβή στοιχεία tokens και κόστους USD."),
    ("Ευελιξία LLM provider",
     " — Εναλλαγή μεταξύ OpenAI, Ollama, OpenRouter κ.λπ. χωρίς αλλαγή κώδικα."),
    ("Πολλαπλοί τρόποι χρήσης",
     " — CLI, REST API, και Streamlit dashboard για διαφορετικές ανάγκες χρηστών."),
    ("Containerized deployment",
     " — Docker Compose για εύκολη ανάπτυξη χωρίς εξάρτηση από τοπικό περιβάλλον."),
]
for label, rest in achievements:
    bold_inline(doc, label, rest, indent=1)

add_heading(doc, "9.2 Τεχνικές Προκλήσεις", 2)

challenges = [
    ("Ακρίβεια surgical fixes",
     " — Η αντιστοίχιση old_code στον πραγματικό κώδικα απαιτεί "
     "fallback μηχανισμούς λόγω whitespace/newline διαφορών στην έξοδο του LLM."),
    ("Sandbox εκτέλεσης tests",
     " — Η εκτέλεση AI-παραγόμενου κώδικα απαιτεί timeout protection (60s) "
     "και ελεγχόμενο Docker περιβάλλον."),
    ("SonarQube Compute Engine latency",
     " — Η ανάλυση μετά το scan δεν είναι σύγχρονη, "
     "απαιτώντας polling mechanism με configurable timeout."),
]
for label, rest in challenges:
    bold_inline(doc, label, rest, indent=1)

add_heading(doc, "9.3 Μελλοντικές Επεκτάσεις", 2)

future = [
    "Υποστήριξη πολλαπλών γλωσσών (Java, JavaScript, C#)",
    "Ενσωμάτωση με CI/CD pipelines (GitHub Actions, GitLab CI)",
    "Ranking/prioritization ζητημάτων βάσει σοβαρότητας",
    "Παράλληλη επεξεργασία πολλαπλών issues με thread pool",
    "Fine-tuning μοντέλων σε domain-specific code patterns",
]
for item in future:
    p = doc.add_paragraph(style="List Bullet")
    run = p.add_run(item)
    run.font.name = "Times New Roman"
    run.font.size = Pt(12)

page_break(doc)

# ─────────────────────────────────────────────────────────────────────────────
# REFERENCES
# ─────────────────────────────────────────────────────────────────────────────

add_heading(doc, "10. Πηγές – Βιβλιογραφία", 1)

refs = [
    "Anthropic (2024). Claude 3 Family. Ανάκτηση Ιούνιος 2026, από https://www.anthropic.com/claude",
    "Chen, M., Tworek, J., Jun, H., et al. (2021). Evaluating Large Language Models Trained on Code. arXiv preprint arXiv:2107.03374. https://arxiv.org/abs/2107.03374",
    "Docker Inc. (2024). Docker Compose. Ανάκτηση Ιούνιος 2026, από https://docs.docker.com/compose/",
    "FastAPI (2024). FastAPI — Modern, Fast, Web Framework for Building APIs. Ανάκτηση Ιούνιος 2026, από https://fastapi.tiangolo.com/",
    "OpenAI (2024). Function calling. OpenAI Platform Docs. Ανάκτηση Ιούνιος 2026, από https://platform.openai.com/docs/guides/function-calling",
    "OpenAI (2024). GPT-4o. Ανάκτηση Ιούνιος 2026, από https://openai.com/index/gpt-4o/",
    "OpenAI (2024). Structured Outputs. OpenAI Platform Docs. Ανάκτηση Ιούνιος 2026, από https://platform.openai.com/docs/guides/structured-outputs",
    "Pydantic (2024). Pydantic — Data validation using Python type annotations. Ανάκτηση Ιούνιος 2026, από https://docs.pydantic.dev/",
    "pytest (2024). pytest: simple powerful testing with Python. Ανάκτηση Ιούνιος 2026, από https://docs.pytest.org/",
    "SonarSource (2024). SonarQube — Continuous Code Quality. Ανάκτηση Ιούνιος 2026, από https://www.sonarsource.com/products/sonarqube/",
    "SonarSource (2024). SonarQube Web API Documentation. Ανάκτηση Ιούνιος 2026, από https://docs.sonarsource.com/sonarqube/latest/extension-guide/web-api/",
    "SQLAlchemy (2024). SQLAlchemy — The Database Toolkit for Python. Ανάκτηση Ιούνιος 2026, από https://www.sqlalchemy.org/",
    "Streamlit (2024). Streamlit — A faster way to build and share data apps. Ανάκτηση Ιούνιος 2026, από https://streamlit.io/",
    "Touvron, H., Lavril, T., Izacard, G., et al. (2023). LLaMA: Open and Efficient Foundation Language Models. arXiv preprint arXiv:2302.13971. https://arxiv.org/abs/2302.13971",
]

for ref in refs:
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    p.paragraph_format.space_after = Pt(6)
    p.paragraph_format.left_indent = Cm(1)
    p.paragraph_format.first_line_indent = Cm(-1)
    run = p.add_run(ref)
    run.font.name = "Times New Roman"
    run.font.size = Pt(11)

page_break(doc)

# ─────────────────────────────────────────────────────────────────────────────
# APPENDIX A — FILE STRUCTURE
# ─────────────────────────────────────────────────────────────────────────────

add_heading(doc, "Παράρτημα Α — Δομή Αρχείων Έργου", 1)

add_table(doc,
    headers=["Αρχείο", "Περιγραφή"],
    rows=[
        ["ui.py", "Streamlit web dashboard (4 σελίδες)"],
        ["main.py", "CLI entry point"],
        ["api.py", "FastAPI REST API (7 endpoints)"],
        ["sonarcube_client.py", "SonarQube API client με pagination"],
        ["models.py", "Pydantic/dataclass μοντέλα δεδομένων"],
        ["database.py", "SQLAlchemy ORM + analytics queries"],
        ["log_config.py", "Centralized logging configuration"],
        ["agents/agent.py", "Βασική κλάση agent με tracked LLM calls"],
        ["agents/coordinator.py", "Ενορχήστρωση pipeline + retry logic"],
        ["agents/fixer.py", "Χειρουργική διόρθωση κώδικα (tool calling)"],
        ["agents/tester.py", "Δυναμική παραγωγή + εκτέλεση pytest"],
        ["agents/reviewer.py", "Αξιολόγηση ποιότητας (structured output)"],
        ["agents/evaluator.py", "Τελική βαθμολόγηση + PASS/RETRY/FAIL"],
        ["Dockerfile", "Container image definition"],
        ["docker-compose.yml", "Full stack (app + SonarQube)"],
        ["start.sh", "Startup script (FastAPI + Streamlit)"],
        ["requirements.docker.txt", "Lean Docker dependencies"],
        ["tests/test_verification.py", "Unit/integration tests (14 test cases)"],
    ],
    caption="Πίνακας 8 — Δομή Αρχείων Έργου")

add_heading(doc, "Παράρτημα Β — Τεχνολογίες και Εξαρτήσεις", 1)

add_table(doc,
    headers=["Τεχνολογία", "Χρήση", "Έκδοση"],
    rows=[
        ["Python", "Γλώσσα υλοποίησης", "≥ 3.12"],
        ["OpenAI SDK", "LLM API client", "≥ 1.109.0"],
        ["FastAPI", "REST API framework", "≥ 0.115.0"],
        ["Uvicorn", "ASGI server", "≥ 0.34.0"],
        ["Streamlit", "Web dashboard", "≥ 1.40.0"],
        ["SQLAlchemy", "ORM / database", "≥ 2.0.0"],
        ["Pydantic", "Data validation / structured outputs", "≥ 2.0.0"],
        ["pytest", "Testing framework", "≥ 9.0.0"],
        ["Requests", "HTTP client", "≥ 2.32.0"],
        ["python-dotenv", "Environment configuration", "≥ 1.1.0"],
        ["Docker", "Containerization", "—"],
        ["SonarQube", "Static code analysis", "Community Edition"],
        ["sonar-scanner-cli", "CLI scanner", "v6.2.1"],
    ],
    caption="Πίνακας 7 — Τεχνολογίες και Εξαρτήσεις")

# ─────────────────────────────────────────────────────────────────────────────
# SAVE
# ─────────────────────────────────────────────────────────────────────────────

doc.save(OUTPUT_FILE)
print(f"✅ Document saved as: {OUTPUT_FILE}")
print(f"   Pages: ~30 | Tables: 8 | Figures: 6")
