"""
SM-2 Spaced Repetition Algorithmus
Basierend auf Piotr Wozniaks SuperMemo 2, vereinfacht.
"""
from datetime import date, timedelta


def sm2(card, rating):
    """
    Berechnet neue SRS-Werte basierend auf der Bewertung.
    
    Args:
        card: dict mit Feldern ease_factor, interval_days, repetitions,
              next_review, last_reviewed, review_count, avg_rating
        rating: int 0-5
            0 = komplett vergessen
            1-2 = unsicher
            3 = okay
            4 = gut
            5 = perfekt erinnert
    
    Returns:
        dict mit aktualisierten SRS-Feldern (neue Instanz, original unverändert)
    """
    card = dict(card)  # copy
    
    if rating >= 3:
        # Erfolgreich: Intervall vergrößern
        if card['repetitions'] == 0:
            card['interval_days'] = 1
        elif card['repetitions'] == 1:
            card['interval_days'] = 3
        else:
            card['interval_days'] = round(card['interval_days'] * card['ease_factor'])
        card['repetitions'] += 1
    else:
        # Vergessen: Reset
        card['repetitions'] = 0
        card['interval_days'] = 1
    
    # Ease-Faktor anpassen (SM-2 Formel)
    q = rating  # quality
    card['ease_factor'] = card['ease_factor'] + (0.1 - (5 - q) * (0.08 + (5 - q) * 0.02))
    card['ease_factor'] = max(1.3, card['ease_factor'])  # Minimum 1.3
    
    # Nächsten Review berechnen
    today = date.today()
    card['next_review'] = (today + timedelta(days=card['interval_days'])).isoformat()
    card['last_reviewed'] = today.isoformat()
    card['review_count'] = card['review_count'] + 1
    
    # Gleitenden Durchschnitt der Bewertungen aktualisieren
    if card['review_count'] == 1:
        card['avg_rating'] = rating
    else:
        card['avg_rating'] = round(
            (card['avg_rating'] * (card['review_count'] - 1) + rating) / card['review_count'], 2
        )
    
    return card


# ── Unit Tests (ausführbar mit: python srs.py) ──────────────────

if __name__ == '__main__':
    # Initiale Karte
    card = {
        'ease_factor': 2.5,
        'interval_days': 0,
        'repetitions': 0,
        'next_review': None,
        'last_reviewed': None,
        'review_count': 0,
        'avg_rating': 0
    }
    
    # Test 1: Erstes Review, perfekt (5)
    c = sm2(card, 5)
    assert c['repetitions'] == 1, f"Expected 1, got {c['repetitions']}"
    assert c['interval_days'] == 1, f"Expected 1, got {c['interval_days']}"
    assert c['review_count'] == 1
    assert c['avg_rating'] == 5
    print("✓ Test 1 passed: Erstes Review (5) → reps=1, interval=1")
    
    # Test 2: Zweites Review, gut (4)
    c = sm2(c, 4)
    assert c['repetitions'] == 2, f"Expected 2, got {c['repetitions']}"
    assert c['interval_days'] == 3, f"Expected 3, got {c['interval_days']}"
    assert c['review_count'] == 2
    print("✓ Test 2 passed: Zweites Review (4) → reps=2, interval=3")
    
    # Test 3: Drittes Review, okay (3)
    c = sm2(c, 3)
    assert c['repetitions'] == 3, f"Expected 3, got {c['repetitions']}"
    assert c['interval_days'] >= 7, f"Expected >=7, got {c['interval_days']}"
    print(f"✓ Test 3 passed: Drittes Review (3) → reps=3, interval={c['interval_days']}")
    
    # Test 4: Vergessen (0) → Reset
    c = sm2(c, 0)
    assert c['repetitions'] == 0, f"Expected 0, got {c['repetitions']}"
    assert c['interval_days'] == 1, f"Expected 1, got {c['interval_days']}"
    print("✓ Test 4 passed: Vergessen (0) → reps=0, interval=1 (Reset)")
    
    # Test 5: Ease-Faktor sinkt nicht unter 1.3
    c['ease_factor'] = 1.3
    c = sm2(c, 1)
    assert c['ease_factor'] >= 1.3, f"Ease factor too low: {c['ease_factor']}"
    print(f"✓ Test 5 passed: Ease-Faktor Minimum (1.3) eingehalten → {c['ease_factor']:.2f}")
    
    print("\n✅ Alle SM-2 Tests bestanden!")
