# Context Packet: thermodynamics

## Allowed Sources

- `wiki/thermodynamics.md`
- `wiki/.understand-anything/knowledge-graph.json`

## Usage Rules

- Use only the material contained in this packet.
- Do not add outside factual knowledge.
- Mark unsupported claims as `SOURCE GAP`.
- Every factual section must include a source reference.

## Source Article

# Thermodynamics

## Key Concepts

**Energy Forms:**
- **Kinetic energy** — movement of molecules
- **Potential energy** — energy stored in chemical bonds
  - Most important potential energy storage molecule: **ATP** (energy in ester bonds between phosphate groups)

## Laws of Thermodynamics

**First Law (Conservation of Energy):**
- Energy of the universe is constant
- When system energy decreases, surroundings energy increases, and vice versa

**Second Law (Entropy):**
- Disorder (entropy, S) of the universe tends to increase
- Spontaneous reactions increase universal disorder
- ∆S = S<sub>final</sub> – S<sub>initial</sub>
- If ∆S is negative → disorder decreased

## Gibbs Free Energy (∆G)

**Equation:** ∆G = ∆H – T∆S

Where:
- ∆H = enthalpy change (bond energy + P∆V)
- T = temperature (Kelvin)
- ∆S = entropy change

**In cells:** Since ∆V ≈ 0 (liquid phase), **∆H ≈ ∆E** (bond energy)

**Spontaneity:**
- ∆G < 0 → spontaneous (exergonic, energy exits system)
- ∆G > 0 → nonspontaneous (endergonic, requires energy input)
- ∆G = 0 → equilibrium

**Enthalpy:**
- ∆H < 0 → exothermic (liberates heat)
- ∆H > 0 → endothermic (requires heat input)
- Most metabolic reactions are exothermic → maintains body temperature

**Sign convention:** All from system's perspective (negative ∆G = system goes to lower free energy)

## Standard Free Energy

**∆G°′** — biochemical standard: 1 M all solutes except H<sup>+</sup>, pH 7

**Relationship to equilibrium:**
- ∆G°′ = –RT ln K'<sub>eq</sub>
- K'<sub>eq</sub> = [C]<sup>c</sup>[D]<sup>d</sup> / [A]<sup>a</sup>[B]<sup>b</sup> at equilibrium

**When K'<sub>eq</sub> = 1:** ∆G°′ = 0 (ln 1 = 0)

## Reaction Quotient (Q) vs. Actual ∆G

**Equation:** ∆G = ∆G°′ + RT ln Q

Where Q uses **actual cellular concentrations**, not equilibrium concentrations.

**Key relationships:**
- Q < K<sub>eq</sub> → ∆G < 0 → forward reaction spontaneous
- Q > K<sub>eq</sub> → ∆G > 0 → reverse reaction spontaneous
- Q = K<sub>eq</sub> → ∆G = 0 → equilibrium

**Two factors determine spontaneity in cell:**
1. Intrinsic properties (K<sub>eq</sub>)
2. Concentrations (RT ln Q)

**Le Châtelier's principle:** Adding reactants (Q < K) drives forward; adding products (Q > K) drives backward

## Key Questions Answered

| Question | Answer |
|----------|--------|
| Can ∆G be negative if ∆G°′ is positive? | Yes, if RT ln Q is sufficiently negative |
| Does K<sub>eq</sub> indicate reaction rate? | No — only relative concentrations at equilibrium |
| Large K<sub>eq</sub> → lower free energy? | Products |
| Large Q → lower free energy? | Can't tell from Q alone |
| ∆G = 0 → favored direction? | Neither (at equilibrium) |
| Radiolabeled B added at equilibrium → where found? | Both A and B (dynamic equilibrium) |

---

*See also: [[kinetics]], [[oxidation-reduction]], [[acids-bases]]*

## Extracted Headings

- # Thermodynamics
- ## Key Concepts
- ## Laws of Thermodynamics
- ## Gibbs Free Energy (∆G)
- ## Standard Free Energy
- ## Reaction Quotient (Q) vs. Actual ∆G
- ## Key Questions Answered

## Candidate Equation Lines

