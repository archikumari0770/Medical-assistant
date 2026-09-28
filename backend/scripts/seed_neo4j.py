"""
Applies Neo4j schema constraints and loads a substantially expanded demo
knowledge graph — conditions, symptoms, medications, drug interactions/
contraindications, lab findings, and differential-diagnosis pairs.

IMPORTANT: this is original, textbook-level illustrative data written for
this prototype, not sourced from or validated against real clinical
guidelines. It exists to exercise every part of the schema (candidate
generation, medication safety checks, differentials) with realistic
*shape*, not to be clinically authoritative. Replace with a properly
sourced and validated knowledge base before any real use — see the
disclaimers already built into AnalysisResult and the narrator prompt.

Run from backend/:  python -m scripts.seed_neo4j
"""
import asyncio
import uuid

from app.database.neo4j import close_driver, run_query
from app.graph.schema import apply_constraints

# ---------------------------------------------------------------------
# Conditions
# ---------------------------------------------------------------------
DEMO_CONDITIONS = [
    {"name": "Influenza", "icd10": "J10", "description": "Acute viral respiratory infection with abrupt onset of fever and systemic symptoms."},
    {"name": "Common Cold", "icd10": "J00", "description": "Mild viral upper respiratory infection with gradual onset, prominent nasal symptoms."},
    {"name": "COVID-19", "icd10": "U07.1", "description": "Viral respiratory infection notable for possible loss of taste/smell and variable severity."},
    {"name": "Community-Acquired Pneumonia", "icd10": "J18.9", "description": "Lung infection acquired outside hospital settings, often with focal infiltrate."},
    {"name": "Acute Bronchitis", "icd10": "J20.9", "description": "Inflammation of the bronchial airways, usually viral, without consolidation."},
    {"name": "Asthma Exacerbation", "icd10": "J45.901", "description": "Acute worsening of reversible airway obstruction."},
    {"name": "Acute Coronary Syndrome", "icd10": "I24.9", "description": "Spectrum of conditions from unstable angina to myocardial infarction."},
    {"name": "Stable Angina", "icd10": "I20.9", "description": "Predictable exertional chest discomfort relieved by rest."},
    {"name": "Pericarditis", "icd10": "I30.9", "description": "Inflammation of the pericardium, often with positional chest pain."},
    {"name": "Atrial Fibrillation", "icd10": "I48.91", "description": "Irregular, often rapid heart rhythm originating in the atria."},
    {"name": "Heart Failure Exacerbation", "icd10": "I50.9", "description": "Acute worsening of chronic heart failure with fluid overload."},
    {"name": "Gastroenteritis", "icd10": "K52.9", "description": "Inflammation of the GI tract, often infectious, with diarrhea and vomiting."},
    {"name": "GERD", "icd10": "K21.9", "description": "Gastroesophageal reflux causing heartburn and regurgitation."},
    {"name": "Peptic Ulcer Disease", "icd10": "K27.9", "description": "Mucosal ulceration of the stomach or duodenum."},
    {"name": "Appendicitis", "icd10": "K35.80", "description": "Acute inflammation of the appendix, classically with RLQ pain."},
    {"name": "Cholecystitis", "icd10": "K81.0", "description": "Inflammation of the gallbladder, often related to gallstones."},
    {"name": "Migraine", "icd10": "G43.9", "description": "Primary headache disorder, often unilateral and pulsating."},
    {"name": "Tension-Type Headache", "icd10": "G44.209", "description": "Bilateral, pressing headache not aggravated by routine activity."},
    {"name": "Cluster Headache", "icd10": "G44.009", "description": "Severe unilateral periorbital headache with autonomic features, occurring in clusters."},
    {"name": "Urinary Tract Infection", "icd10": "N39.0", "description": "Bacterial infection of the urinary tract."},
    {"name": "Cellulitis", "icd10": "L03.90", "description": "Bacterial skin and soft tissue infection with redness, warmth, and swelling."},
    {"name": "Anaphylaxis", "icd10": "T78.2", "description": "Severe, rapidly progressive systemic allergic reaction."},
    {"name": "Panic Attack", "icd10": "F41.0", "description": "Sudden episode of intense fear with prominent somatic symptoms."},
    {"name": "Costochondritis", "icd10": "M94.0", "description": "Inflammation of costal cartilage causing reproducible chest wall pain."},
    {"name": "Diabetic Ketoacidosis", "icd10": "E11.10", "description": "Life-threatening metabolic complication of diabetes with hyperglycemia and ketosis."},
    {"name": "Hypoglycemia", "icd10": "E16.2", "description": "Abnormally low blood glucose, often medication-related in diabetics."},
]

