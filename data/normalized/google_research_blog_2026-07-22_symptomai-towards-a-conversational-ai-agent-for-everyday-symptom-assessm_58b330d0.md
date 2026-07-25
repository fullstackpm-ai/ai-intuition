---
id: google_research_blog_2026-07-22_symptomai-towards-a-conversational-ai-agent-for-everyday-symptom-assessm_58b330d0
lane: frontier_primitives
published_at: '2026-07-22T00:00:00+00:00'
raw_artifact_id: google_research_blog_2026-07-22_symptomai-towards-a-conversational-ai-agent-for-everyday-symptom-assessm_58b330d0
raw_path: data/raw/lab-posts/google_research_blog_2026-07-22_symptomai-towards-a-conversational-ai-agent-for-everyday-symptom-assessm_58b330d0.html
source_id: google_research_blog
source_name: Google Research Blog
source_type: html
title: 'SymptomAI: Towards a conversational AI agent for everyday symptom assessment
  General Science · Health & Bioscience · Natural Language Processing · Responsible
  AI'
url: https://research.google/blog/symptomai-towards-a-conversational-ai-agent-for-everyday-symptom-assessment/
---

# SymptomAI: Towards a conversational AI agent for everyday symptom assessment

SymptomAI: Towards a conversational AI agent for everyday symptom assessment

July 22, 2026

Joseph Breda, Student Researcher, and Jake Sunshine, Research Scientist, Google Research

We present a first-of-its-kind research of AI for differential diagnosis and symptom checking through a national-scale study.

Quick links

Paper

Share Copy link ×

Copy link ×

A large proportion of clinical diagnoses can be derived from language-based interviews alone. These diagnostic interviews are typically conducted by clinicians through doctor-patient interactions during in-person or remote visits. While these interactions are the gold standard for symptom assessment, they can often suffer from financial , geographic , and systemic barriers that limit their accessibility. Current language models (LMs) have demonstrated strong differential diagnosis assessment capabilities when evaluated on curated medical case-studies, highlighting their potential to support the diagnostic process. However, existing evaluations have largely relied on curated, highly detailed and sometimes synthetic patient vignettes, which may not reflect real world experience and clinical presentation variability. These evaluations do not capture how everyday patients report their health symptoms, for example with varying levels of medical literacy, incomplete information, and other complexities that arise through natural conversation. This represents a key gap, leading to uncertainty of how LMs might perform in real-world contexts.

To address this gap, we conduct an in-situ comparative research study of a set of experimental conversational prototype AI agents designed to explore how conversational AI might conduct end-to-end symptom interviews and differential diagnostic assessment for research benchmarking purposes. In our recent research paper, “ SymptomAI: Towards a Conversational AI Agent for Everyday Symptom Assessment ”, we share results from a randomized national scale study (n=13,917) in which consented research participants interact with one of five possible Gemini Flash 2.0 SymptomAI agents. All diagnoses, labels, and disease associations generated during the study were for research analysis only and did not constitute confirmed clinical diagnoses or official medical assessments. Two weeks after their interaction with the AI agents, we asked research participants to report any diagnoses they received from a visit with a healthcare provider. Using this data, we conducted a clinical expert annotation study comparing SymptomAI’s diagnostic performance relative to real clinicians' medical assessments.

After assessing the accuracy of SymptomAI’s differential diagnoses (DDx), we further compare SymptomAI’s diagnoses against biosignals from participants’ Fitbit wearable devices in the time leading up to their conversation with SymptomAI. We show that SymptomAI conversations that led to diagnosis with an infectious disease etiology coincide with physiological trends that may indicate an immune response, suggesting further evidence of SymptomAI’s performance.

For this research, we administered a set of conversational AI agents for end-to-end patient interviewing and differential diagnostic assessment. A participant could converse with an agent about their symptoms, receive a candidate differential list and enter a subsequent diagnosis.

How it works

