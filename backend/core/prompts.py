"""Revna — Expert contexts, prompt rules, and hallucination detection.

Ported ~1:1 from coach/prompts.py. Expert knowledge blocks are domain-generic
and reusable across all coaching types. The prompt building functions that
reference specific user/health data live in services/ai.py and services/notifications.py.
"""

import re

# ─── Expert Knowledge Blocks ─────────────────────────────────────────────────

WELLNESS_SUGGESTIONS = """SUGGESTIONS BIEN-ETRE HOLISTIQUES (adapte selon contexte):

NUTRITION:
- Proteines: 1.5-2g/kg/jour pour la recuperation (poulet, poisson, oeufs, legumineuses)
- Vitamine C: agrumes, kiwi, poivron (synthese du collagene)
- Omega-3: poissons gras, noix, graines de lin (anti-inflammatoire naturel)
- Calcium + Vitamine D: produits laitiers, soleil 15min/jour
- Hydratation: 2L/jour minimum, +500ml si activite physique
- Anti-inflammatoires naturels: curcuma, gingembre, cerises

ACTIVITES BIEN-ETRE (selon BB et heure):
- BB > 60%: marche rapide 30min, velo d'appartement, natation
- BB 30-60%: marche calme 20min, yoga doux, etirements
- BB < 30%: respiration, meditation, bain chaud, lecture
- Matin: activite physique (cortisol naturellement eleve)
- Apres-midi: pause active, marche digestive
- Soir: activites calmes, pas d'ecran 1h avant coucher

HYGIENE DU SOMMEIL:
- Temperature chambre: 18-19C
- Derniere exposition lumiere bleue: 1h avant coucher
- Routine pre-sommeil: douche tiede + lecture/meditation
- Pas de cafe apres 14h, pas d'alcool
- Horaires reguliers (+/- 30min)
- Si insomnie: technique 4-7-8 (inspire 4s, retiens 7s, expire 8s)

QUAND SUGGERER QUOI (DATA-DRIVEN):
- Sommeil < 50 OU fragmentation > 20%: rappeler hygiene du sommeil le soir
- Deep sleep < 60min: routine pre-sommeil
- BB basse matin OU recharge nocturne < +20: suggerer aliments energetiques
- Stress eleve OU pics stress > 50 recurrents: tisane, marche en nature
- Stress concentre le soir (>40 apres 18h): routine de decompression
- BB drain rapide en apres-midi (>15/h): pause active a 15h, collation proteines
- VFC en baisse > 10%: signe de surcharge, priorite repos + sommeil
- Derniere activite > 5 jours: encourager reprise douce, marche 20min
- Hydratation: rappel toutes les 3h"""

PSY_TECHNIQUES = """MICRO-INTERVENTIONS PSYCHOLOGIQUES (choisis UNE technique adaptee au contexte):

ACT (Therapie d'Acceptation et d'Engagement):
- Defusion cognitive: "Cette pensee est juste une pensee, pas une realite"
  -> Quand: pensees negatives, catastrophisme
- Acceptation: accueillir la douleur sans lutter ("la resistance amplifie la souffrance")
  -> Quand: douleur persistante, frustration face aux limites
- Valeurs: "Pourquoi tu fais ca? Pour quoi/qui?"
  -> Quand: perte de motivation, plateau, decouragement
- Action engagee: un petit pas concret vers ses valeurs malgre la douleur
  -> Quand: evitement, procrastination

MINDFULNESS (adapte au moment de la journee):
- Matin: scan corporel 3min
- Midi: respiration ancrage 2min (inspire 4s, retiens 2s, expire 6s, 5 cycles)
- Soir: gratitude 3 choses
- Urgence stress: technique 5-4-3-2-1

AUTO-COMPASSION (Kristin Neff - MSC):
- Main sur le coeur + phrase: "C'est un moment difficile. Puis-je etre bienveillant envers moi-meme?"
- Normalisation: "D'autres personnes vivent exactement ca"

MATRICE CONTEXTUELLE (quel signal -> quelle technique):
- Stress eleve -> defusion + respiration ancrage
- BB basse -> scan corporel + acceptation
- Plateau readiness 7j+ -> valeurs + auto-compassion
- Objectif atteint -> celebration chaleureuse
- Douleur augmentee -> acceptation + main sur le coeur
- Mauvais sommeil -> gratitude soir + technique 4-7-8"""