# ---------------------------------------------------------------------
# Symptoms (name -> synonyms). This list is mirrored in
# app/nlp/extractor.py's SYMPTOM_VOCAB and the frontend's SymptomInput
# chip list — keep those in sync if you add more here.
# ---------------------------------------------------------------------
DEMO_SYMPTOMS = {
    "fever": [],
    "chills": [],
    "cough": [],
    "productive cough": [],
    "sore throat": [],
    "runny nose": [],
    "nasal congestion": ["stuffy nose"],
    "sneezing": [],
    "loss of taste or smell": [],
    "shortness of breath": ["SOB", "difficulty breathing"],
    "wheezing": [],
    "chest pain": [],
    "pleuritic chest pain": [],
    "palpitations": ["heart racing", "racing heart"],
    "leg swelling": [],
    "headache": ["head pain"],
    "one-sided headache": [],
    "sensitivity to light": ["photophobia"],
    "visual aura": [],
    "facial swelling": [],
    "throat tightness": [],
    "hives": [],
    "nausea": [],
    "vomiting": [],
    "diarrhea": [],
    "abdominal pain": ["stomach ache", "stomach pain"],
    "right upper quadrant pain": [],
    "right lower quadrant pain": [],
    "heartburn": [],
    "black stools": [],
    "bloating": [],
    "fatigue": [],
    "muscle aches": [],
    "night sweats": [],
    "weight loss": [],
    "joint pain": [],
    "back pain": [],
    "dizziness": [],
    "confusion": [],
    "rash": [],
    "swelling": [],
    "urinary frequency": [],
    "painful urination": [],
    "flank pain": [],
    "excessive thirst": [],
    "fruity breath odor": [],
    "sweating": [],
    "tremor": [],
    "anxiety": [],
}

