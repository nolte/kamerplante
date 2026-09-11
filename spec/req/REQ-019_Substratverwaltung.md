# Spezifikation: REQ-019 - Substratverwaltung

```yaml
ID: REQ-019
Titel: Substrat-Konfiguration und Lebenszyklusverwaltung
Kategorie: Infrastruktur
Fokus: Beides
Technologie: Python, ArangoDB
Status: Entwurf
Version: 4.1
```

## 1. Business Case

**User Story:** "Als Gärtner möchte ich Substrate und deren Chargen verwalten, um pH/EC-Verlauf, Wiederverwendbarkeit und Aufbereitungsbedarf im Blick zu behalten."

**Beschreibung:**
Das System verwaltet Substrate als wiederverwendbare Definitionen mit konkreten Chargen (Batches). Jede Charge trackt ihren Zustand über Zyklen hinweg und liefert Empfehlungen zur Wiederverwendung und Aufbereitung.

**Substrat-Typen:**
- **Erdmischungen** (Zusammensetzung, pH-Pufferung, Nährstoff-Vorrat)
- **Hydro/Inert-Medien** (Steinwolle-Slabs/-Plugs, Cocos, Blähton, Perlite, Vermiculite)
- **Living Soil** (Mikrobiom-Tracking, No-Till-Strategien, EC-Grenzwerte 0.0–1.5 mS/cm — natürlich höher als inerte Substrate durch organische Nährstofffreisetzung)
- **Substratlos** (`none` für DWC, Kratky, NFT — Nährlösung wird über REQ-014 verwaltet)

**Zimmerpflanzen-Substrate:** Orchideenrinde (`orchid_bark`), Sphagnum-Moos (`sphagnum`) und mineralische Substrate wie Pon/Seramis (`pon_mineral`) werden als eigenständige Substrattypen unterstützt. Diese verhalten sich fundamental anders als Erde — Gießhäufigkeit, pH-Bereich und EC-Toleranz unterscheiden sich massiv (z.B. Orchideen in Rinde: Tauchbad alle 7–14 Tage, komplett abtrocknen lassen; vs. Erde: gleichmäßig feucht halten).

**Kernfunktionen:**
- Batch-Tracking mit pH/EC-Verlauf über Anbauzyklen
- Wiederverwendbarkeits-Prüfung (pH-Drift, Salzakkumulation, Zyklen)
- Aufbereitungs-Anleitungen je Substrattyp (Entsalzung, Pufferung, Mikrobiom-Reaktivierung)
- Zuordnung von Chargen zu Slots (über `filled_with`-Edge)

## 2. ArangoDB-Modellierung

### Nodes:

- **`:Substrate`** - Substrat-Definition
  - Properties:
    - `type: Literal['soil', 'coco', 'rockwool_slab', 'rockwool_plug', 'clay_pebbles', 'perlite', 'vermiculite', 'living_soil', 'none', 'orchid_bark', 'pon_mineral', 'sphagnum']`
      - `none`: Substratlose Systeme (DWC, Kratky, NFT mit nackten Wurzeln) — alle physikalischen Properties nicht anwendbar
      - `orchid_bark`: Rindenmulch-Mischung für Epiphyten (Orchideen, Bromeliaden) — hohe Luftdurchlässigkeit, `air_porosity_percent` typisch 50–70%, `water_retention: low`, pH 5.5–6.5
      - `pon_mineral`: Anorganisches Mineralsubstrat (Lechuza Pon, Seramis) — strukturstabil, semi-hydroponisch, pH-neutral (6.0–7.0), speichert Nährlösung im Porenraum
      - `sphagnum`: Torfmoos für feuchtigkeitsliebende Epiphyten und Karnivoren — `water_retention: high`, pH 3.5–4.5, EC-sensitiv (< 0.5 mS/cm für Karnivoren)
      - Hinweis: Nährlösung ist kein Substrat und wird in REQ-014 (Tankmanagement) als Tank mit Typ `nutrient` verwaltet
    - `brand: Optional[str]`
    - `ph_base: float` (pH im **Wasserextrakt**, pH-H₂O)

      > **Konvention (festgelegt 2026-09-03, #1175):** `ph_base` ist der pH-Wert eines Wasserextrakts, nicht der CaCl₂-Wert. Das Extraktionsverhältnis legt der Katalog nicht fest (Plagron publiziert 1:1,5 v/v nach RHP, EN 13037 misst 1:5 v/v); es wird je Quelle im Seed-Datensatz notiert. Grund: jeder Konsument des Felds vergleicht es mit einer Messung in Wasser — die `ph_history` einer Charge (Messgerät im Drain oder in der Aufschlämmung), die volumengewichtete Mischung aus `calculate_mix_properties`, die MCP-Düngebeurteilung. Ein CaCl₂-Wert läge 0,5–1 Einheit darunter (LECHUZA-PON deklariert 8,2 H₂O gegen 7,1 CaCl₂) und würde als „saurer als dein Messgerät" gelesen. Ein Datensatz, dessen einzige Quelle CaCl₂ angibt, wird **nicht** umgerechnet — der Abstand ist substratabhängig — und bleibt offen.
    - `ec_base_ms: float` (Vorgedüngt oder inert)
    - `water_retention: Literal['low', 'medium', 'high']`
    - `water_holding_capacity_percent: Optional[float]` (volumetrische WHC, quantitativ: low <30%, medium 30–60%, high >60%)
    - `easily_available_water_percent: Optional[float]` (pflanzenverfügbares Wasser, 15–55%)
    - `air_porosity_percent: float` (bei <10% → Wiederverwendung ablehnen: Verdichtung/Erstickungsgefahr)
    - `cec_meq_per_100cm3: Optional[float]` (Kationenaustauschkapazität **pro 100 cm³ Substratvolumen** — bestimmt Nährstoffpufferung. Beeinflusst Düngfrequenz und Spülberechnung in REQ-004)

      > **Einheit (festgelegt 2026-08-15, #1152 §F):** die Werte sind **volumenbezogen**, nicht massebezogen. Der Katalog wurde so gepflegt: sieben von sieben Stichproben liegen erst nach Division durch die Schüttdichte in ihrer Literaturbandbreite (Torf 10 statt 100–200 meq/100 g; Vermiculit 15 statt 100–150; Perlit 0,1 statt ≈1,5). Das Feld hieß bis #1152 `cec_meq_per_100g`, und #1099 hatte die Mix-Engine auf dieser Namensgrundlage massegewichtet — das machte korrekte Zahlen falsch, bei einer 50/50-Mischung aus Perlit und Wurmhumus um 70 % (15,1 volumengewichtet gegen 25,7 massegewichtet).
      >
      > Die oben genannten Literaturbereiche (Steinwolle 0–2, Perlite 1–3, Blähton 2–5, Kokos 40–100, Erde 100–200, Living Soil 150–300) sind **masse**bezogen und daher nicht direkt mit den Katalogwerten vergleichbar. Sie sind hier absichtlich stehen geblieben, weil ihre Umrechnung auf die Volumenbasis noch aussteht — ein daraus geratener Plausibilitätsbereich würde nur die vorhandenen Werte bestätigen.
    - `particle_size_mm: Optional[float]` (mittlere Partikelgröße, substrattyp-abhängig)
    - `bulk_density_g_per_l: Optional[float]` (Schüttdichte, 50–1200 g/L)
    - `composition: dict[str, float]` (z.B. {"peat": 0.4, "compost": 0.3, "perlite": 0.3} — Summe muss 1.0 ergeben)
    - `buffer_capacity: Literal['low', 'medium', 'high']` (beeinflusst pH-Korrektur-Effektivität in REQ-004)
    - `reusable: bool`
    - `irrigation_strategy: Optional[Literal['infrequent', 'moderate', 'frequent', 'continuous']]` (Bewässerungs-Empfehlung: Erde→infrequent, Kokos→frequent, Blähton/Ebb&Flow→frequent, Living Soil→moderate. Wird von REQ-018 für Bewässerungsautomatik genutzt)

- **`:SubstrateBatch`** - Konkrete Substrat-Charge
  - Properties:
    - `batch_id: str`
    - `volume_liters: float`
    - `mixed_on: date`
    - `last_amended: Optional[date]`
    - `cycles_used: int`
    - `ph_current: Optional[float]`
    - `ec_current_ms: Optional[float]`
    - `temperature_c: Optional[float]` (Substrattemperatur — kritisch: <12°C Wurzelaktivität stark reduziert, >28°C Pythium-Risiko, Phosphor bei <15°C schlecht verfügbar)

### Edges (ArangoDB Edge Collections):
```
filled_with:     slots → substrate_batches              (Slot nutzt Substrat-Charge)
uses_type:       substrate_batches → substrates          (Charge basiert auf Substrat-Definition)
grown_in:        plant_instances → substrate_batches      (Pflanze wächst in Charge)
```

## 3. Technische Umsetzung (Python)

### Logik-Anforderungen:

**1. Substrat-Recycling-Tracker:**
```python
from datetime import date, timedelta
from typing import Optional
from pydantic import BaseModel, Field

class SubstrateLifecycleManager(BaseModel):
    """Tracking von Substrat-Wiederverwendung und Erschöpfung"""

    substrate_type: str
    initial_volume_liters: float
    max_reuse_cycles: int = Field(default=3)
    current_cycle: int = Field(default=0)
    ph_history: list[float] = Field(default_factory=list)
    ec_history: list[float] = Field(default_factory=list)

    def can_reuse(self) -> tuple[bool, Optional[str]]:
        """Prüft ob Substrat wiederverwendbar ist"""

        # Einweg-Substrat (nur Plugs/Anzuchtwürfel)
        if self.substrate_type in ['rockwool_plug', 'peat_plugs']:
            return False, "Einweg-Substrat (Anzucht-Plug) nicht wiederverwendbar"

        # Steinwolle-Slabs: max 3 Zyklen mit Aufbereitung (Dampfsterilisation/H₂O₂)
        # Gängige Praxis in professioneller Gewächshauskultur (Tomate, Paprika, Gurke)

        # Max Zyklen erreicht
        if self.current_cycle >= self.max_reuse_cycles:
            return False, f"Maximale Wiederverwendung ({self.max_reuse_cycles} Zyklen) erreicht"

        # pH-Stabilität-Check (Standardabweichung statt Erst-/Letztwert-Differenz)
        # Substrattyp-spezifische Grenzwerte: Living Soil toleriert mehr Schwankung
        if len(self.ph_history) >= 3:
            import statistics
            ph_stddev = statistics.stdev(self.ph_history)
            max_stddev = {
                'coco': 0.3, 'clay_pebbles': 0.3, 'perlite': 0.3,
                'rockwool_slab': 0.3, 'soil': 0.5, 'living_soil': 0.7,
            }.get(self.substrate_type, 0.5)
            if ph_stddev > max_stddev:
                return False, (
                    f"pH-Instabilität zu hoch (σ={ph_stddev:.2f}, "
                    f"max {max_stddev} für {self.substrate_type})"
                )

        # Salzakkumulation-Check (EC-Anstieg)
        if len(self.ec_history) >= 2:
            if self.substrate_type in ['coco', 'living_soil']:
                ec_increase = self.ec_history[-1] - self.ec_history[0]
                if ec_increase > 1.0:
                    return False, f"Salzakkumulation kritisch (EC +{ec_increase:.1f})"

        return True, None

    def prepare_for_reuse(self) -> dict:
        """Gibt Anweisungen zur Substrat-Aufbereitung"""

        treatments = []

        if self.substrate_type == 'coco':
            treatments.append({
                'step': 'CalMag-Pufferung',
                'action': 'Mit CalMag-Lösung (Ca:Mg 3:1–5:1, EC 1.2, pH 5.8–6.2) '
                          'durchspülen (3–5× Substratvolumen), mindestens 8h einweichen',
                'duration_hours': 24
            })

        if self.substrate_type == 'rockwool_slab':
            treatments.append({
                'step': 'Sterilisation',
                'action': 'Dampfsterilisation (70°C, 30 Minuten) oder '
                          'chemische Desinfektion (H₂O₂ 3%, 24h einweichen)',
                'duration_hours': 24
            })
            treatments.append({
                'step': 'Entsalzung',
                'action': 'Mit pH 5.5-Wasser durchspülen (2–3× Substratvolumen)',
                'duration_hours': 2
            })

        if self.substrate_type == 'clay_pebbles':
            treatments.append({
                'step': 'Reinigung',
                'action': 'Wurzelreste entfernen, in pH 5.5-Wasser mit H₂O₂ (3%) '
                          'einweichen, gründlich abspülen',
                'duration_hours': 12
            })
            treatments.append({
                'step': 'Entsalzung',
                'action': 'Mit pH-neutralem Wasser durchspülen (3× Volumen)',
                'duration_hours': 2
            })

        if self.substrate_type == 'perlite':
            treatments.append({
                'step': 'Reinigung',
                'action': 'Wurzelreste absieben, mit H₂O₂-Lösung (3%) desinfizieren, '
                          'durchspülen (3× Volumen)',
                'duration_hours': 4
            })

        if self.substrate_type in ['living_soil', 'compost_mix']:
            treatments.append({
                'step': 'Nachkompostierung',
                'action': 'Mit Wurm-Kompost und Gesteinsmehl mischen',
                'duration_days': 14
            })
            treatments.append({
                'step': 'Mikrobiom-Reaktivierung',
                'action': 'Komposttee-Gabe (500ml/10L Substrat)',
                'duration_hours': 0
            })

        # Entsalzung bei hohem EC — Spülmenge substrattyp-abhängig (CEC beeinflusst Bindung)
        if any(ec > 2.0 for ec in self.ec_history[-3:]):
            flush_volumes = {
                'rockwool_slab': '2–3', 'clay_pebbles': '3',
                'coco': '5', 'perlite': '3',
                'soil': '5–10', 'living_soil': '5–10',
            }
            vol = flush_volumes.get(self.substrate_type, '3')
            treatments.insert(0, {
                'step': 'Entsalzung',
                'action': f'Mit pH 5.5-Wasser durchspülen ({vol}× Substratvolumen)',
                'duration_hours': 2
            })

        return {
            'treatments': treatments,
            'estimated_prep_time': sum(
                t.get('duration_hours', 0) for t in treatments
            ) + sum(t.get('duration_days', 0) * 24 for t in treatments),
            'ready_date': date.today() + timedelta(
                days=max([t.get('duration_days', 0) for t in treatments] or [0])
            )
        }
```

### Datenvalidierung:
```python
from typing import Literal, Optional
from pydantic import BaseModel, Field, model_validator

SubstrateType = Literal[
    'soil', 'coco', 'peat', 'rockwool_slab', 'rockwool_plug',
    'clay_pebbles', 'perlite', 'vermiculite', 'living_soil', 'none',
    'orchid_bark', 'pon_mineral', 'sphagnum'
]
# Hinweis: 'hydro_solution' wurde entfernt — Nährlösung ist kein Substrat
# und wird in REQ-014 (Tankmanagement) als Tank verwaltet.
# 'rockwool' wurde in 'rockwool_slab' (wiederverwendbar) und
# 'rockwool_plug' (Einweg-Anzucht) differenziert.
# 'none' für substratlose Hydroponik-Systeme (DWC, Kratky, NFT).
# 'orchid_bark': Pinienrinde für Epiphyten — Tauchbad-Methode, komplett abtrocknen lassen.
# 'pon_mineral': Lechuza Pon / Seramis — mineralisch, semi-hydroponisch, Wasserstandsanzeiger.
# 'sphagnum': Torfmoos — hohe Wasserhaltung, pH 3.5–4.5, für Orchideen und Karnivoren.


class SubstrateValidator(BaseModel):
    """Validierung der Substrat-Definition."""

    substrate_type: SubstrateType
    composition: Optional[dict[str, float]] = None
    air_porosity_percent: Optional[float] = None

    @model_validator(mode='after')
    def validate_composition(self):
        """Composition-Summe muss 1.0 ergeben (±0.01 Toleranz)."""
        if self.composition:
            total = sum(self.composition.values())
            if abs(total - 1.0) > 0.01:
                raise ValueError(
                    f"Composition-Summe muss 1.0 ergeben, ist {total:.2f}"
                )
        return self

    @model_validator(mode='after')
    def validate_physical_properties_for_none(self):
        """Typ 'none' darf keine physikalischen Properties haben."""
        if self.substrate_type == 'none':
            if self.composition:
                raise ValueError("Substrattyp 'none' hat keine Composition")
        return self


# Substrattyp → Bewässerungsstrategie-Mapping (für REQ-018 Automatik)
IRRIGATION_STRATEGY_MAP = {
    'soil': 'infrequent',        # Alle 2–3 Tage, tiefes Gießen
    'coco': 'frequent',          # 2–3× täglich, Drain-to-Waste 10–30%
    'rockwool_slab': 'frequent', # 3–6× täglich, kleine Mengen
    'rockwool_plug': 'moderate', # 1–2× täglich (Anzucht)
    'clay_pebbles': 'frequent',  # Ebb&Flow 4–6× täglich
    'perlite': 'frequent',       # 3–4× täglich
    'vermiculite': 'moderate',   # 1–2× täglich
    'living_soil': 'moderate',   # Alle 2–4 Tage, nicht überwässern
    'none': 'continuous',        # DWC/NFT: kontinuierliche Nährlösung
    'orchid_bark': 'infrequent',  # Tauchbad alle 7–14 Tage, komplett abtrocknen lassen
    'pon_mineral': 'moderate',    # Wasserstandsanzeiger-basiert, Reservoir ~2cm, wöchentlich nachfüllen
    'sphagnum': 'moderate',       # Gleichmäßig feucht halten, nie ganz austrocknen, Sprühen ergänzend
}
```

## 4. Authentifizierung & Autorisierung

> **Hinweis (SEC-H-001):** Dieser Abschnitt wurde nachträglich ergänzt, um die Auth-Anforderungen
> gemäß REQ-023 (Authentifizierung) und REQ-024 (Mandantenverwaltung) zu dokumentieren.

**Standardregel:** Alle Endpunkte dieses REQ erfordern Authentifizierung (JWT Bearer Token).

> **Korrektur (#1195, 2026-08-15).** Dieser Abschnitt behauptete „Alle Substrat-Daten sind
> Tenant-scoped" — das traf **nicht zu**. Bis #1195 trugen weder `Substrate` noch
> `SubstrateBatch` ein `tenant_key`, das Repository war nicht mandantengebunden, und
> `/api/v1/substrates` hing über alle 15 Routen hinter `Depends(get_current_user)` allein:
> jeder authentifizierte Nutzer konnte die Chargen **jedes** Mandanten lesen, ändern und
> löschen sowie den geteilten Katalog verändern. Die Tabelle beschrieb einen Sollzustand in
> der Gegenwartsform — genau die Fehlerklasse, die NFR-018 §1 katalogisiert. Sie beschreibt
> jetzt den durchgesetzten Zustand, und die durchsetzende Stelle ist jeweils benannt.
>
> Die Rollenbezeichnungen sind zugleich auf das verbindliche Vokabular aus REQ-049 §3
> gebracht: „Mitglied" und unqualifiziertes „Admin" sind dort ausdrücklich **verboten**,
> weil beide mehrdeutig sind (§3.2).

**Zwei unterschiedliche Scoping-Regeln**, deren Verwechslung der naheliegende Fehler ist:

- **Substrat-Katalog — Hybrid.** Geseedete Basis-Medien (`tenant_key == ""`) plus die
  **eigenen Mischungen** eines Mandanten. Lesen nimmt die *Vereinigung* (eigene ∪ global);
  ein strikter Filter würde den geseedeten Katalog für jeden echten Mandanten leeren (#324
  in der Gegenrichtung). Dieselbe Form wie Arten und Sorten seit #1090.
- **Substrat-Chargen — strikt.** Eine Charge ist eine physische Sache, die *ein* Mandant
  angemischt hat; eine globale Charge gibt es nicht. Lesen filtert auf Gleichheit. Eine
  Zeile, die die Migration `v0043` nicht zuordnen konnte, trägt `""` und ist damit im
  `full`-Modus für niemanden sichtbar — die fail-safe Richtung, dokumentiert in §7.

| Ressource | Lesen | Anlegen/Ändern | Löschen | Durchgesetzt durch |
|---|---|---|---|---|
| Substrat-Katalog, **globale** Basis-Medien | Alle Rollen (auch ohne Mandant) | Plattform-Admin | Plattform-Admin | `require_platform_admin_for_global_catalogue` |
| Substrat-Katalog, **eigene** Mischungen | Alle Rollen des Mandanten | Ab Gärtner | Nur Leitung | `SubstrateService._authorize_write` |
| Substrat-Chargen | Alle Rollen des Mandanten | Ab Gärtner | Nur Leitung | `SubstrateService._authorize_batch_write`, fremd → `404` |
| Wiederverwendungs-Prüfung | Alle Rollen des Mandanten | — | — | Chargen-Scope oben |

Ein **fremder** Datensatz antwortet mit `404`, nie mit `403` — Eigentümer-Verschleierung, damit
die By-Key-Routen kein mandantenübergreifendes Existenz-Orakel werden. Der aktive Mandant wird
über den `X-Active-Tenant`-Mechanismus aufgelöst (REQ-049 §2.11), nicht über einen
`/t/{slug}/`-Pfad: die Routen sind global-aber-mandantenbewusst, genau die Form, für die dieser
Resolver gebaut wurde.

## 5. Abhängigkeiten

**Erforderliche Module:**
- REQ-002 (Standort): Slot-Zuordnung via `filled_with`-Edge

**Wird benötigt von:**
- REQ-003 (Phasen): Substrattyp beeinflusst Phasen-Parameter
- REQ-004 (Düngung): **HOCH** — Substrat-EC/pH für Düngeberechnung, `buffer_capacity` und `cec_meq_per_100cm3` für Spül-Berechnung (FlushingProtocol benötigt CEC für korrekte Spülzeitberechnung)
- REQ-005 (Sensorik): Substrat-Messwerte (pH, EC, Feuchtigkeit, Temperatur)
- REQ-018 (Umgebungssteuerung): **MITTEL** — `irrigation_strategy` bestimmt Bewässerungs-Automatik (Frequenz, Volumen)

## 6. Akzeptanzkriterien

### Definition of Done (DoD):

- [ ] **Substrat-CRUD:** Substrat-Definitionen anlegen, lesen, aktualisieren, löschen
- [ ] **Batch-Tracking:** Chargen mit pH/EC-Verlauf über Zyklen verfolgen
- [ ] **Wiederverwendbarkeits-Check:** Automatische Prüfung auf pH-Stabilität (Standardabweichung), Salzakkumulation und Zyklen
- [ ] **Aufbereitungs-Anleitung:** Substrattyp-spezifische Aufbereitungsschritte (inkl. Blähton, Perlite, Steinwolle-Slabs)
- [ ] **Slot-Zuordnung:** Chargen können Slots zugeordnet werden (`filled_with`-Edge)
- [ ] **Pflanzen-Zuordnung:** Pflanzen werden mit konkreten Chargen verknüpft (`grown_in` → `substrate_batches`, nicht `substrates`)
- [ ] **Substrat-Recycling:** Wiederverwendbarkeits-Check mit Aufbereitungs-Anleitung
- [ ] **Composition-Validierung:** Summenprüfung (=1.0), standardisierte Komponentennamen
- [ ] **CEC-Tracking:** Kationenaustauschkapazität pro Substrattyp für Dünge-/Spülberechnung
- [ ] **Substrattemperatur:** Tracking über SubstrateBatch, Warnung bei <12°C oder >28°C
- [ ] **Bewässerungs-Mapping:** Substrattyp → Bewässerungsstrategie für REQ-018 Automatik
<!-- Quelle: Tabellen-Analyse UI-NFR-010 §7.2, §8.1 -->
- [ ] **Listenansicht-Filter:** Substrate-Liste bietet Substrattyp-Filter (Enum-Chip: 13 Werte gemäß SubstrateType-Enum); URL-Parameter `?substrate_type=...` (UI-NFR-010 §7.2)
- [ ] **Tablet-Spaltenprioritäten:** SubstrateList blendet auf Tablet „Erstellt-am" aus; Primärspalten: Name, Typ, pH (UI-NFR-010 §8.1)

### Testszenarien:

**Szenario 1: Substrat-Recycling**
```
GIVEN: Coco-Substrat nach 2 Zyklen, EC-Historie [1.2, 1.8, 2.5]
WHEN: Nutzer prüft Wiederverwendbarkeit
THEN:
  - System erlaubt Wiederverwendung (max 3 Zyklen)
  - Aufbereitungs-Plan: 1) Entsalzung, 2) CalMag-Pufferung
  - Geschätzte Prep-Zeit: 26 Stunden
```

**Szenario 2a: Steinwolle-Plug ablehnen**
```
GIVEN: Steinwolle-Plug (rockwool_plug), 1 Zyklus verwendet
WHEN: Nutzer prüft Wiederverwendbarkeit
THEN:
  - System lehnt ab: "Einweg-Substrat (Anzucht-Plug) nicht wiederverwendbar"
```

**Szenario 2b: Steinwolle-Slab wiederverwenden**
```
GIVEN: Steinwolle-Slab (rockwool_slab), 1 Zyklus verwendet, EC ok, pH ok
WHEN: Nutzer prüft Wiederverwendbarkeit
THEN:
  - System erlaubt Wiederverwendung (max 3 Zyklen)
  - Aufbereitungs-Plan: 1) Sterilisation (Dampf 70°C oder H₂O₂ 3%), 2) Entsalzung
  - Geschätzte Prep-Zeit: 26 Stunden
```

**Szenario 3: pH-Instabilität (Standardabweichung)**
```
GIVEN: Coco-Substrat, pH-Historie [5.8, 4.5, 6.5, 5.2, 7.0] (σ=0.88)
WHEN: Nutzer prüft Wiederverwendbarkeit
THEN:
  - System lehnt ab: "pH-Instabilität zu hoch (σ=0.88, max 0.3 für coco)"
```

**Szenario 4: Living Soil Aufbereitung**
```
GIVEN: Living Soil nach 1 Zyklus, EC ok, pH ok
WHEN: Nutzer bereitet Substrat zur Wiederverwendung vor
THEN:
  - Aufbereitungs-Plan enthält:
    1) Nachkompostierung (14 Tage)
    2) Mikrobiom-Reaktivierung (Komposttee)
  - Geschätztes Fertigstellungsdatum: heute + 14 Tage
```

---

**Hinweise für RAG-Integration:**
- Keywords: Substrat, Charge, Batch, pH, EC, CEC, Kationenaustauschkapazität, WHC, Wasserhaltekapazität, Wiederverwendung, Recycling, Aufbereitung, Coco, Living Soil, Steinwolle-Slab, Steinwolle-Plug, Perlite, Blähton, Vermiculite, Substrattemperatur, Bewässerungsstrategie, Composition-Validierung, pH-Standardabweichung
- Technische Begriffe: SubstrateLifecycleManager, SubstrateValidator, pH-Stabilität, Salzakkumulation, CalMag-Pufferung, Mikrobiom-Reaktivierung, Dampfsterilisation, IRRIGATION_STRATEGY_MAP, Drain-to-Waste, Trockenlaufschutz
- Verknüpfung: Zentral für REQ-004 (Düngung — CEC, buffer_capacity), REQ-005 (Sensorik — pH, EC, Feuchte, Temperatur), REQ-018 (Umgebungssteuerung — Bewässerungs-Mapping), abhängig von REQ-002 (Standort)