HEALTH_DATA_INTERPRETATION = """INTERPRETATION DES DONNEES DETAILLEES (OBLIGATOIRE):

Tu disposes de donnees detaillees. Utilise-les pour des analyses PRECISES, pas des generalites.

SOMMEIL DETAILLE:
- Deep sleep < 60min = recuperation physique insuffisante
  -> Reduire l'intensite, privilegier mobilite
- Deep sleep > 90min = excellente recuperation physique
- REM < 45min = recuperation cognitive/emotionnelle insuffisante
  -> Le patient sera plus sensible emotionnellement, adapter le ton
- Fragmentation > 15% = sommeil de mauvaise qualite MEME si le score semble correct
- Fragmentation > 25% = sommeil tres perturbe
- Recharge BB nocturne < +20 = le corps n'a pas recupere pendant la nuit
- Stress nocturne moyen > 30 = systeme nerveux sympathique actif la nuit (alerte)

PATTERNS STRESS & ENERGIE:
- Stress matin > 50 + soir < 30 = profil normal (activation matinale)
- Stress soir > 40 = mauvaise decompression, impact sur le sommeil a venir
- Stress constant > 40 toute la journee = charge allostatique elevee
- BB qui drain > 15 en 1h = episode de forte depense
- Courbe BB descendante toute la journee (sans remontee) = signal d'alarme

TENDANCE VFC (7 nuits):
- VFC en hausse > 5% = recuperation amelioree -> maintenir ou progresser
- VFC stable (±5%) = equilibre correct -> maintenir le programme
- VFC en baisse 5-10% = debut de fatigue accumulee -> reduire legerement
- VFC en baisse > 10% = surcharge -> reduire significativement

DETECTION MULTI-SIGNAUX (PRIORITAIRE — croise les donnees):

ALERTE ROUGE (reduire drastiquement ou repos):
- Sommeil < 40 + BB < 25 + VFC en baisse = fatigue systemique
- Fragmentation > 20% + stress nocturne > 30 + recharge BB < +15 = nuit non-recuperatrice
- 3+ jours consecutifs BB < 40 = epuisement chronique

ALERTE ORANGE (reduire moderement):
- Sommeil 40-60 + fragmentation > 15% = qualite de sommeil trompeuse
- BB ok (> 50) mais VFC en baisse > 10% = fatigue masquee
- Stress moyen > 45 + deep sleep < 60min = cercle vicieux stress-sommeil

SIGNAL POSITIF (maintenir ou progresser):
- Sommeil > 70 + fragmentation < 10% + VFC stable ou en hausse = conditions optimales
- BB > 60 + recharge nocturne > +30 + stress nocturne < 20 = excellente recuperation
- Deep sleep > 90min + REM > 60min = nuit de haute qualite"""

SAFETY_DECISION_TREE = """ARBRE DE DECISION SECURITE (OBLIGATOIRE — verifie AVANT toute recommandation):

NIVEAU 1 — STOP IMMEDIAT (recommander consultation medicale):
- SpO2 < 85% → "Cette valeur necessite un avis medical."
- FC repos > 100 bpm persistant → "FC repos anormalement elevee. Consulte si ca persiste."

NIVEAU 2 — ALERTE (adapter + surveiller):
- SpO2 85-90% → Mentionner objectivement, recommander de surveiller
- 5+ nuits consecutives score < 50 → Suspecter cause sous-jacente
- VFC en chute > 20% sur 7 nuits → Possible surcharge ou infection, repos strict
- BB < 10% le matin → Corps epuise, repos actif uniquement

NIVEAU 3 — VIGILANCE (mentionner sans alarmer):
- SpO2 90-93% → Normal en altitude, a surveiller en plaine
- Stress nocturne > 40 repete 3+ nuits → Proposer routine pre-sommeil
- Fragmentation > 25% → Qualite de sommeil impactee

REGLE: En cas de doute sur la gravite, TOUJOURS orienter vers un professionnel de sante.
Ne JAMAIS diagnostiquer. Ne JAMAIS minimiser un signal de niveau 1."""

# ─── Prompt rules & hallucination detection ──────────────────────────────────

PROMPT_RULES = """REGLES ABSOLUES (s'appliquent a TOUTES tes reponses):
- INTERDIT de dire "donnees indisponibles", "pas de donnees", "donnees manquantes"
- TOUTES les donnees de sante sont fournies ci-dessus — utilise les CHIFFRES EXACTS
- Si une donnee specifique n'apparait pas, ne la mentionne pas — ne dis PAS qu'elle est absente
- Reponds en francais
- Format: HTML Telegram (<b>, <i>, pas de markdown, pas de ```)
- Ton chaleureux, bienveillant, personnalise — jamais clinique ou froid"""

HALLUCINATION_PATTERNS = [
    r"donn[ée]es?\s+(in)?disponibles?",
    r"pas\s+de\s+donn[ée]es?",
    r"donn[ée]es?\s+manquantes?",
    r"donn[ée]es?\s+(non\s+)?(re[çc]ues?|trouv[ée]es?)",
    r"donn[ée]es?\s+inconnues?",
    r"aucune\s+donn[ée]e",
    r"je\s+n.?ai\s+pas\s+(acc[eè]s|re[çc]u)",
    r"impossible\s+d.?acc[ée]der",
    r"donn[ée]es?\s+absentes?",
    r"pas\s+(?:encore\s+)?(?:de\s+)?(?:sync|synchronis)",
    r"capteurs?\s+(?:sont\s+)?(?:in)?disponibles?",
    r"en\s+attente\s+de\s+(?:donn[ée]es?|sync)",
]
_HALLUCINATION_RE = re.compile("|".join(HALLUCINATION_PATTERNS), re.IGNORECASE)

ANTI_HALLUCINATION_SUFFIX = (
    "\n\nATTENTION: Ta reponse precedente contenait '{pattern}' — "
    "c'est INTERDIT. TOUTES les donnees sont dans le prompt ci-dessus. "
    "Utilise les CHIFFRES EXACTS. Ne dis JAMAIS que les donnees sont "
    "indisponibles ou manquantes."
)


def validate_ai_message(message: str) -> tuple[bool, str | None]:
    """Check if an AI-generated message contains hallucination patterns.

    Returns (is_valid, matched_pattern). is_valid=True means the message is OK.
    """
    if not message:
        return False, "empty"
    match = _HALLUCINATION_RE.search(message)
    if match:
        return False, match.group()
    return True, None


def strip_hallucination_sentences(text: str) -> str:
    """Remove sentences containing hallucination patterns from AI text."""
    lines = text.split("\n")
    clean = [line for line in lines if not _HALLUCINATION_RE.search(line)]
    return "\n".join(clean)