# (symptom, condition, weight 0-1)
SYMPTOM_CONDITION_EDGES = [
    ("fever", "Influenza", 0.85), ("chills", "Influenza", 0.6), ("cough", "Influenza", 0.6),
    ("muscle aches", "Influenza", 0.75), ("fatigue", "Influenza", 0.6), ("sore throat", "Influenza", 0.4),
    ("runny nose", "Common Cold", 0.85), ("nasal congestion", "Common Cold", 0.8), ("sneezing", "Common Cold", 0.75),
    ("sore throat", "Common Cold", 0.6), ("cough", "Common Cold", 0.4), ("fatigue", "Common Cold", 0.3),
    ("fever", "COVID-19", 0.6), ("cough", "COVID-19", 0.6), ("loss of taste or smell", "COVID-19", 0.7),
    ("fatigue", "COVID-19", 0.55), ("shortness of breath", "COVID-19", 0.4), ("sore throat", "COVID-19", 0.35),
    ("fever", "Community-Acquired Pneumonia", 0.7), ("productive cough", "Community-Acquired Pneumonia", 0.8),
    ("shortness of breath", "Community-Acquired Pneumonia", 0.75), ("pleuritic chest pain", "Community-Acquired Pneumonia", 0.55),
    ("chills", "Community-Acquired Pneumonia", 0.4), ("confusion", "Community-Acquired Pneumonia", 0.25),
    ("cough", "Acute Bronchitis", 0.85), ("productive cough", "Acute Bronchitis", 0.6),
    ("fatigue", "Acute Bronchitis", 0.35), ("sore throat", "Acute Bronchitis", 0.3),
    ("shortness of breath", "Asthma Exacerbation", 0.85), ("wheezing", "Asthma Exacerbation", 0.85),
    ("cough", "Asthma Exacerbation", 0.5), ("chest pain", "Asthma Exacerbation", 0.3),
    ("chest pain", "Acute Coronary Syndrome", 0.9), ("shortness of breath", "Acute Coronary Syndrome", 0.55),
    ("sweating", "Acute Coronary Syndrome", 0.5), ("nausea", "Acute Coronary Syndrome", 0.35), ("fatigue", "Acute Coronary Syndrome", 0.3),
    ("chest pain", "Stable Angina", 0.8), ("shortness of breath", "Stable Angina", 0.4), ("fatigue", "Stable Angina", 0.25),
    ("chest pain", "Pericarditis", 0.75), ("pleuritic chest pain", "Pericarditis", 0.7), ("fever", "Pericarditis", 0.3),
    ("palpitations", "Atrial Fibrillation", 0.8), ("dizziness", "Atrial Fibrillation", 0.45),
    ("shortness of breath", "Atrial Fibrillation", 0.4), ("fatigue", "Atrial Fibrillation", 0.35),
    ("shortness of breath", "Heart Failure Exacerbation", 0.8), ("leg swelling", "Heart Failure Exacerbation", 0.75),
    ("fatigue", "Heart Failure Exacerbation", 0.5), ("weight loss", "Heart Failure Exacerbation", 0.15),
    ("nausea", "Gastroenteritis", 0.7), ("vomiting", "Gastroenteritis", 0.8), ("diarrhea", "Gastroenteritis", 0.85),
    ("abdominal pain", "Gastroenteritis", 0.6), ("fever", "Gastroenteritis", 0.3),
    ("heartburn", "GERD", 0.85), ("bloating", "GERD", 0.3), ("abdominal pain", "GERD", 0.25),
    ("abdominal pain", "Peptic Ulcer Disease", 0.75), ("heartburn", "Peptic Ulcer Disease", 0.4),
    ("black stools", "Peptic Ulcer Disease", 0.35), ("nausea", "Peptic Ulcer Disease", 0.3),
    ("right lower quadrant pain", "Appendicitis", 0.85), ("abdominal pain", "Appendicitis", 0.6),
    ("nausea", "Appendicitis", 0.5), ("fever", "Appendicitis", 0.4), ("vomiting", "Appendicitis", 0.35),
    ("right upper quadrant pain", "Cholecystitis", 0.85), ("abdominal pain", "Cholecystitis", 0.5),
    ("nausea", "Cholecystitis", 0.5), ("vomiting", "Cholecystitis", 0.4), ("fever", "Cholecystitis", 0.35),
    ("headache", "Migraine", 0.85), ("one-sided headache", "Migraine", 0.6), ("nausea", "Migraine", 0.5),
    ("sensitivity to light", "Migraine", 0.55), ("visual aura", "Migraine", 0.3),
    ("headache", "Tension-Type Headache", 0.8), ("fatigue", "Tension-Type Headache", 0.3),
    ("one-sided headache", "Cluster Headache", 0.75), ("headache", "Cluster Headache", 0.6),
    ("painful urination", "Urinary Tract Infection", 0.8), ("urinary frequency", "Urinary Tract Infection", 0.75),
    ("flank pain", "Urinary Tract Infection", 0.3), ("fever", "Urinary Tract Infection", 0.25),
    ("swelling", "Cellulitis", 0.7), ("rash", "Cellulitis", 0.5), ("fever", "Cellulitis", 0.35),
    ("hives", "Anaphylaxis", 0.8), ("facial swelling", "Anaphylaxis", 0.75), ("throat tightness", "Anaphylaxis", 0.8),
    ("shortness of breath", "Anaphylaxis", 0.6), ("dizziness", "Anaphylaxis", 0.4),
    ("anxiety", "Panic Attack", 0.85), ("palpitations", "Panic Attack", 0.65), ("shortness of breath", "Panic Attack", 0.5),
    ("dizziness", "Panic Attack", 0.45), ("sweating", "Panic Attack", 0.4), ("tremor", "Panic Attack", 0.3),
    ("chest pain", "Costochondritis", 0.7), ("pleuritic chest pain", "Costochondritis", 0.3),
    ("excessive thirst", "Diabetic Ketoacidosis", 0.7), ("fruity breath odor", "Diabetic Ketoacidosis", 0.6),
    ("nausea", "Diabetic Ketoacidosis", 0.5), ("vomiting", "Diabetic Ketoacidosis", 0.45),
    ("confusion", "Diabetic Ketoacidosis", 0.35), ("urinary frequency", "Diabetic Ketoacidosis", 0.4),
    ("sweating", "Hypoglycemia", 0.7), ("tremor", "Hypoglycemia", 0.65), ("confusion", "Hypoglycemia", 0.5),
    ("dizziness", "Hypoglycemia", 0.5), ("anxiety", "Hypoglycemia", 0.35),
]

