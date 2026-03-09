"""Revna — Static data: sport icons, French days, adaptation levels."""

FRENCH_DAYS = {
    0: "Lundi", 1: "Mardi", 2: "Mercredi", 3: "Jeudi",
    4: "Vendredi", 5: "Samedi", 6: "Dimanche",
}
FRENCH_DAYS_SHORT = {
    0: "Lun", 1: "Mar", 2: "Mer", 3: "Jeu",
    4: "Ven", 5: "Sam", 6: "Dim",
}

SPORT_ICONS = {
    "strength": "mdi:dumbbell", "bike": "mdi:bike", "run": "mdi:run",
    "swim": "mdi:swim", "brick": "mdi:lightning-bolt", "rest": "mdi:sleep",
}

REST_DAY_MOBILITY = {
    "sport": "strength", "type": "recovery",
    "name": "Mobilité douce (adaptation repos)",
    "description": "Séance allégée automatiquement.",
    "duration_minutes": 10, "primary_zone": "Zone 0",
    "human_readable": (
        "Mobilité douce: 5min mouvements articulaires lents "
        "(cou, épaules, hanches)\n"
        "Respiration diaphragmatique: 3min\n"
        "Étirements légers: 2min"
    ),
    "completed": False, "exercise_count": 3,
}

# ─── Notification types & limits ─────────────────────────────────────────────

NOTIFICATION_TYPES = {
    "morning_report":      {"max_tokens": 800, "temperature": 0.4, "label": "Rapport matinal"},
    "poor_sleep":          {"max_tokens": 400, "temperature": 0.3, "label": "Alerte sommeil"},
    "sedentary":           {"max_tokens": 300, "temperature": 0.5, "label": "Pause active"},
    "steps_evening":       {"max_tokens": 400, "temperature": 0.4, "label": "Bilan pas"},
    "high_stress":         {"max_tokens": 400, "temperature": 0.3, "label": "Stress élevé"},
    "low_body_battery":    {"max_tokens": 400, "temperature": 0.3, "label": "Énergie basse"},
    "weekly_summary":      {"max_tokens": 500, "temperature": 0.4, "label": "Bilan hebdo"},
    "low_spo2":            {"max_tokens": 250, "temperature": 0.2, "label": "SpO2 basse"},
    "steps_goal_reached":  {"max_tokens": 200, "temperature": 0.6, "label": "Objectif pas"},
    "monday_activity":     {"max_tokens": 250, "temperature": 0.5, "label": "Rappel activité"},
    "evening_report":      {"max_tokens": 1200, "temperature": 0.4, "label": "Bilan du soir"},
    "chronic_fatigue":     {"max_tokens": 500, "temperature": 0.3, "label": "Fatigue chronique"},
    "recovery_protocol":   {"max_tokens": 400, "temperature": 0.3, "label": "Protocole récup"},
    "readiness_prediction": {"max_tokens": 400, "temperature": 0.4, "label": "Prédiction J+1"},
}

NOTIFICATION_COOLDOWNS = {
    "morning_report": 6 * 3600,
    "poor_sleep": 12 * 3600,
    "sedentary": 2 * 3600,
    "steps_evening": 18 * 3600,
    "high_stress": 3 * 3600,
    "low_body_battery": 4 * 3600,
    "weekly_summary": 6 * 86400,
    "low_spo2": 12 * 3600,
    "steps_goal_reached": 18 * 3600,
    "monday_activity": 6 * 86400,
    "evening_report": 18 * 3600,
    "checkin_morning": 10 * 3600,
    "checkin_evening": 10 * 3600,
    "ai_adapt_notif": 6 * 3600,
    "chronic_fatigue": 24 * 3600,
    "recovery_protocol": 12 * 3600,
    "readiness_prediction": 18 * 3600,
    "health_monitor": 3 * 3600,
    "spontaneous_response": 30,
}

NOTIFICATION_CONFLICT_GROUPS = {
    "sedentary":          ["steps_goal_reached", "recovery_protocol"],
    "low_body_battery":   ["steps_goal_reached"],
    "high_stress":        ["sedentary"],
    "recovery_protocol":  ["chronic_fatigue"],
    "chronic_fatigue":    ["recovery_protocol"],
    "poor_sleep":         ["morning_report"],
    "steps_goal_reached": ["sedentary"],
}

ESSENTIAL_NOTIFICATIONS = {
    "morning_report", "evening_report", "weekly_summary",
    "low_spo2", "chronic_fatigue", "steps_goal_reached",
}

CONVERSATION_MAX_PER_HOUR = 10
CONVERSATION_HISTORY_HOURS = 48

SILENT_DAY_READINESS_THRESHOLD = 80

MEDICAL_DISCLAIMER = "\n\n<i>⚕️ Info bien-être, ne remplace pas un avis médical.</i>"
