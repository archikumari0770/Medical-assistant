"""
Populates the medical_knowledge Qdrant collection with reference material
covering all 26 conditions in the knowledge graph (see scripts/seed_neo4j.py) -
one paragraph per condition, for consistency between the two knowledge
sources used by the decision-support pipeline.

The text below is original writing for this prototype -- general,
textbook-level background -- NOT copied from any specific published
source. Treat it as a placeholder to prove the RAG pipeline works
end-to-end, not as a clinically validated reference. For real use,
replace this with material you have the rights to index.

Note on wording: an earlier evaluation (see scripts/eval_rag.py) found
that describing a condition by explicitly negating a confusable
neighbor's symptoms (e.g. "unlike X, high fever is uncommon") creates
false lexical/semantic overlap that embedding models pick up on despite
the negation -- they encode co-occurring terms, not logical polarity.
These paragraphs are written to describe each condition primarily on
its own positive terms, minimizing that pattern.

Run from backend/ (after Docker is up):
    python -m scripts.seed_medical_knowledge
"""
import asyncio

from app.config import settings
from app.database.qdrant import ensure_collections, get_client
from app.rag.medical_rag import index_medical_reference

REFERENCES = [
    (
        "Influenza — overview",
        "Influenza is an acute viral respiratory illness caused by influenza A or B viruses, typically "
        "spread by respiratory droplets. Onset is usually abrupt, with fever, chills, headache, myalgia, "
        "and fatigue appearing alongside respiratory symptoms such as cough and sore throat. Most cases "
        "in otherwise healthy individuals are self-limited and resolve within a week to ten days, though "
        "fatigue can linger longer. Young children, older adults, pregnant individuals, and those with "
        "chronic cardiopulmonary conditions are at higher risk of complications such as secondary "
        "bacterial pneumonia. Antiviral treatment such as oseltamivir is most effective when started "
        "within 48 hours of symptom onset.",
    ),
    (
        "Common Cold — overview",
        "The common cold is a mild viral upper respiratory infection, most often caused by rhinoviruses. "
        "Onset is gradual, typically building over a day or two. The dominant features are nasal "
        "congestion, runny nose, sneezing, and a mild sore throat, with cough and tiredness usually "
        "minor. Body temperature is generally normal or only slightly elevated, and body aches are "
        "absent or very mild. Symptoms usually peak within two to three days and resolve within a week. "
        "Management is purely supportive -- rest, fluids, and over-the-counter symptom relief -- since no "
        "antiviral treatment is indicated.",
    ),
    (
        "COVID-19 — overview",
        "COVID-19 is a viral respiratory infection caused by SARS-CoV-2, transmitted primarily through "
        "respiratory droplets and aerosols. Presentation is highly variable, ranging from asymptomatic "
        "infection to severe respiratory failure. Common features include fever, cough, and fatigue, "
        "with a notable subset of patients experiencing altered or lost sense of taste or smell. Illness "
        "severity tends to increase with age and underlying cardiopulmonary or metabolic conditions. "
        "Most cases are managed with supportive care at home; warning signs prompting evaluation include "
        "persistent shortness of breath, chest pain, or low oxygen levels.",
    ),
    (
        "Community-Acquired Pneumonia — overview",
        "Community-acquired pneumonia is a lung infection acquired outside a hospital setting, most "
        "commonly caused by bacterial pathogens such as Streptococcus pneumoniae, though viral and "
        "atypical causes are also frequent. Typical presentation includes fever, productive cough, "
        "pleuritic chest pain, and dyspnea; some patients -- particularly older adults -- present with "
        "confusion or general decline rather than classic respiratory symptoms. Diagnosis is usually "
        "supported by chest imaging showing a new infiltrate. Severity assessment tools help determine "
        "whether outpatient treatment with amoxicillin or azithromycin, hospitalization, or higher-level "
        "care is appropriate.",
    ),
    (
        "Acute Bronchitis — overview",
        "Acute bronchitis is inflammation of the bronchial airways, usually following a viral upper "
        "respiratory infection. The hallmark feature is a persistent cough, often productive, lasting "
        "one to three weeks. Chest imaging, when obtained, is typically read as clear or shows only "
        "nonspecific changes. Fever is usually absent or low-grade, and the overall presentation is "
        "milder and more localized to the airways than a systemic lung infection. Treatment is largely "
        "supportive; antibiotics are not indicated for the typical viral case, and bronchodilators may "
        "help if wheezing is prominent.",
    ),
    (
        "Asthma Exacerbation — overview",
        "An asthma exacerbation is an acute worsening of underlying reversible airway obstruction, often "
        "triggered by allergens, respiratory infection, or irritant exposure. Presentation includes "
        "shortness of breath, wheezing, chest tightness, and cough, with symptoms often worse at night "
        "or with exertion. Peak flow or spirometry measurements typically show reduced airflow that "
        "improves with bronchodilator use. First-line treatment is inhaled short-acting beta-agonists "
        "such as albuterol, with systemic corticosteroids like prednisone added for moderate-to-severe "
        "episodes.",
    ),
    (
        "Acute Coronary Syndrome — overview",
        "Acute coronary syndrome encompasses unstable angina and myocardial infarction, resulting from "
        "reduced blood flow to the heart muscle. Classic presentation is pressure-like or squeezing "
        "chest pain, often radiating to the arm or jaw, accompanied by diaphoresis, nausea, or shortness "
        "of breath, and not reliably reproduced by chest wall palpation. Onset is frequently but not "
        "always related to exertion. Elevated cardiac troponin supports the diagnosis of infarction. "
        "Initial management includes aspirin and further risk stratification; vasoconstrictive "
        "medications such as sumatriptan are avoided given the underlying reduced coronary blood flow.",
    ),
    (
        "Stable Angina — overview",
        "Stable angina is predictable, exertional chest discomfort resulting from a fixed narrowing in a "
        "coronary artery that limits blood flow during increased cardiac demand. Episodes are typically "
        "brought on by physical exertion or emotional stress and resolve within minutes of rest or with "
        "nitroglycerin. The discomfort is often described as pressure or tightness. A consistent, "
        "predictable pattern that recurs similarly with similar levels of exertion is a hallmark feature, "
        "distinguishing it from a new or escalating pattern of chest pain that would raise concern for an "
        "acute coronary event.",
    ),
    (
        "Pericarditis — overview",
        "Pericarditis is inflammation of the thin sac surrounding the heart, often following a viral "
        "infection. The classic presentation is sharp, pleuritic chest pain that improves when sitting up "
        "and leaning forward and worsens when lying flat. A low-grade fever may accompany the pain. A "
        "pericardial friction rub may be heard on exam, and characteristic ECG changes can support the "
        "diagnosis. Most cases in otherwise healthy individuals are self-limited and respond to "
        "anti-inflammatory medication.",
    ),
    (
        "Atrial Fibrillation — overview",
        "Atrial fibrillation is an irregular, often rapid heart rhythm arising from disorganized "
        "electrical activity in the heart's upper chambers. Patients frequently notice palpitations "
        "described as a fluttering or irregular heartbeat, sometimes with associated dizziness, fatigue, "
        "or shortness of breath, though some cases are found incidentally without symptoms. An "
        "irregularly irregular pulse is a key exam finding. A central concern beyond symptoms is stroke "
        "risk from clot formation in the fibrillating atria, making anticoagulation with agents such as "
        "warfarin a major consideration alongside rate-control medications like metoprolol.",
    ),
    (
        "Heart Failure Exacerbation — overview",
        "A heart failure exacerbation is an acute worsening of the heart's ability to pump or fill "
        "effectively, leading to fluid accumulation. Common features include progressive shortness of "
        "breath, especially when lying flat, along with swelling in the legs and ankles and rapid weight "
        "gain from fluid retention. Fatigue and reduced exercise tolerance are also typical. Crackles "
        "heard at the lung bases on exam support the diagnosis. Management centers on diuretics such as "
        "furosemide to remove excess fluid, alongside adjustment of the patient's underlying heart "
        "failure medications.",
    ),
    (
        "Gastroenteritis — overview",
        "Gastroenteritis refers to inflammation of the gastrointestinal tract, most often caused by "
        "viral infection (norovirus and rotavirus being common culprits), though bacterial and parasitic "
        "causes also occur. Presentation typically includes nausea, vomiting, watery diarrhea, and "
        "diffuse abdominal cramping, usually with a rapid onset. Most cases are self-limited and managed "
        "with supportive care, particularly oral rehydration. Warning signs that warrant closer "
        "evaluation include high fever, bloody stools, signs of significant dehydration, or symptoms "
        "persisting beyond several days.",
    ),
    (
        "GERD — overview",
        "Gastroesophageal reflux disease results from stomach acid repeatedly flowing back into the "
        "esophagus, most often due to a weakened lower esophageal sphincter. The hallmark symptom is "
        "heartburn -- a burning sensation rising from the stomach toward the chest -- frequently "
        "accompanied by regurgitation of sour or bitter material, particularly after meals or when lying "
        "down. Symptoms often improve with acid-suppressing medication such as omeprazole. Chronic, "
        "poorly controlled reflux can lead to esophageal irritation over time, so persistent symptoms "
        "despite treatment warrant further evaluation.",
    ),
    (
        "Peptic Ulcer Disease — overview",
        "Peptic ulcer disease refers to mucosal erosion of the stomach or duodenum, most commonly caused "
        "by Helicobacter pylori infection or nonsteroidal anti-inflammatory drug use. Presentation is "
        "typically gnawing or burning epigastric pain, which for duodenal ulcers often improves "
        "temporarily with eating, while gastric ulcers may instead worsen with food. Nausea and bloating "
        "can accompany the pain. Bleeding ulcers can produce dark, tarry stools, a warning sign requiring "
        "urgent evaluation. Treatment includes acid suppression with agents like omeprazole and, when H. "
        "pylori is identified, antibiotic eradication therapy.",
    ),
    (
        "Appendicitis — overview",
        "Appendicitis is acute inflammation of the appendix, classically presenting with pain that "
        "begins diffusely around the umbilicus before localizing to the right lower quadrant over "
        "several hours. The pain is typically focal and worsened by movement or palpation of that "
        "specific area. Fever is usually low-grade initially, and nausea or a single episode of vomiting "
        "often follows the onset of pain rather than preceding it. Prompt surgical evaluation is "
        "warranted, as delayed diagnosis raises the risk of perforation.",
    ),
    (
        "Cholecystitis — overview",
        "Cholecystitis is inflammation of the gallbladder, most often triggered by a gallstone "
        "obstructing its outlet. The characteristic presentation is steady, severe pain in the right "
        "upper quadrant of the abdomen, frequently triggered or worsened after a fatty meal, sometimes "
        "radiating to the right shoulder blade. Fever, nausea, and vomiting commonly accompany the pain. "
        "Examination often reveals tenderness with inspiratory arrest on palpation of the right upper "
        "quadrant. Ultrasound is the initial imaging study of choice, and management typically involves "
        "antibiotics with surgical removal of the gallbladder.",
    ),
    (
        "Migraine — overview",
        "Migraine is a primary headache disorder characterized by recurrent moderate-to-severe headache "
        "episodes, often unilateral and pulsating, commonly accompanied by nausea and sensitivity to "
        "light or sound. Attacks typically last between four and seventy-two hours if untreated, and "
        "characteristically worsen with routine physical activity. A subset of patients experience an "
        "aura -- transient neurological symptoms, often visual -- preceding the headache. Acute treatment "
        "includes triptans such as sumatriptan; frequent or disabling migraine may warrant preventive "
        "therapy.",
    ),
    (
        "Tension-Type Headache — overview",
        "Tension-type headache is the most common primary headache disorder, presenting as a bilateral, "
        "pressing or band-like sensation of mild-to-moderate intensity. It is not aggravated by routine "
        "physical activity, and nausea or vomiting are notably absent, though mild sensitivity to light "
        "or sound can occur. Episodes can last from thirty minutes to several days. Stress and muscle "
        "tension are commonly implicated triggers. Simple analgesics are usually sufficient for acute "
        "episodes.",
    ),
    (
        "Cluster Headache — overview",
        "Cluster headache is a severe, strictly unilateral headache disorder centered around the eye or "
        "temple, often accompanied by same-side autonomic features such as tearing, nasal congestion, or "
        "eyelid drooping. Attacks are shorter than migraine, typically fifteen minutes to three hours, "
        "but recur multiple times daily in clusters lasting weeks to months, followed by long "
        "symptom-free remission periods. Patients are often restless and agitated during an attack, "
        "pacing rather than lying still.",
    ),
    (
        "Urinary Tract Infection — overview",
        "A urinary tract infection is a bacterial infection of the bladder or, less commonly, the "
        "kidneys, more frequent in women due to anatomical factors. Lower tract infections typically "
        "present with burning on urination, urinary frequency and urgency, and sometimes blood-tinged or "
        "cloudy urine, generally without systemic symptoms. Involvement of the kidneys is suggested by "
        "the addition of flank pain, fever, and chills, indicating a more serious infection requiring "
        "closer monitoring. Uncomplicated lower tract infections are usually treated with a short course "
        "of oral antibiotics such as ceftriaxone or similar agents.",
    ),
    (
        "Cellulitis — overview",
        "Cellulitis is a bacterial infection of the skin and underlying soft tissue, often entering "
        "through a break in the skin such as a cut, insect bite, or area of chronic skin irritation. It "
        "presents with an area of skin that is red, warm, swollen, and tender, with borders that are "
        "typically poorly defined and can spread over hours to days. Fever and chills may accompany more "
        "extensive infection. The affected skin is characteristically tender to touch. Treatment is with "
        "antibiotics targeting common skin bacteria.",
    ),
    (
        "Anaphylaxis — overview",
        "Anaphylaxis is a severe, rapidly progressive allergic reaction involving multiple body systems "
        "simultaneously, typically triggered by a food, medication, or insect sting in a sensitized "
        "individual. Onset is usually within minutes of exposure, with hives, swelling of the lips, "
        "face, or throat, and a sensation of throat tightness or difficulty breathing. Gastrointestinal "
        "symptoms, dizziness, and a drop in blood pressure can follow rapidly. Immediate treatment is "
        "intramuscular epinephrine, with emergency care sought regardless of initial response to "
        "treatment.",
    ),
    (
        "Panic Attack — overview",
        "A panic attack is a sudden surge of intense fear or discomfort that peaks within minutes, "
        "accompanied by prominent physical symptoms such as a racing heart, sweating, trembling, "
        "shortness of breath, and a sense of impending doom. Episodes are typically unprovoked or "
        "triggered by a specific stressor and are not associated with physical exertion. Because the "
        "physical symptoms can closely resemble those of a cardiac event, a first panic attack is often "
        "evaluated to rule out a cardiac cause before the diagnosis is made. Episodes generally resolve "
        "on their own within twenty to thirty minutes.",
    ),
    (
        "Costochondritis — overview",
        "Costochondritis is inflammation of the costal cartilage connecting the ribs to the sternum, "
        "producing localized chest wall pain. A key feature is reproducibility: pressing on the affected "
        "cartilage reliably reproduces the pain. The pain may worsen with movement, deep breathing, or "
        "certain positions, and is not typically accompanied by diaphoresis, nausea, or radiation to the "
        "arm. It is usually self-limited and managed with rest and simple analgesics.",
    ),
    (
        "Diabetic Ketoacidosis — overview",
        "Diabetic ketoacidosis is a life-threatening metabolic complication of diabetes, most often "
        "occurring in type 1 diabetes, in which a severe insulin deficiency leads to breakdown of fat for "
        "energy and accumulation of acidic ketones in the blood. Presentation includes excessive thirst, "
        "frequent urination, nausea, vomiting, and abdominal pain, often with a fruity odor to the breath "
        "from the ketones themselves. Rapid, deep breathing and confusion can develop as the condition "
        "progresses. Laboratory findings show markedly elevated blood glucose alongside ketones in the "
        "blood or urine. Treatment requires intravenous fluids, insulin, and correction of electrolyte "
        "abnormalities.",
    ),
    (
        "Hypoglycemia — overview",
        "Hypoglycemia is an abnormally low blood glucose level, most often occurring in people with "
        "diabetes as a side effect of insulin or certain oral medications, particularly if a dose is "
        "mismatched with food intake or activity. Early symptoms include sweating, trembling, a racing "
        "heartbeat, and anxiety, reflecting the body's adrenaline response to falling glucose. As glucose "
        "drops further, confusion and difficulty concentrating can occur. A defining feature is rapid "
        "symptom resolution within minutes of consuming glucose or a sugary food, which also serves as a "
        "practical bedside diagnostic test.",
    ),
]


async def seed():
    # Every chunk gets a fresh random ID on each run, so re-seeding without
    # clearing first just ADDS more points on top of whatever is already
    # there -- old, possibly-outdated documents keep competing against the
    # current ones forever. This collection is admin-curated reference
    # content (not user-generated data), so it's correct and safe for this
    # script to fully reset it on every run rather than accumulate.
    client = get_client()
    if await client.collection_exists(settings.qdrant_collection_medical):
        await client.delete_collection(settings.qdrant_collection_medical)

    await ensure_collections()
    for title, text in REFERENCES:
        doc_id = await index_medical_reference(title, text, source="prototype-illustrative-reference")
        print(f"Indexed '{title}' -> {doc_id}")
    print(f"Done. Indexed {len(REFERENCES)} reference documents.")


if __name__ == "__main__":
    asyncio.run(seed())