# ---------------------------------------------------------------------
# Medications
# ---------------------------------------------------------------------
DEMO_MEDICATIONS = [
    {"name": "Oseltamivir", "drug_class": "Antiviral (neuraminidase inhibitor)"},
    {"name": "Amoxicillin", "drug_class": "Antibiotic (aminopenicillin)"},
    {"name": "Azithromycin", "drug_class": "Antibiotic (macrolide)"},
    {"name": "Sumatriptan", "drug_class": "Triptan (5-HT1 agonist)"},
    {"name": "Ondansetron", "drug_class": "Antiemetic (5-HT3 antagonist)"},
    {"name": "Loperamide", "drug_class": "Antidiarrheal"},
    {"name": "Albuterol", "drug_class": "Short-acting beta-2 agonist"},
    {"name": "Prednisone", "drug_class": "Corticosteroid"},
    {"name": "Omeprazole", "drug_class": "Proton pump inhibitor"},
    {"name": "Metronidazole", "drug_class": "Antibiotic (nitroimidazole)"},
    {"name": "Ceftriaxone", "drug_class": "Antibiotic (cephalosporin)"},
    {"name": "Aspirin", "drug_class": "Antiplatelet / NSAID"},
    {"name": "Clopidogrel", "drug_class": "Antiplatelet (P2Y12 inhibitor)"},
    {"name": "Warfarin", "drug_class": "Anticoagulant (vitamin K antagonist)"},
    {"name": "Metoprolol", "drug_class": "Beta-blocker"},
    {"name": "Lisinopril", "drug_class": "ACE inhibitor"},
    {"name": "Furosemide", "drug_class": "Loop diuretic"},
    {"name": "Epinephrine", "drug_class": "Alpha/beta agonist (emergency)"},
    {"name": "Ibuprofen", "drug_class": "NSAID"},
    {"name": "Insulin", "drug_class": "Antidiabetic hormone"},
]

# (condition, medication) — TREATED_BY
CONDITION_MEDICATION_EDGES = [
    ("Influenza", "Oseltamivir"),
    ("Community-Acquired Pneumonia", "Amoxicillin"),
    ("Community-Acquired Pneumonia", "Azithromycin"),
    ("Acute Bronchitis", "Albuterol"),
    ("Asthma Exacerbation", "Albuterol"),
    ("Asthma Exacerbation", "Prednisone"),
    ("Migraine", "Sumatriptan"),
    ("Gastroenteritis", "Ondansetron"),
    ("Gastroenteritis", "Loperamide"),
    ("GERD", "Omeprazole"),
    ("Peptic Ulcer Disease", "Omeprazole"),
    ("Cholecystitis", "Metronidazole"),
    ("Urinary Tract Infection", "Ceftriaxone"),
    ("Cellulitis", "Ceftriaxone"),
    ("Acute Coronary Syndrome", "Aspirin"),
    ("Acute Coronary Syndrome", "Clopidogrel"),
    ("Atrial Fibrillation", "Metoprolol"),
    ("Atrial Fibrillation", "Warfarin"),
    ("Heart Failure Exacerbation", "Furosemide"),
    ("Heart Failure Exacerbation", "Metoprolol"),
    ("Anaphylaxis", "Epinephrine"),
    ("Diabetic Ketoacidosis", "Insulin"),
]

# (medication_a, medication_b, severity) — INTERACTS_WITH
MEDICATION_INTERACTIONS = [
    ("Warfarin", "Aspirin", "major"),
    ("Warfarin", "Ibuprofen", "major"),
    ("Lisinopril", "Ibuprofen", "moderate"),
    ("Metoprolol", "Albuterol", "moderate"),
    ("Clopidogrel", "Omeprazole", "moderate"),
]

# (medication, condition) — CONTRAINDICATED_FOR
MEDICATION_CONTRAINDICATIONS = [
    ("Ibuprofen", "Peptic Ulcer Disease"),
    ("Ibuprofen", "Heart Failure Exacerbation"),
    ("Metoprolol", "Asthma Exacerbation"),
    ("Sumatriptan", "Acute Coronary Syndrome"),
    ("Sumatriptan", "Stable Angina"),
]