- - ∆S = S<sub>final</sub> – S<sub>initial</sub>
- **Equation:** ∆G = ∆H – T∆S
- - ∆H = enthalpy change (bond energy + P∆V)
- - T = temperature (Kelvin)
- - ∆S = entropy change
- - ∆G = 0 → equilibrium
- **Sign convention:** All from system's perspective (negative ∆G = system goes to lower free energy)
- **∆G°′** — biochemical standard: 1 M all solutes except H<sup>+</sup>, pH 7
- - ∆G°′ = –RT ln K'<sub>eq</sub>
- - K'<sub>eq</sub> = [C]<sup>c</sup>[D]<sup>d</sup> / [A]<sup>a</sup>[B]<sup>b</sup> at equilibrium
- **When K'<sub>eq</sub> = 1:** ∆G°′ = 0 (ln 1 = 0)
- ## Reaction Quotient (Q) vs. Actual ∆G
- **Equation:** ∆G = ∆G°′ + RT ln Q
- Where Q uses **actual cellular concentrations**, not equilibrium concentrations.
- - Q < K<sub>eq</sub> → ∆G < 0 → forward reaction spontaneous
- - Q > K<sub>eq</sub> → ∆G > 0 → reverse reaction spontaneous
- - Q = K<sub>eq</sub> → ∆G = 0 → equilibrium
- 2. Concentrations (RT ln Q)
- **Le Châtelier's principle:** Adding reactants (Q < K) drives forward; adding products (Q > K) drives backward
- ## Key Questions Answered
- | Question | Answer |
- | Can ∆G be negative if ∆G°′ is positive? | Yes, if RT ln Q is sufficiently negative |
- | Large Q → lower free energy? | Can't tell from Q alone |
- | ∆G = 0 → favored direction? | Neither (at equilibrium) |

## Relevant Knowledge-Graph Nodes