We enrolled 13,917 consenting research study participants who each describe their symptoms to one of five randomized SymptomAI agents, each with varying degrees of flexibility in how they conducted the symptom interview. During these conversations, participants described their symptoms and SymptomAI asked follow-up questions, with conversations culminating in a final differential diagnosis (DDx, a list of plausible diagnoses) and recommendations for next steps. Participants could then go on to see a healthcare provider and were asked to share the outcome of that visit via a survey two-weeks later. To evaluate and baseline SymptomAI’s assessment, we conducted a clinical-expert annotation study in which a panel of three board-certified clinicians reviewed the conversation transcripts and provided their own assessment (i.e., differential diagnosis). Then each clinician, in a blinded fashion , ranked the DDx provided by SymptomAI and those provided by the remaining clinicians.

Key results

Clinical experts preference for SymptomAI DDx

We found that the clinicians preferred the DDx generated by SymptomAI over those provided by the other clinicians in over 50% of the cases. This indicates that SymptomAI DDx aligned with our clinicians’ medical assessments just as often or more often than that of other clinicians.

The SymptomAI generated DDx were more likely to be ranked as the best DDx in overall quality by our clinical raters.

Clinical experts found SymptomAI DDx to be more accurate

Similarly, we compare the accuracy of the DDx generated by SymptomAI and provided by real clinicians via top-5 Accuracy (i.e., whether the true diagnosis provided by our participants' personal healthcare provider appears as one of the five possible diagnoses in the DDx). We had our clinicians each identify whether the provided diagnosis was in each DDx, including both the DDx generated by SymptomAI and those provided by clinicians. We found that the clinicians ranked the DDx generated by SymptomAI to be accurate more often than the DDx provided by other clinicians.

The SymptomAI generated DDx were more likely to contain the self-reported diagnosis provided by a healthcare provider.

Eliciting more information improves performance

As part of this research, we assessed different approaches for conducting history taking interviews. Participants were randomly assigned to five study arms, each employing different prompting strategies. Two ( Dynamic Live and Dynamic Final ) were given total agency to ask unrestricted follow up questions, two more ( Fixed Canonical and Flexible Canonical ) each asked questions from a set of standard history taking questions taught in medical school, and finally a Base unprompted LM, representing the fully user-driven experience that is the current status quo when querying LM chatbots. We found that all agent-driven prompting strategies (i.e., where SymptomAI actively asked follow up questions) significantly outperformed the Base condition, demonstrating the value of eliciting information from participants for improving differential diagnostic accuracy.

Accuracy of Symptom AI and clinicians by SymptomAI experiment arm.

Total user word count by SymptomAI experiment arm.

SymptomAI performance on low-confidence examples

We found that SymptomAI’s performance above clinical baselines was greatest for cases where the clinician’s felt least confident in their own DDx.

The top-5 accuracy assigned by clinicians to SymptomAI and baseline clinician-generated DDx stratified by the baseline clinician’s confidence in their own DDx.

Diagnosis from SymptomAI correlates with biosignals

Given SymptomAI's accuracy against clinical baselines, we can also explore its potential at scale. Currently, the cost of clinical labels prohibits real-world analyses of population-scale datasets. Accurate symptom checking systems like SymptomAI have the potential to enable automated reference labeling of clinical quality diagnosis, which can open up large-scale analyses of physiological data — a task that is currently impossible at scale.

One such example is correlating wearable biosignals with different categories of illness. The most notable changes in wearable biosignals are observed for acute respiratory infections. To study this at population scale, we collected daily biometric data from our consenting participants for up to 30 days prior to their interaction with SymptomAI. We find clear biosignal shifts indicating symptom onset in the days approaching the user's symptom reporting. Importantly, the separation between cohorts was derived through categorizing SymptomAI's top-1 candidate diagnosis and grouping diagnoses that were classified as respiratory infections. This cohort excludes non-infectious respiratory illnesses like allergic rhinitis or chronic obstructive pulmonary disease . The correlation of wearable biosignals shift peaks aligning with the date of symptom reporting for these participants serves as observational physiological evidence that align with their reported symptoms.

Wearable biosignals in the days leading up to a SymptomAI conversation relative to a historic average from a baseline period across day -30 to -15 for the infected ( red ) and baseline ( gray ) cohorts. The infected cohort includes participants which SymptomAI diagnosed with a respiratory infection while the baseline includes all other participants in our dataset. Day 0 denotes the date of the SymptomAI conversation.

Utility alongside biosignals

AI-based assessment of symptom presentations opens the door to new research. By using SymptomAI to analyze a large volume of symptom reports and pairing those with real-time Fitbit data, we can explore digital biosignal phenotypes across a wide range of diseases. Our analysis revealed distinct shifts in physiological metrics — including cardiovascular function, respiration, skin temperature, and sleep quality — in the days leading up to a user's SymptomAI conversation. These objective changes align closely with the timing of the symptom conversation, offering a potential way to validate patient-reported symptoms or provide passive data to help inform a differential diagnosis alongside their symptom conversation. Additionally, this real-time accessibility highlights a core benefit of AI symptom checkers. Unlike traditional clinical appointments that can suffer from scheduling delays, participants could take part on the SymptomAI research study contemporaneously while symptoms are fresh. This potentially could improve the accuracy of patient-reported onset timelines — a crucial detail for population-scale health analysis.

Limitations

SymptomAI is an exploratory research effort that could represent a significant research advancement in AI-based symptom assessment and demonstrates the potential it could provide for the general public seeking understanding of their symptoms. While a population deployment evaluation reveals the accuracy of symptom assessment through remote patient interviews, there are nuanced limitations when comparing against clinician’s assessments.

Firstly, differential diagnosis itself is an ambiguous task and even reported diagnoses may change and develop longitudinally. A symptom assessment is a snapshot in time and captures the symptoms as they present in that moment. Due to the scale of our deployment, we were unable to control for frequency and timing of symptom reporting. As a result, some participants may have reported their symptoms well before more representative indicators developed, while others may have reported obvious indicators from an informed context after years of experience with chronic illness. Future work may focus on specific illnesses at specific points during symptom development such as early-onset metabolic syndrome or symptoms discussed at the start of respiratory infections. All diagnoses, labels, and disease associations generated during the study are AI-derived for research analysis only and do not constitute confirmed clinical diagnoses or official medical assessments.

Secondly, in our evaluation the clinicians reviewed static chat transcripts and were not given agency to ask their own follow-up questions. Clinicians may have intuitively sourced different information had they directed the symptom interview. Moreover, while recent research has shown that conversational AI systems can source clinical data with a clinician-level of detail and accuracy, such systems may miss alternative signals like body language, visual assessment, medical records, or in the context of primary care, existing rapport with the patient.

In conclusion, we introduce SymptomAI, an investigational conversational AI agent for conducting real-world patient interviews and symptom assessments. We demonstrate SymptomAI’s end-to-end real-world performance through DDx accuracy on a population sample, and show how SymptomAI diagnoses can enable analysis of population-scale signals like wearable biosignals for identifying associations in physiological signals with reported illness.

Acknowledgements

This work is the result of equal contributions from Joe Breda, Jake Sunshine and Daniel McDuff. We would like to thank our co-authors and collaborators from Google Research and Google DeepMind for their contributions to this work.

Labels:

General Science

Health & Bioscience

Natural Language Processing

Responsible AI

Quick links

Paper

Share Copy link ×

Copy link ×

Other posts of interest

June 26, 2026 Accelerating Gemini Nano models on Pixel with frozen Multi-Token Prediction Machine Intelligence · Mobile Systems · Natural Language Processing

June 26, 2026

Machine Intelligence ·

Mobile Systems ·

Natural Language Processing

June 24, 2026 Thinking to recall: How reasoning unlocks parametric knowledge in LLMs Generative AI · Machine Intelligence · Natural Language Processing

June 24, 2026

Generative AI ·

Machine Intelligence ·

Natural Language Processing

June 12, 2026 Research into how AI can help users understand skin conditions Health & Bioscience · Human-Computer Interaction and Visualization

June 12, 2026

Health & Bioscience ·

Human-Computer Interaction and Visualization