# ---------------------------------------------------------------------
# Lab findings
# ---------------------------------------------------------------------
DEMO_LAB_FINDINGS = [
    {"name": "Elevated WBC", "normal_range": "4,500-11,000/uL"},
    {"name": "Elevated Troponin", "normal_range": "<0.04 ng/mL"},
    {"name": "Elevated Blood Glucose", "normal_range": "70-99 mg/dL fasting"},
    {"name": "Elevated Ketones", "normal_range": "negative"},
    {"name": "Elevated Bilirubin", "normal_range": "0.1-1.2 mg/dL"},
    {"name": "Hypoxia (Low Oxygen Saturation)", "normal_range": ">=95%"},
    {"name": "Positive Influenza Antigen", "normal_range": "negative"},
]

# (condition, lab_finding) — ASSOCIATED_WITH
CONDITION_LABFINDING_EDGES = [
    ("Influenza", "Positive Influenza Antigen"),
    ("Community-Acquired Pneumonia", "Elevated WBC"),
    ("Community-Acquired Pneumonia", "Hypoxia (Low Oxygen Saturation)"),
    ("Appendicitis", "Elevated WBC"),
    ("Cellulitis", "Elevated WBC"),
    ("Acute Coronary Syndrome", "Elevated Troponin"),
    ("Cholecystitis", "Elevated Bilirubin"),
    ("Diabetic Ketoacidosis", "Elevated Blood Glucose"),
    ("Diabetic Ketoacidosis", "Elevated Ketones"),
]

# (condition_a, condition_b, distinguishing_feature) — DIFFERENTIAL_OF
# Query in app/graph/queries.py matches this relationship in either
# direction, so one entry per pair is enough.
DIFFERENTIALS = [
    ("Influenza", "Common Cold",
     "Influenza has abrupt onset with high fever and prominent myalgia; the common cold is milder with gradual onset and dominant nasal symptoms."),
    ("Influenza", "COVID-19",
     "Loss of taste or smell is comparatively more specific to COVID-19; the two otherwise overlap substantially."),
    ("Community-Acquired Pneumonia", "Acute Bronchitis",
     "Pneumonia typically shows a focal infiltrate on imaging with more systemic toxicity; bronchitis is a clinical diagnosis without consolidation."),
    ("Migraine", "Tension-Type Headache",
     "Migraine is typically unilateral and pulsating with nausea/photophobia and worsens with activity; tension headache is bilateral, pressing, and not activity-aggravated."),
    ("Migraine", "Cluster Headache",
     "Cluster headache is strictly unilateral and periorbital with same-side autonomic features (tearing, nasal congestion), occurring in clusters."),
    ("Acute Coronary Syndrome", "Costochondritis",
     "ACS pain is often exertional or pressure-like with possible radiation and autonomic symptoms; costochondritis pain is reproducible with chest wall palpation."),
    ("Acute Coronary Syndrome", "GERD",
     "GERD discomfort often relates to meals or lying down; ACS is not reliably relieved by antacids and may follow an exertional pattern."),
    ("Acute Coronary Syndrome", "Panic Attack",
     "Panic attacks often build rapidly with prominent anxiety and paresthesias; ACS more classically has an exertional pattern and cardiac risk factors."),
    ("Appendicitis", "Gastroenteritis",
     "Appendicitis typically localizes to the right lower quadrant with focal tenderness; gastroenteritis pain is usually diffuse with prominent diarrhea."),
    ("Cholecystitis", "Peptic Ulcer Disease",
     "Cholecystitis pain is right upper quadrant and often worse after fatty meals; PUD pain is epigastric and relates more to fasting or eating timing."),
    ("Heart Failure Exacerbation", "Community-Acquired Pneumonia",
     "Heart failure often has bilateral leg swelling and orthopnea; pneumonia more often has focal findings with fever and productive cough."),
    ("Anaphylaxis", "Asthma Exacerbation",
     "Anaphylaxis typically involves skin/mucosal findings (hives, facial swelling) with multi-system involvement; asthma exacerbation is primarily respiratory."),
    ("Diabetic Ketoacidosis", "Gastroenteritis",
     "DKA presents with polyuria, excessive thirst, and fruity breath odor alongside GI symptoms; gastroenteritis lacks this metabolic derangement pattern."),
    ("Hypoglycemia", "Panic Attack",
     "Hypoglycemia symptoms resolve rapidly with glucose and often relate to medication/food timing; panic attacks do not respond to glucose."),
]