```json
[
  {
    "id": "article:acids-bases",
    "type": "article",
    "name": "Acids and Bases",
    "filePath": "acids-bases.md",
    "summary": "- **Acid** = proton (H⁺) donor - **Base** = proton (H⁺) acceptor - Any anion or neutral species with a lone pair can be a base",
    "tags": [],
    "complexity": "simple",
    "knowledgeMeta": {
      "wikilinks": [
        "thermodynamics",
        "buffers-physiology"
      ],
      "content": "# Acids and Bases\n\n## Definitions\n\n### Brønsted-Lowry (Most important for MCAT)\n- **Acid** = proton (H⁺) donor\n- **Base** = proton (H⁺) acceptor\n- Any anion or neutral species with a lone pair can be a base\n\n**Example:**\n```\nH₂CO₃ + H₂O ⇌ H₃O⁺ + HCO₃⁻\nAcids: H₂CO₃, H₃O⁺\nBases: HCO₃⁻, H₂O\n```\n\n### Lewis (Broader)\n- **Acid** = electron-pair acceptor\n- **Base** = electron-pair donor\n- Forms coordinate covalent bonds\n\n**Example (heme group):** O₂ binds to Fe²⁺\n- O₂ donates electron pair → **Lewis base**\n- Fe²⁺ accepts electron pair → **Lewis acid**\n\n## Conjugate Acid-Base Pairs\n\n**Conjugate base** = acid minus H⁺\n**Conjugate acid** = base plus H⁺\n\n```\nNH₃ + H₂O ⇌ NH₄⁺ + OH⁻\n          ↑      ↑\n        base   acid\n        \nForward:  NH₃ = base, H₂O = acid\n          NH₄⁺ = conj. acid of NH₃\n          OH⁻ = conj. base of H₂O\n\nReverse:  NH₄⁺ = acid, OH⁻ = base\n          NH₃ = conj. base of NH₄⁺\n          H₂O = conj. acid of OH⁻\n```\n\n## Acid/Base Strength\n\n### Acid Dissociation Constant (K<sub>a</sub>)\n```\nHA + H₂O ⇌ H₃O⁺ + A⁻\nKₐ = [H₃O⁺][A⁻] / [HA]\n```\n- Larger K<sub>a</sub> → stronger acid\n- pK<sub>a</sub> = –log K<sub>a</sub>\n- **Lower pK<sub>a</sub> → stronger acid**\n\n### Base Dissociation Constant (K<sub>b</sub>)\n```\nB + H₂O ⇌ HB⁺ + OH⁻\nK_b = [HB⁺][OH⁻] / [B]\n```\n- Larger K<sub>b</sub> → stronger base\n- pK<sub>b</sub> = –log K<sub>b</sub>\n- **Lower pK<sub>b</sub> → stronger base**\n\n## Amphoteric Substances\n- Can act as **both** acid and base\n- Conjugate base of a weak polyprotic acid is always amphoteric\n- Example: HCO₃⁻ (bicarbonate)\n  - As base: HCO₃⁻ + H₂O ⇌ H₂CO₃ + OH⁻\n  - As acid: HCO₃⁻ + H₂O ⇌ CO₃²⁻ + H₃O⁺\n- **Amino acids** are all amphoteric\n\n## pH and pOH\n\n**pH = –log[H⁺]** (or –log[H₃O⁺])\n- [H⁺] = 10⁻ᵖᴴ\n- Pure water: [H⁺] = 10⁻⁷ M → pH = 7 (neutral at 25°C)\n\n| pH Range | Solution |\n|----------|----------|\n| < 7 | Acidic |\n| = 7 | Neutral |\n| > 7 | Basic |\n\n**pOH = –log[OH⁻]**\n- [OH⁻] = 10⁻ᵖᴼᴴ\n- At 25°C: **pH + pOH = 14**\n\n## Buffer Solutions\n\n**Buffer** = resists pH change when small amounts of acid/base added\n- Contains weak acid + conjugate base (or weak base + conjugate acid)\n- In roughly equal concentrations\n\n### Bicarbonate Buffer System (Most important in blood)\n```\nReaction 1:  H₂CO₃ ⇌ H⁺ + HCO₃⁻\nReaction 2:  CO₂ + H₂O ⇌ H₂CO₃\n```\n\n**During exercise:** Muscles produce lactic acid → H⁺ increases\n- Reaction 1 shifts LEFT (Le Châtelier's principle)\n- Free H⁺ reduced → pH drop minimized\n\n**Holding breath:** CO₂ accumulates → Reaction 2 shifts RIGHT → more H₂CO₃ → more H⁺ → **pH decreases**\n\n## Quick Reference\n\n| Property | Stronger Acid | Stronger Base |\n|----------|---------------|---------------|\n| K value | Larger K<sub>a</sub> | Larger K<sub>b</sub> |\n| pK value | **Lower** pK<sub>a</sub> | **Lower** pK<sub>b</sub> |\n| pH | Lower | Higher |\n\n**Examples:**\n- Lactic acid (pK<sub>a</sub> = 3.9) > Uric acid (pK<sub>a</sub> = 5.6)\n- Lowest [H₃O⁺] = highest pH (seawater pH 8.5)\n- Least acidic = highest pK<sub>a</sub> (bicarbonate pK<sub>a</s",
      "backlinks": [
        "article:chapter-3-summary",
        "article:thermodynamics"
      ]
    }
  },
  {
    "id": "article:chapter-3-summary",
    "type": "article",
    "name": "Chapter 3: Biochemistry Basics — Summary",
    "filePath": "chapter-3-summary.md",
    "summary": "This chapter covers foundational biochemistry concepts tested on the MCAT: thermodynamics, kinetics, redox reactions, and acid/base chemistry.",
    "tags": [],
    "complexity": "simple",
    "knowledgeMeta": {
      "wikilinks": [
        "thermodynamics",
        "kinetics",
        "oxidation-reduction",
        "acids-bases"
      ],
      "content": "# Chapter 3: Biochemistry Basics — Summary\n\n## Overview\nThis chapter covers foundational biochemistry concepts tested on the MCAT: thermodynamics, kinetics, redox reactions, and acid/base chemistry.\n\n---\n\n## Major Topics\n\n### 1. [[thermodynamics]]\n- **Gibbs free energy:** ∆G = ∆H – T∆S\n- **Spontaneity:** ∆G < 0 (exergonic) vs ∆G > 0 (endergonic)\n- **Standard free energy:** ∆G°′ = –RT ln K'<sub>eq</sub> (pH 7, 1 M solutes)\n- **Actual cellular ∆G:** ∆G = ∆G°′ + RT ln Q\n- **Le Châtelier's principle:** Q vs K<sub>eq</sub> drives reaction direction\n- **Key:** Two factors determine spontaneity in cells — intrinsic properties (K<sub>eq</sub>) + concentrations (RT ln Q)\n\n### 2. [[kinetics]]\n- **Thermodynamics** ≠ **Kinetics** (∆G says nothing about rate)\n- **Activation energy (E<sub>a</sub>):** Barrier to reaching transition state [TS]‡\n- **Catalysts/Enzymes:** Lower E<sub>a</sub> by stabilizing TS, **do not change ∆G or K<sub>eq</sub>**\n- **Enzymes:** Biological catalysts, kinetic role only\n\n### 3. [[oxidation-reduction]]\n- **Oxidation** = loss of e⁻/H / gain of O\n- **Reduction** = gain of e⁻/H / loss of O\n- **Redox pairs:** One oxidized, one reduced (always coupled)\n- **Metabolism:** Catabolism = oxidative (releases energy); Anabolism = reductive (requires ATP)\n- **Glucose oxidation:** C₆H₁₂O₆ + 6 O₂ → 6 CO₂ + 6 H₂O\n\n### 4. [[acids-bases]]\n- **Brønsted-Lowry:** Acid = H⁺ donor, Base = H⁺ acceptor\n- **Lewis:** Acid = e⁻ pair acceptor, Base = e⁻ pair donor\n- **Conjugate pairs:** Differ by one H⁺\n- **Strength:** Lower pK<sub>a</sub> = stronger acid; Lower pK<sub>b</sub> = stronger base\n- **Amphoteric:** Can act as acid or base (e.g., HCO₃⁻, amino acids)\n- **pH = –log[H⁺]; pH + pOH = 14 (at 25°C)**\n- **Buffers:** Weak acid + conjugate base resist pH change\n- **Bicarbonate buffer:** CO₂ + H₂O ⇌ H₂CO₃ ⇌ H⁺ + HCO₃⁻ (key in blood)\n\n---\n\n## Key Equations to Memorize\n\n| Equation | Use |\n|----------|-----|\n| ∆G = ∆H – T∆S | Thermodynamic spontaneity |\n| ∆G°′ = –RT ln K'<sub>eq</sub> | Standard free energy ↔ equilibrium |\n| ∆G = ∆G°′ + RT ln Q | Actual cellular ∆G from concentrations |\n| pH = –log[H⁺] | Acidity |\n| pH + pOH = 14 | Acid-base relationship (25°C) |\n| pK<sub>a</sub> = –log K<sub>a</sub> | Acid strength |\n| pK<sub>b</sub> = –log K<sub>b</sub> | Base strength |\n\n---\n\n## High-Yield Facts for MCAT\n\n1. **ATP** = primary energy currency (high-energy phosphate bonds)\n2. **∆G < 0** = spontaneous; **∆G = 0** = equilibrium\n3. **Enzymes** lower E<sub>a</sub>, **do not** change ∆G or K<sub>eq</sub>\n4. **Catalysts** speed up both forward and reverse reactions equally\n5. **Redox:** OIL RIG (Oxidation Is Loss, Reduction Is Gain)\n6. **pK<sub>a</sub>:** Lower = stronger acid; Higher = weaker acid/more basic\n7. **Bicarbonate buffer** = main blood buffer; CO₂ accumulation → pH drops\n8. **Amphoteric** substances (HCO₃⁻, amino acids) can donate or accept H⁺\n\n---\n\n## Practice Questions Cross-Reference\n\n| Topic | Question Numbers |\n|-------|------------------|\n| Enzymes/E<s",
      "backlinks": []
    }
  },
  {
    "id": "article:kinetics",
    "type": "article",
    "name": "Kinetics and Activation Energy",
    "filePath": "kinetics.md",
    "summary": "**Thermodynamics** (∆G): Tells you *if* a reaction will occur and *where* it ends - ∆G < 0 = spontaneous (energetically favorable) - Says **nothing** about reaction rate or pathway",
    "tags": [],
    "complexity": "simple",
    "knowledgeMeta": {
      "wikilinks": [
        "thermodynamics",
        "enzymes"
      ],
      "content": "# Kinetics and Activation Energy\n\n## Thermodynamics vs. Kinetics\n\n**Thermodynamics** (∆G): Tells you *if* a reaction will occur and *where* it ends\n- ∆G < 0 = spontaneous (energetically favorable)\n- Says **nothing** about reaction rate or pathway\n\n**Kinetics** (E<sub>a</sub>): Tells you *how fast* a reaction occurs\n- Study of reaction rates = chemical kinetics\n\n**Key distinction:** \"Spontaneous\" in thermodynamics ≠ \"fast\" in common usage\n- Example: Wood burning is spontaneous (∆G < 0) but needs a match (activation energy) to start\n\n## Activation Energy (E<sub>a</sub>)\n\n**Definition:** Minimum energy required to reach the transition state [TS]‡\n\n**Transition state:**\n- Unstable, high-energy intermediate\n- intermediate\n- Exists momentarily → either forms products or reverts to reactants\n- Written as [TS]‡ in square brackets with double-cross symbol\n\n**E<sub>a</sub> is the barrier** preventing spontaneous reactions from proceeding at significant rates\n\n## Catalysts\n\n**Properties:**\n1. Lower E<sub>a</sub> by stabilizing the transition state\n2. **Do not change ∆G** (thermodynamics unchanged)\n3. Not consumed — regenerated each reaction cycle\n\n**Enzymes** = biological catalysts\n- Kinetic role only (affect rate, not equilibrium)\n- Can increase rate enormously (years → seconds)\n- **Do not alter** equilibrium concentrations of reactants/products\n\n## Reaction Coordinate Graph\n\n```\nFree Energy\n  ↑\n  │    [TS]‡ (no catalyst)\n  │   / \\\n  │  /   \\       Ea without catalyst\n  │ /     \\\n  │/       \\______________ Products\n  │\n  │    [TS]‡ (with catalyst)\n  │   / \\\n  │  /   \\       Ea with catalyst (lower)\n  │ /     \\\n  │/       \\______________ Products\n  │\n  └──────────────────────→ Reaction Coordinate\n  Reactants\n```\n\n- x-axis: reaction progress (reaction coordinate)\n- y-axis: free energy\n- ∆G = G<sub>products</sub> – G<sub>reactants</sub> (unchanged by catalyst)\n\n## Key Concept Summary\n\n| Concept | Thermodynamic or Kinetic? | Affected by Catalyst? |\n|---------|---------------------------|----------------------|\n| ∆G (spontaneity) | Thermodynamic | No |\n| K<sub>eq</sub> (equilibrium) | Thermodynamic | No |\n| E<sub>a</sub> (activation energy) | Kinetic | **Yes** (lowered) |\n| Reaction rate | Kinetic | **Yes** (increased) |\n| Equilibrium concentrations | Thermodynamic | No |\n\n---\n\n*See also: [[thermodynamics]], [[enzymes]] (Chapter 4)*",
      "backlinks": [
        "article:chapter-3-summary",
        "article:thermodynamics"
      ]
    }
  },
  {
    "id": "article:oxidation-reduction",
    "type": "article",
    "name": "Oxidation and Reduction (Redox)",
    "filePath": "oxidation-reduction.md",
    "summary": "**Oxidation** = loss of electrons **Reduction** = gain of electrons",
    "tags": [],
    "complexity": "simple",
    "knowledgeMeta": {
      "wikilinks": [
        "thermodynamics",
        "metabolism-overview"
      ],
      "content": "# Oxidation and Reduction (Redox)\n\n## Core Concept\n\n**Oxidation** = loss of electrons\n**Reduction** = gain of electrons\n\n**Mnemonic:** OIL RIG — Oxidation Is Loss, Reduction Is Gain\n\nWhen one atom is oxidized, another **must** be reduced → **redox pair**\n\n## Three Ways to Identify Redox Reactions\n\n| Oxidation (loss) | Reduction (gain) |\n|------------------|------------------|\n| Gain of O atoms | Loss of O atoms |\n| Loss of H atoms | Gain of H atoms |\n| Loss of electrons | Gain of electrons |\n\n## Quick Examples\n\n| Change | Classification | Reason |\n|--------|----------------|--------|\n| CH₃CH₃ → H₂C=CH₂ | Oxidation | Hydrogens removed |\n| Fe³⁺ → Fe²⁺ | Reduction | Electron added |\n| O₂ → H₂O | Reduction | Hydrogens added to O₂ |\n| Disulfide bond formation | Oxidation | Hydrogens removed |\n\n## Energy Metabolism Context\n\n**Photosynthesis:** Plants (photoautotrophs) store solar energy in carbohydrates\n**Cellular respiration:** Animals (chemoheterotrophs) oxidize reduced molecules (carbs, fats) → CO₂ + ATP\n\n**Glucose oxidation:**\n```\nC₆H₁₂O₆ + 6 O₂ → 6 CO₂ + 6 H₂O\n```\n- Carbons in glucose → oxidized (to CO₂)\n- Oxygen → reduced (to H₂O)\n- Redox pair: C (oxidized) / O (reduced)\n\n## Catabolism vs. Anabolism\n\n| Process | Direction | Redox | Energy |\n|---------|-----------|-------|--------|\n| **Catabolism** | Breaking down | Oxidative | Releases energy |\n| **Anabolism** | Building up | Reductive | Requires energy (ATP) |\n\n- Fatty acid synthesis = successive reductions of carbon chain\n- ATP stores energy from catabolism; drives anabolism\n\n---\n\n*See also: [[thermodynamics]], [[metabolism-overview]]*",
      "backlinks": [
        "article:chapter-3-summary",
        "article:thermodynamics"
      ]
    }
  },
  {
    "id": "article:thermodynamics",
    "type": "article",
    "name": "Thermodynamics",
    "filePath": "thermodynamics.md",
    "summary": "**Energy Forms:** - **Kinetic energy** — movement of molecules - **Potential energy** — energy stored in chemical bonds - Most important potential energy storage molecule: **ATP** (energy in ester ...",
    "tags": [],
    "complexity": "simple",
    "knowledgeMeta": {
      "wikilinks": [
        "kinetics",
        "oxidation-reduction",
        "acids-bases"
      ],
      "content": "# Thermodynamics\n\n## Key Concepts\n\n**Energy Forms:**\n- **Kinetic energy** — movement of molecules\n- **Potential energy** — energy stored in chemical bonds\n  - Most important potential energy storage molecule: **ATP** (energy in ester bonds between phosphate groups)\n\n## Laws of Thermodynamics\n\n**First Law (Conservation of Energy):**\n- Energy of the universe is constant\n- When system energy decreases, surroundings energy increases, and vice versa\n\n**Second Law (Entropy):**\n- Disorder (entropy, S) of the universe tends to increase\n- Spontaneous reactions increase universal disorder\n- ∆S = S<sub>final</sub> – S<sub>initial</sub>\n- If ∆S is negative → disorder decreased\n\n## Gibbs Free Energy (∆G)\n\n**Equation:** ∆G = ∆H – T∆S\n\nWhere:\n- ∆H = enthalpy change (bond energy + P∆V)\n- T = temperature (Kelvin)\n- ∆S = entropy change\n\n**In cells:** Since ∆V ≈ 0 (liquid phase), **∆H ≈ ∆E** (bond energy)\n\n**Spontaneity:**\n- ∆G < 0 → spontaneous (exergonic, energy exits system)\n- ∆G > 0 → nonspontaneous (endergonic, requires energy input)\n- ∆G = 0 → equilibrium\n\n**Enthalpy:**\n- ∆H < 0 → exothermic (liberates heat)\n- ∆H > 0 → endothermic (requires heat input)\n- Most metabolic reactions are exothermic → maintains body temperature\n\n**Sign convention:** All from system's perspective (negative ∆G = system goes to lower free energy)\n\n## Standard Free Energy\n\n**∆G°′** — biochemical standard: 1 M all solutes except H<sup>+</sup>, pH 7\n\n**Relationship to equilibrium:**\n- ∆G°′ = –RT ln K'<sub>eq</sub>\n- K'<sub>eq</sub> = [C]<sup>c</sup>[D]<sup>d</sup> / [A]<sup>a</sup>[B]<sup>b</sup> at equilibrium\n\n**When K'<sub>eq</sub> = 1:** ∆G°′ = 0 (ln 1 = 0)\n\n## Reaction Quotient (Q) vs. Actual ∆G\n\n**Equation:** ∆G = ∆G°′ + RT ln Q\n\nWhere Q uses **actual cellular concentrations**, not equilibrium concentrations.\n\n**Key relationships:**\n- Q < K<sub>eq</sub> → ∆G < 0 → forward reaction spontaneous\n- Q > K<sub>eq</sub> → ∆G > 0 → reverse reaction spontaneous\n- Q = K<sub>eq</sub> → ∆G = 0 → equilibrium\n\n**Two factors determine spontaneity in cell:**\n1. Intrinsic properties (K<sub>eq</sub>)\n2. Concentrations (RT ln Q)\n\n**Le Châtelier's principle:** Adding reactants (Q < K) drives forward; adding products (Q > K) drives backward\n\n## Key Questions Answered\n\n| Question | Answer |\n|----------|--------|\n| Can ∆G be negative if ∆G°′ is positive? | Yes, if RT ln Q is sufficiently negative |\n| Does K<sub>eq</sub> indicate reaction rate? | No — only relative concentrations at equilibrium |\n| Large K<sub>eq</sub> → lower free energy? | Products |\n| Large Q → lower free energy? | Can't tell from Q alone |\n| ∆G = 0 → favored direction? | Neither (at equilibrium) |\n| Radiolabeled B added at equilibrium → where found? | Both A and B (dynamic equilibrium) |\n\n---\n\n*See also: [[kinetics]], [[oxidation-reduction]], [[acids-bases]]*",
      "backlinks": [
        "article:acids-bases",
        "article:chapter-3-summary",
        "article:kinetics",
        "article:oxidation-reduction"
      ]
    }
  },
  {
    "id": "entity:enzymes",
    "type": "entity",
    "name": "Enzymes",
    "summary": "Biological catalysts (typically proteins) that lower activation energy without altering reaction thermodynamics",
    "tags": [
      "entity",
      "biochemistry",
      "protein"
    ],
    "complexity": "simple"
  },
  {
    "id": "entity:le-chatelier-principle",
    "type": "entity",
    "name": "Le Châtelier's Principle",
    "summary": "A system at equilibrium responds to a disturbance (concentration, pressure, temperature) by shifting to counteract the change",
    "tags": [
      "entity",
      "chemistry",
      "equilibrium"
    ],
    "complexity": "simple"
  },
  {
    "id": "entity:gibbs-free-energy",
    "type": "entity",
    "name": "Gibbs Free Energy",
    "summary": "Thermodynamic potential (∆G = ∆H – T∆S) predicting spontaneity; ∆G < 0 indicates a spontaneous process at constant T and P",
    "tags": [
      "entity",
      "thermodynamics",
      "energy"
    ],
    "complexity": "simple"
  },
  {
    "id": "entity:activation-energy",
    "type": "entity",
    "name": "Activation Energy (Ea)",
    "summary": "Minimum energy barrier reactants must overcome to reach the transition state; determines reaction rate but not equilibrium",
    "tags": [
      "entity",
      "kinetics",
      "energy"
    ],
    "complexity": "simple"
  },
  {
    "id": "claim:thermodynamics:dg-dh-tds",
    "type": "claim",
    "name": "Gibbs Free Energy Equation",
    "summary": "∆G = ∆H – T∆S relates enthalpy, entropy, and temperature to determine reaction spontaneity",
    "tags": [
      "claim",
      "biochemistry",
      "thermodynamics",
      "equation"
    ],
    "complexity": "simple"
  },
  {
    "id": "claim:thermodynamics:spontaneity",
    "type": "claim",
    "name": "Spontaneity Criterion",
    "summary": "A process is spontaneous at constant temperature and pressure if and only if ∆G < 0",
    "tags": [
      "claim",
      "biochemistry",
      "thermodynamics"
    ],
    "complexity": "simple"
  },
  {
    "id": "claim:thermodynamics:dg-standard",
    "type": "claim",
    "name": "Standard Free Energy and Equilibrium",
    "summary": "∆G°′ = –RT ln K'eq links standard free energy change to the equilibrium constant at pH 7",
    "tags": [
      "claim",
      "biochemistry",
      "thermodynamics",
      "equation"
    ],
    "complexity": "simple"
  },
  {
    "id": "claim:thermodynamics:dg-q",
    "type": "claim",
    "name": "Reaction Quotient Determines Direction",
    "summary": "∆G = ∆G°′ + RT ln Q; reaction proceeds forward when Q < K'eq (∆G < 0) and reverse when Q > K'eq",
    "tags": [
      "claim",
      "biochemistry",
      "thermodynamics",
      "equation"
    ],
    "complexity": "simple"
  },
  {
    "id": "claim:thermodynamics:dh-approx-de",
    "type": "claim",
    "name": "Enthalpy Approximates Internal Energy in Cells",
    "summary": "In cellular conditions (constant pressure, negligible volume change), ∆H ≈ ∆E",
    "tags": [
      "claim",
      "biochemistry",
      "thermodynamics"
    ],
    "complexity": "simple"
  },
  {
    "id": "claim:kinetics:thermo-vs-kinetics",
    "type": "claim",
    "name": "Thermodynamics vs Kinetics Distinction",
    "summary": "Thermodynamics determines whether a reaction can occur (∆G); kinetics determines how fast it occurs (Ea, rate constants)",
    "tags": [
      "claim",
      "biochemistry",
      "kinetics"
    ],
    "complexity": "simple"
  },
  {
    "id": "claim:chapter-3-summary:thermo-not-kinetics",
    "type": "claim",
    "name": "Thermodynamics does not determine kinetics",
    "summary": "ΔG indicates spontaneity but says nothing about reaction rate; thermodynamics and kinetics are independent concepts",
    "tags": [
      "claim",
      "biochemistry",
      "thermodynamics"
    ],
    "complexity": "simple"
  },
  {
    "id": "claim:chapter-3-summary:enzymes-lower-ea-not-delta-g",
    "type": "claim",
    "name": "Enzymes lower activation energy without changing ΔG or Keq",
    "summary": "Enzymes (biological catalysts) stabilize the transition state to lower Ea, accelerating both forward and reverse reactions equally, but do not alter the overall ΔG or equilibrium constant",
    "tags": [
      "claim",
      "biochemistry",
      "enzymes"
    ],
    "complexity": "simple"
  }
]
```