async def seed():
    print("Applying constraints...")
    await apply_constraints()

    print(f"Seeding {len(DEMO_CONDITIONS)} conditions...")
    for cond in DEMO_CONDITIONS:
        await run_query(
            "MERGE (c:Condition {name: $name}) "
            "SET c.id = coalesce(c.id, $id), c.icd10 = $icd10, c.description = $description",
            {"id": str(uuid.uuid4()), **cond},
        )

    print(f"Seeding {len(DEMO_SYMPTOMS)} symptoms...")
    for name, synonyms in DEMO_SYMPTOMS.items():
        await run_query(
            "MERGE (s:Symptom {name: $name}) "
            "SET s.id = coalesce(s.id, $id), s.synonyms = $synonyms",
            {"id": str(uuid.uuid4()), "name": name, "synonyms": [s.lower() for s in synonyms]},
        )

    print(f"Seeding {len(SYMPTOM_CONDITION_EDGES)} symptom to condition edges...")
    for symptom, condition, weight in SYMPTOM_CONDITION_EDGES:
        await run_query(
            "MATCH (s:Symptom {name: $symptom}), (c:Condition {name: $condition}) "
            "MERGE (s)-[r:INDICATES]->(c) SET r.weight = $weight",
            {"symptom": symptom, "condition": condition, "weight": weight},
        )

    print(f"Seeding {len(DEMO_MEDICATIONS)} medications...")
    for med in DEMO_MEDICATIONS:
        await run_query(
            "MERGE (m:Medication {name: $name}) SET m.id = coalesce(m.id, $id), m.drug_class = $drug_class",
            {"id": str(uuid.uuid4()), **med},
        )

    print(f"Seeding {len(CONDITION_MEDICATION_EDGES)} condition to medication edges...")
    for condition, medication in CONDITION_MEDICATION_EDGES:
        await run_query(
            "MATCH (c:Condition {name: $condition}), (m:Medication {name: $medication}) "
            "MERGE (c)-[:TREATED_BY]->(m)",
            {"condition": condition, "medication": medication},
        )

    print(f"Seeding {len(MEDICATION_INTERACTIONS)} medication interactions...")
    for med_a, med_b, severity in MEDICATION_INTERACTIONS:
        await run_query(
            "MATCH (m1:Medication {name: $med_a}), (m2:Medication {name: $med_b}) "
            "MERGE (m1)-[r:INTERACTS_WITH]-(m2) SET r.severity = $severity",
            {"med_a": med_a, "med_b": med_b, "severity": severity},
        )

    print(f"Seeding {len(MEDICATION_CONTRAINDICATIONS)} medication contraindications...")
    for medication, condition in MEDICATION_CONTRAINDICATIONS:
        await run_query(
            "MATCH (m:Medication {name: $medication}), (c:Condition {name: $condition}) "
            "MERGE (m)-[:CONTRAINDICATED_FOR]->(c)",
            {"medication": medication, "condition": condition},
        )

    print(f"Seeding {len(DEMO_LAB_FINDINGS)} lab findings...")
    for lab in DEMO_LAB_FINDINGS:
        await run_query(
            "MERGE (l:LabFinding {name: $name}) SET l.id = coalesce(l.id, $id), l.normal_range = $normal_range",
            {"id": str(uuid.uuid4()), **lab},
        )

    print(f"Seeding {len(CONDITION_LABFINDING_EDGES)} condition to lab finding edges...")
    for condition, lab in CONDITION_LABFINDING_EDGES:
        await run_query(
            "MATCH (c:Condition {name: $condition}), (l:LabFinding {name: $lab}) "
            "MERGE (c)-[:ASSOCIATED_WITH]->(l)",
            {"condition": condition, "lab": lab},
        )

    print(f"Seeding {len(DIFFERENTIALS)} differential-diagnosis pairs...")
    for cond_a, cond_b, feature in DIFFERENTIALS:
        await run_query(
            "MATCH (a:Condition {name: $cond_a}), (b:Condition {name: $cond_b}) "
            "MERGE (a)-[r:DIFFERENTIAL_OF]-(b) SET r.distinguishing_feature = $feature",
            {"cond_a": cond_a, "cond_b": cond_b, "feature": feature},
        )

    print("Done.")
    await close_driver()


if __name__ == "__main__":
    asyncio.run(seed())