## Relevant Knowledge-Graph Edges

```json
[
  {
    "source": "article:acids-bases",
    "target": "article:thermodynamics",
    "type": "related",
    "direction": "forward",
    "weight": 0.7
  },
  {
    "source": "article:chapter-3-summary",
    "target": "article:thermodynamics",
    "type": "related",
    "direction": "forward",
    "weight": 0.7
  },
  {
    "source": "article:chapter-3-summary",
    "target": "article:kinetics",
    "type": "related",
    "direction": "forward",
    "weight": 0.7
  },
  {
    "source": "article:chapter-3-summary",
    "target": "article:oxidation-reduction",
    "type": "related",
    "direction": "forward",
    "weight": 0.7
  },
  {
    "source": "article:chapter-3-summary",
    "target": "article:acids-bases",
    "type": "related",
    "direction": "forward",
    "weight": 0.7
  },
  {
    "source": "article:kinetics",
    "target": "article:thermodynamics",
    "type": "related",
    "direction": "forward",
    "weight": 0.7
  },
  {
    "source": "article:oxidation-reduction",
    "target": "article:thermodynamics",
    "type": "related",
    "direction": "forward",
    "weight": 0.7
  },
  {
    "source": "article:thermodynamics",
    "target": "article:kinetics",
    "type": "related",
    "direction": "forward",
    "weight": 0.7
  },
  {
    "source": "article:thermodynamics",
    "target": "article:oxidation-reduction",
    "type": "related",
    "direction": "forward",
    "weight": 0.7
  },
  {
    "source": "article:thermodynamics",
    "target": "article:acids-bases",
    "type": "related",
    "direction": "forward",
    "weight": 0.7
  },
  {
    "source": "article:kinetics",
    "target": "article:thermodynamics",
    "type": "builds_on",
    "direction": "forward",
    "weight": 0.85,
    "description": "Kinetics article explicitly contrasts kinetics (rate, Ea) with thermodynamics (∆G, equilibrium), stating catalysts lower Ea without changing ∆G"
  },
  {
    "source": "article:oxidation-reduction",
    "target": "article:thermodynamics",
    "type": "builds_on",
    "direction": "forward",
    "weight": 0.8,
    "description": "Redox reactions are framed in terms of free energy release; glucose oxidation's -2870 kJ/mol is a thermodynamic quantity driving ATP synthesis"
  },
  {
    "source": "article:kinetics",
    "target": "entity:enzymes",
    "type": "exemplifies",
    "direction": "forward",
    "weight": 0.8,
    "description": "Enzymes are presented as the primary biological exemplars of catalysts that lower Ea"
  },
  {
    "source": "article:kinetics",
    "target": "entity:catalysts",
    "type": "exemplifies",
    "direction": "forward",
    "weight": 0.75,
    "description": "General catalyst behavior (lowering Ea, not changing ∆G) is illustrated through enzyme mechanisms"
  },
  {
    "source": "article:oxidation-reduction",
    "target": "entity:glucose-oxidation",
    "type": "exemplifies",
    "direction": "forward",
    "weight": 0.85,
    "description": "Glucose oxidation is the central worked example of a coupled redox reaction in catabolism"
  },
  {
    "source": "article:thermodynamics",
    "target": "entity:atp",
    "type": "exemplifies",
    "direction": "forward",
    "weight": 0.8,
    "description": "ATP hydrolysis (∆G ≈ -30.5 kJ/mol) is the key biological example of a favorable free energy change driving coupled reactions"
  },
  {
    "source": "article:thermodynamics",
    "target": "entity:le-chatelier-principle",
    "type": "cites",
    "direction": "forward",
    "weight": 0.7,
    "description": "Le Châtelier's principle is invoked to explain how changing reactant/product concentrations (Q) shifts reaction direction"
  },
  {
    "source": "article:thermodynamics",
    "target": "entity:gibbs-free-energy",
    "type": "cites",
    "direction": "forward",
    "weight": 0.75,
    "description": "Gibbs free energy equation ∆G = ∆H – T∆S is the foundational thermodynamic relation developed in the article"
  },
  {
    "source": "article:kinetics",
    "target": "entity:activation-energy",
    "type": "cites",
    "direction": "forward",
    "weight": 0.8,
    "description": "Activation energy Ea and transition state theory are the core kinetic concepts introduced"
  },
  {
    "source": "article:kinetics",
    "target": "entity:transition-state",
    "type": "cites",
    "direction": "forward",
    "weight": 0.75,
    "description": "Transition state [TS]‡ is presented as the high-energy intermediate stabilized by catalysts"
  },
  {
    "source": "article:chapter-3-summary",
    "target": "article:acids-bases",
    "type": "builds_on",
    "direction": "forward",
    "weight": 0.8,
    "description": "Chapter 3 summary explicitly summarizes and integrates acids-bases as one of four major topics with condensed key points"
  },
  {
    "source": "article:acids-bases",
    "target": "entity:le-chatelier-principle",
    "type": "exemplifies",
    "direction": "forward",
    "weight": 0.7,
    "description": "Bicarbonate buffer response to lactic acid during exercise explicitly invokes Le Chatelier's principle (reaction shifts left to consume added H+)"
  },
  {
    "source": "article:acids-bases",
    "target": "entity:bicarbonate-buffer-system",
    "type": "exemplifies",
    "direction": "forward",
    "weight": 0.7,
    "description": "Article provides detailed mechanism of bicarbonate buffer system including both carbonic acid dissociation and CO2 hydration reactions"
  },
  {
    "source": "article:acids-bases",
    "target": "entity:lactic-acid",
    "type": "exemplifies",
    "direction": "forward",
    "weight": 0.7,
    "description": "Lactic acid used as concrete example of metabolic acid production during exercise that challenges blood pH"
  },
  {
    "source": "article:acids-bases",
    "target": "entity:amino-acids",
    "type": "exemplifies",
    "direction": "forward",
    "weight": 0.7,
    "description": "Amino acids cited as universal example of amphoteric substances"
  },
  {
    "source": "article:chapter-3-summary",
    "target": "entity:princeton-review",
    "type": "cites",
    "direction": "forward",
    "weight": 0.7,
    "description": "Chapter 3 summary explicitly cites Princeton Review MCAT Biochemistry Review as its source"
  },
  {
    "source": "article:chapter-3-summary",
    "target": "entity:glucose-oxidation",
    "type": "exemplifies",
    "direction": "forward",
    "weight": 0.7,
    "description": "Glucose oxidation equation (C6H12O6 + 6 O2 → 6 CO2 + 6 H2O) given as canonical example of complete oxidation in catabolism"
  },
  {
    "source": "article:chapter-3-summary",
    "target": "entity:atp",
    "type": "exemplifies",
    "direction": "forward",
    "weight": 0.6,
    "description": "ATP cited as primary energy currency with high-energy phosphate bonds in high-yield facts"
  },
  {
    "source": "article:chapter-3-summary",
    "target": "entity:enzymes",
    "type": "exemplifies",
    "direction": "forward",
    "weight": 0.6,
    "description": "Enzymes described as biological catalysts with purely kinetic role in high-yield facts"
  },
  {
    "source": "article:chapter-3-summary",
    "target": "entity:catalysts",
    "type": "exemplifies",
    "direction": "forward",
    "weight": 0.6,
    "description": "Catalysts noted to speed both forward and reverse reactions equally without changing ΔG or Keq"
  }
]
```

## Explicit Source Gaps

- Add source gaps during generation when the packet lacks support.
