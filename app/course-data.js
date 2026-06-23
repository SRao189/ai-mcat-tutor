window.MCAT_COURSE_DATA = [
  {
    "id": "module-1",
    "title": "Thermodynamics",
    "objectives": [
      "Understand the key concepts of thermodynamics including energy forms and the laws of thermodynamics",
      "Apply the Gibbs free energy equation to determine reaction spontaneity",
      "Explain the relationship between standard free energy, equilibrium, and actual cellular conditions",
      "Use Le Châtelier's principle to predict reaction direction based on concentrations"
    ],
    "sections": [
      {
        "id": "section-1",
        "title": "Key Concepts",
        "content": "Energy exists in two primary forms: kinetic energy (movement of molecules) and potential energy (stored in chemical bonds). The most important potential energy storage molecule in biological systems is ATP, with energy stored in the ester bonds between its phosphate groups.",
        "sourceRefs": [
          "wiki/course/context/module-1-context.md:22-24"
        ]
      },
      {
        "id": "section-2",
        "title": "Laws of Thermodynamics",
        "content": "The First Law states that the energy of the universe is constant; when system energy decreases, surroundings energy increases, and vice versa. The Second Law states that disorder (entropy, S) of the universe tends to increase, and spontaneous reactions increase universal disorder. Entropy change is calculated as ∆S = S_final – S_initial. If ∆S is negative, disorder has decreased.",
        "sourceRefs": [
          "wiki/course/context/module-1-context.md:28-37"
        ]
      },
      {
        "id": "section-3",
        "title": "Gibbs Free Energy",
        "content": "Gibbs free energy (∆G) determines reaction spontaneity. The equation is ∆G = ∆H – T∆S, where ∆H is enthalpy change (bond energy + P∆V), T is temperature in Kelvin, and ∆S is entropy change. In cells, since volume change is approximately zero (∆V ≈ 0), ∆H ≈ ∆E (bond energy). A negative ∆G indicates a spontaneous (exergonic) reaction where energy exits the system. A positive ∆G indicates a nonspontaneous (endergonic) reaction requiring energy input. When ∆G = 0, the system is at equilibrium. Enthalpy change (∆H) indicates heat flow: negative ∆H is exothermic (releases heat), positive ∆H is endothermic (requires heat input). Most metabolic reactions are exothermic, helping maintain body temperature. All sign conventions are from the system's perspective: negative ∆G means the system goes to lower free energy.",
        "sourceRefs": [
          "wiki/course/context/module-1-context.md:40-60"
        ]
      },
      {
        "id": "section-4",
        "title": "Standard Free Energy",
        "content": "Standard free energy (∆G°′) is defined under biochemical standard conditions: 1 M concentration for all solutes except H⁺, with pH 7. The relationship between standard free energy and equilibrium is given by ∆G°′ = –RT ln K'_eq, where K'_eq is the equilibrium constant calculated as [C]^c[D]^d / [A]^a[B]^b at equilibrium. When K'_eq = 1, ∆G°′ = 0 (since ln 1 = 0).",
        "sourceRefs": [
          "wiki/course/context/module-1-context.md:63-70"
        ]
      },
      {
        "id": "section-5",
        "title": "Reaction Quotient and Actual Free Energy",
        "content": "The actual free energy change in a cell is determined by ∆G = ∆G°′ + RT ln Q, where Q is the reaction quotient using actual cellular concentrations, not equilibrium concentrations. When Q < K_eq, ∆G < 0 and the forward reaction is spontaneous. When Q > K_eq, ∆G > 0 and the reverse reaction is spontaneous. When Q = K_eq, ∆G = 0 and the system is at equilibrium. Two factors determine spontaneity in cells: intrinsic properties (K_eq) and concentrations (RT ln Q). Le Châtelier's principle states that adding reactants (Q < K) drives the reaction forward, while adding products (Q > K) drives it backward.",
        "sourceRefs": [
          "wiki/course/context/module-1-context.md:73-87"
        ]
      }
    ],
    "equations": [
      {
        "expression": "∆S = S_final – S_initial",
        "meaning": "Change in entropy equals final entropy minus initial entropy.",
        "sourceRefs": [
          "wiki/course/context/module-1-context.md:35"
        ]
      },
      {
        "expression": "∆G = ∆H – T∆S",
        "meaning": "Gibbs free energy change equals enthalpy change minus temperature times entropy change.",
        "sourceRefs": [
          "wiki/course/context/module-1-context.md:40"
        ]
      },
      {
        "expression": "∆G°′ = –RT ln K'_eq",
        "meaning": "Standard free energy change equals negative R times T times the natural logarithm of the equilibrium constant.",
        "sourceRefs": [
          "wiki/course/context/module-1-context.md:66"
        ]
      },
      {
        "expression": "∆G = ∆G°′ + RT ln Q",
        "meaning": "Actual free energy change equals standard free energy change plus R times T times the natural logarithm of the reaction quotient.",
        "sourceRefs": [
          "wiki/course/context/module-1-context.md:73"
        ]
      }
    ],
    "workedExamples": [
      {
        "question": "Can ∆G be negative if ∆G°′ is positive?",
        "steps": [
          "Recall that ∆G = ∆G°′ + RT ln Q",
          "If ∆G°′ is positive, the reaction is nonspontaneous under standard conditions",
          "However, if RT ln Q is sufficiently negative, the overall ∆G can become negative",
          "This occurs when Q is much smaller than K_eq, meaning reactant concentrations are high and product concentrations are low"
        ],
        "answer": "Yes, if RT ln Q is sufficiently negative.",
        "sourceRefs": [
          "wiki/course/context/module-1-context.md:92"
        ]
      },
      {
        "question": "What happens to a reaction at equilibrium when more reactant is added?",
        "steps": [
          "At equilibrium, Q = K_eq and ∆G = 0",
          "Adding more reactant increases the concentration of reactants",
          "This decreases Q (since Q = [products]/[reactants])",
          "When Q < K_eq, ∆G becomes negative",
          "According to Le Châtelier's principle, the system responds by shifting the reaction forward to consume the added reactant"
        ],
        "answer": "The reaction shifts forward to consume the added reactant.",
        "sourceRefs": [
          "wiki/course/context/module-1-context.md:86-87"
        ]
      }
    ],
    "checks": [
      {
        "question": "Is the following statement true or false? '∆G < 0 means the reaction is fast.'",
        "answer": "False",
        "explanation": "∆G < 0 indicates a spontaneous (thermodynamically favorable) reaction, but says nothing about the reaction rate. Kinetics (activation energy) determines speed, not thermodynamics.",
        "sourceRefs": [
          "wiki/course/context/module-1-context.md:93"
        ],
        "reviewTarget": "thermodynamics vs kinetics"
      },
      {
        "question": "What does a large K_eq value indicate about the relative free energy of products versus reactants?",
        "answer": "Products have lower free energy than reactants",
        "explanation": "A large K_eq means the equilibrium favors products. Since ∆G°′ = –RT ln K_eq, a large K_eq results in a negative ∆G°′, indicating products are at lower free energy than reactants.",
        "sourceRefs": [
          "wiki/course/context/module-1-context.md:94"
        ],
        "reviewTarget": "standard free energy and equilibrium"
      }
    ],
    "practiceQuestions": [
      {
        "question": "Which of the following best describes the relationship between ∆G, ∆G°′, and Q?",
        "choices": [
          "∆G = ∆G°′ + RT ln K_eq",
          "∆G = ∆G°′ + RT ln Q",
          "∆G°′ = ∆G + RT ln Q",
          "Q = ∆G°′ + RT ln ∆G"
        ],
        "answer": "∆G = ∆G°′ + RT ln Q",
        "explanation": "The equation ∆G = ∆G°′ + RT ln Q relates the actual free energy change to the standard free energy change and the reaction quotient using actual concentrations.",
        "sourceRefs": [
          "wiki/course/context/module-1-context.md:73"
        ],
        "reviewTarget": "reaction quotient and actual free energy"
      },
      {
        "question": "In a system at equilibrium, if radiolabeled B is added, where will the label be found after equilibrium is re-established?",
        "choices": [
          "Only in B",
          "Only in A",
          "In both A and B",
          "Nowhere, since the system is at equilibrium"
        ],
        "answer": "In both A and B",
        "explanation": "At dynamic equilibrium, reactions continue in both directions. Adding radiolabeled B will lead to the formation of labeled A as the forward reaction proceeds, and labeled B will remain as the reverse reaction occurs.",
        "sourceRefs": [
          "wiki/course/context/module-1-context.md:97"
        ],
        "reviewTarget": "equilibrium dynamics"
      }
    ],
    "sourceRefs": [
      "wiki/course/context/module-1-context.md",
      "wiki/thermodynamics.md",
      "wiki/.understand-anything/knowledge-graph.json"
    ],
    "sourceGaps": []
  },
  {
    "id": "module-2",
    "title": "Kinetics and Activation Energy",
    "objectives": [
      "Distinguish what thermodynamics tells you from what kinetics tells you about a reaction",
      "Define activation energy and the transition state",
      "Explain how catalysts and enzymes affect reaction rate without changing ∆G or K_eq"
    ],
    "sections": [
      {
        "id": "section-1",
        "title": "Thermodynamics vs. Kinetics",
        "content": "Thermodynamics (measured by ∆G) tells you whether a reaction will occur and where it ends up: a negative ∆G means the reaction is spontaneous (energetically favorable), but this says nothing about reaction rate or pathway. Kinetics (measured by activation energy, E_a) tells you how fast a reaction occurs; the study of reaction rates is called chemical kinetics. \"Spontaneous\" in the thermodynamic sense does not mean \"fast\" in everyday usage — wood burning is spontaneous (∆G < 0) but still needs a match (activation energy) to start.",
        "sourceRefs": [
          "wiki/course/context/module-2-context.md:19-29"
        ]
      },
      {
        "id": "section-2",
        "title": "Activation Energy and the Transition State",
        "content": "Activation energy (E_a) is the minimum energy required to reach the transition state, written [TS]‡. The transition state is an unstable, high-energy intermediate that exists only momentarily before either forming products or reverting back to reactants. E_a acts as the barrier preventing spontaneous reactions from proceeding at a significant rate.",
        "sourceRefs": [
          "wiki/course/context/module-2-context.md:31-41"
        ]
      },
      {
        "id": "section-3",
        "title": "Catalysts and Enzymes",
        "content": "Catalysts lower E_a by stabilizing the transition state, do not change ∆G (the thermodynamics of the reaction is unchanged), and are not consumed — they are regenerated each reaction cycle. Enzymes are biological catalysts with a purely kinetic role: they affect rate, not equilibrium. Enzymes can increase reaction rate enormously (from years to seconds) but do not alter the equilibrium concentrations of reactants or products.",
        "sourceRefs": [
          "wiki/course/context/module-2-context.md:43-53"
        ]
      },
      {
        "id": "section-4",
        "title": "Reaction Coordinate and Key Concept Summary",
        "content": "On a reaction coordinate graph, the x-axis is reaction progress and the y-axis is free energy; ∆G equals the free energy of products minus the free energy of reactants and is unchanged by a catalyst, while a catalyst lowers the height of the transition-state peak (E_a). Summarizing which quantities are thermodynamic versus kinetic, and whether a catalyst affects them: ∆G (thermodynamic, not affected by catalyst), K_eq (thermodynamic, not affected by catalyst), E_a (kinetic, lowered by catalyst), reaction rate (kinetic, increased by catalyst), and equilibrium concentrations (thermodynamic, not affected by catalyst).",
        "sourceRefs": [
          "wiki/course/context/module-2-context.md:55-88"
        ]
      }
    ],
    "equations": [
      {
        "expression": "∆G = G_products – G_reactants",
        "meaning": "Gibbs free energy change equals the free energy of products minus the free energy of reactants; this value is unchanged by a catalyst.",
        "sourceRefs": [
          "wiki/course/context/module-2-context.md:78"
        ]
      }
    ],
    "workedExamples": [
      {
        "question": "Wood burning has a negative ∆G, meaning it is thermodynamically spontaneous. Why doesn't a pile of wood spontaneously combust at room temperature without a match?",
        "steps": [
          "∆G < 0 only tells you the reaction is energetically favorable (thermodynamically spontaneous) — it says nothing about reaction rate or pathway",
          "Reaction rate is governed by kinetics, specifically the activation energy (E_a), the minimum energy needed to reach the transition state",
          "Without enough energy input to clear the E_a barrier, the reaction proceeds too slowly to be observed",
          "The match supplies the energy needed to reach the transition state, after which the reaction proceeds on its own"
        ],
        "answer": "Because a spontaneous reaction (∆G < 0) is not necessarily a fast one — wood burning still has an activation energy barrier (E_a) that must be overcome, and the match provides that initial energy.",
        "sourceRefs": [
          "wiki/course/context/module-2-context.md:21-29"
        ]
      }
    ],
    "checks": [
      {
        "question": "Is the following statement true or false? 'Adding an enzyme to a reaction changes its equilibrium constant (K_eq).'",
        "answer": "False",
        "explanation": "Enzymes are catalysts with a purely kinetic role — they lower E_a and increase rate but do not alter equilibrium concentrations of reactants or products, so K_eq is unchanged.",
        "sourceRefs": [
          "wiki/course/context/module-2-context.md:50-53"
        ],
        "reviewTarget": "catalysts and enzymes"
      },
      {
        "question": "What is the transition state [TS]‡?",
        "answer": "An unstable, high-energy intermediate that exists momentarily during a reaction before forming products or reverting to reactants",
        "explanation": "The transition state sits at the peak of the reaction coordinate graph and represents the highest-energy point the system must pass through; activation energy is the energy needed to reach it.",
        "sourceRefs": [
          "wiki/course/context/module-2-context.md:33-39"
        ],
        "reviewTarget": "activation energy and the transition state"
      },
      {
        "question": "A catalyst is added to a reaction. Which of the following changes?",
        "choices": [
          "∆G",
          "K_eq",
          "Activation energy (E_a)",
          "Equilibrium concentrations of products"
        ],
        "answer": "Activation energy (E_a)",
        "explanation": "Catalysts lower E_a by stabilizing the transition state; ∆G, K_eq, and equilibrium concentrations are thermodynamic quantities that catalysts do not change.",
        "sourceRefs": [
          "wiki/course/context/module-2-context.md:82-88"
        ],
        "reviewTarget": "reaction coordinate and key concept summary"
      }
    ],
    "practiceQuestions": [
      {
        "question": "Which of the following best distinguishes thermodynamics from kinetics?",
        "choices": [
          "Thermodynamics tells you how fast a reaction goes; kinetics tells you if it is spontaneous",
          "Thermodynamics tells you if a reaction will occur and where it ends; kinetics tells you how fast it occurs",
          "Thermodynamics and kinetics both measure reaction rate",
          "Thermodynamics only applies to enzyme-catalyzed reactions"
        ],
        "answer": "Thermodynamics tells you if a reaction will occur and where it ends; kinetics tells you how fast it occurs",
        "explanation": "∆G (thermodynamics) indicates spontaneity and the final equilibrium position, while E_a and rate (kinetics) indicate how quickly the reaction proceeds.",
        "sourceRefs": [
          "wiki/course/context/module-2-context.md:19-26"
        ],
        "reviewTarget": "thermodynamics vs. kinetics"
      },
      {
        "question": "An enzyme increases the rate of a reaction from years to seconds. What happens to the equilibrium concentrations of reactants and products?",
        "choices": [
          "They shift toward more products than before",
          "They shift toward more reactants than before",
          "They remain the same as without the enzyme",
          "They cannot be determined without more information"
        ],
        "answer": "They remain the same as without the enzyme",
        "explanation": "Enzymes have a purely kinetic role — they speed up forward and reverse reactions equally and do not alter the equilibrium concentrations of reactants or products.",
        "sourceRefs": [
          "wiki/course/context/module-2-context.md:50-53"
        ],
        "reviewTarget": "catalysts and enzymes"
      },
      {
        "question": "On a reaction coordinate graph, what does the height of the peak [TS]‡ represent relative to the reactants?",
        "answer": "The activation energy (E_a) — the minimum energy barrier that must be overcome to reach the transition state",
        "explanation": "The transition state sits at the top of the reaction coordinate curve; the energy difference between the reactants and this peak is E_a.",
        "sourceRefs": [
          "wiki/course/context/module-2-context.md:55-78"
        ],
        "reviewTarget": "reaction coordinate and key concept summary"
      }
    ],
    "sourceRefs": [
      "wiki/course/context/module-2-context.md",
      "wiki/kinetics.md",
      "wiki/.understand-anything/knowledge-graph.json"
    ],
    "sourceGaps": []
  },
  {
    "id": "module-3",
    "title": "Oxidation and Reduction (Redox)",
    "objectives": [
      "Define oxidation and reduction in terms of electrons, oxygen, and hydrogen",
      "Identify oxidation and reduction in example reactions",
      "Relate redox chemistry to catabolism and anabolism in metabolism"
    ],
    "sections": [
      {
        "id": "section-1",
        "title": "Core Concept",
        "content": "Oxidation is the loss of electrons, and reduction is the gain of electrons. The mnemonic OIL RIG captures this: Oxidation Is Loss, Reduction Is Gain. Because electrons that are lost by one atom must be gained by another, oxidation and reduction always occur together — when one atom is oxidized, another must be reduced, forming a redox pair.",
        "sourceRefs": [
          "wiki/course/context/module-3-context.md:21-26"
        ]
      },
      {
        "id": "section-2",
        "title": "Three Ways to Identify Redox Reactions",
        "content": "Redox reactions can be identified three ways. Oxidation corresponds to a gain of oxygen atoms, a loss of hydrogen atoms, or a loss of electrons. Reduction corresponds to the opposite: a loss of oxygen atoms, a gain of hydrogen atoms, or a gain of electrons.",
        "sourceRefs": [
          "wiki/course/context/module-3-context.md:28-34"
        ]
      },
      {
        "id": "section-3",
        "title": "Quick Examples",
        "content": "CH₃CH₃ → H₂C=CH₂ is an oxidation because hydrogens are removed. Fe³⁺ → Fe²⁺ is a reduction because an electron is added. O₂ → H₂O is a reduction because hydrogens are added to O₂. Disulfide bond formation is an oxidation because hydrogens are removed.",
        "sourceRefs": [
          "wiki/course/context/module-3-context.md:38-43"
        ]
      },
      {
        "id": "section-4",
        "title": "Energy Metabolism Context",
        "content": "Photosynthetic organisms (photoautotrophs, such as plants) store solar energy in carbohydrates. Cellular respiration in animals (chemoheterotrophs) oxidizes reduced molecules such as carbohydrates and fats, producing CO₂ and ATP. In glucose oxidation (C₆H₁₂O₆ + 6 O₂ → 6 CO₂ + 6 H₂O), the carbons in glucose are oxidized to CO₂ while oxygen is reduced to H₂O, making carbon and oxygen the redox pair in this reaction.",
        "sourceRefs": [
          "wiki/course/context/module-3-context.md:46-56"
        ]
      },
      {
        "id": "section-5",
        "title": "Catabolism vs. Anabolism",
        "content": "Catabolism is the breaking down of molecules; it is oxidative and releases energy. Anabolism is the building up of molecules; it is reductive and requires energy (ATP). Fatty acid synthesis is an example of anabolism, consisting of successive reductions of the carbon chain. ATP stores energy released from catabolism and uses it to drive anabolism.",
        "sourceRefs": [
          "wiki/course/context/module-3-context.md:58-66"
        ]
      }
    ],
    "equations": [
      {
        "expression": "C₆H₁₂O₆ + 6 O₂ → 6 CO₂ + 6 H₂O",
        "meaning": "Glucose oxidation: carbon in glucose is oxidized to CO₂ while oxygen is reduced to H₂O.",
        "sourceRefs": [
          "wiki/course/context/module-3-context.md:50-56"
        ]
      }
    ],
    "workedExamples": [
      {
        "question": "In the reaction Fe³⁺ → Fe²⁺, is iron oxidized or reduced?",
        "steps": [
          "Compare the charge of iron before and after the reaction: it goes from 3+ to 2+",
          "A decrease in positive charge means iron gained an electron",
          "By OIL RIG, gain of electrons = reduction"
        ],
        "answer": "Iron is reduced, because it gains an electron as its charge decreases from 3+ to 2+.",
        "sourceRefs": [
          "wiki/course/context/module-3-context.md:21-24",
          "wiki/course/context/module-3-context.md:41"
        ]
      },
      {
        "question": "In glucose oxidation (C₆H₁₂O₆ + 6 O₂ → 6 CO₂ + 6 H₂O), which element is oxidized and which is reduced?",
        "steps": [
          "Identify what happens to carbon: glucose's carbons end up in CO₂, having gained oxygen atoms",
          "By the three ways to identify redox reactions, gain of oxygen atoms = oxidation, so carbon is oxidized",
          "Identify what happens to oxygen: O₂ ends up in H₂O, having gained hydrogen atoms",
          "Gain of hydrogen atoms = reduction, so oxygen is reduced",
          "Carbon (oxidized) and oxygen (reduced) form the redox pair in this reaction"
        ],
        "answer": "Carbon is oxidized (to CO₂) and oxygen is reduced (to H₂O).",
        "sourceRefs": [
          "wiki/course/context/module-3-context.md:50-56"
        ]
      }
    ],
    "checks": [
      {
        "question": "Is the following statement true or false? 'Oxidation can occur without a corresponding reduction elsewhere in the reaction.'",
        "answer": "False",
        "explanation": "Electrons lost by one atom (oxidation) must be gained by another atom (reduction); oxidation and reduction always occur together as a redox pair.",
        "sourceRefs": [
          "wiki/course/context/module-3-context.md:26"
        ],
        "reviewTarget": "core concept"
      },
      {
        "question": "Disulfide bond formation involves the loss of hydrogen atoms. Is this an oxidation or a reduction?",
        "answer": "Oxidation",
        "explanation": "Loss of hydrogen atoms is one of the three ways to identify oxidation.",
        "sourceRefs": [
          "wiki/course/context/module-3-context.md:43"
        ],
        "reviewTarget": "three ways to identify redox reactions"
      },
      {
        "question": "Which of the following best describes anabolism?",
        "choices": [
          "Breaking down molecules, oxidative, releases energy",
          "Building up molecules, reductive, requires energy",
          "Breaking down molecules, reductive, requires energy",
          "Building up molecules, oxidative, releases energy"
        ],
        "answer": "Building up molecules, reductive, requires energy",
        "explanation": "Anabolism is the building up of molecules; it is reductive in nature and requires energy input (ATP), as in fatty acid synthesis.",
        "sourceRefs": [
          "wiki/course/context/module-3-context.md:58-66"
        ],
        "reviewTarget": "catabolism vs. anabolism"
      }
    ],
    "practiceQuestions": [
      {
        "question": "Which mnemonic describes the relationship between oxidation and reduction in terms of electrons?",
        "choices": [
          "OIL RIG: Oxidation Is Loss, Reduction Is Gain",
          "OIL RIG: Oxidation Is Gain, Reduction Is Loss",
          "RIG OIL: Reduction Is Gain of oxygen, Oxidation Is Loss of oxygen",
          "There is no mnemonic in the source material"
        ],
        "answer": "OIL RIG: Oxidation Is Loss, Reduction Is Gain",
        "explanation": "OIL RIG stands for Oxidation Is Loss (of electrons), Reduction Is Gain (of electrons).",
        "sourceRefs": [
          "wiki/course/context/module-3-context.md:24"
        ],
        "reviewTarget": "core concept"
      },
      {
        "question": "CH₃CH₃ is converted to H₂C=CH₂ by removing hydrogens. Is this an oxidation or reduction, and why?",
        "answer": "Oxidation, because loss of hydrogen atoms is one of the three ways to identify an oxidation reaction",
        "explanation": "The three ways to identify redox reactions list loss of hydrogen atoms as oxidation.",
        "sourceRefs": [
          "wiki/course/context/module-3-context.md:38-40"
        ],
        "reviewTarget": "quick examples"
      },
      {
        "question": "Which process releases energy: catabolism or anabolism?",
        "choices": [
          "Catabolism, because it is oxidative and breaks molecules down",
          "Anabolism, because it builds molecules up",
          "Both release equal amounts of energy",
          "Neither process involves energy changes"
        ],
        "answer": "Catabolism, because it is oxidative and breaks molecules down",
        "explanation": "Catabolism breaks down molecules, is oxidative, and releases energy; that released energy (via ATP) drives anabolism.",
        "sourceRefs": [
          "wiki/course/context/module-3-context.md:60-66"
        ],
        "reviewTarget": "catabolism vs. anabolism"
      }
    ],
    "sourceRefs": [
      "wiki/course/context/module-3-context.md",
      "wiki/oxidation-reduction.md",
      "wiki/.understand-anything/knowledge-graph.json"
    ],
    "sourceGaps": []
  },
  {
    "id": "module-4",
    "title": "Acids and Bases",
    "objectives": [
      "Apply the Brønsted-Lowry and Lewis definitions of acids and bases",
      "Identify conjugate acid-base pairs in a reaction",
      "Relate K_a/K_b and pK_a/pK_b to acid and base strength",
      "Explain how the bicarbonate buffer system resists pH change in blood"
    ],
    "sections": [
      {
        "id": "section-1",
        "title": "Definitions: Brønsted-Lowry and Lewis",
        "content": "Under the Brønsted-Lowry definition (most important for the MCAT), an acid is a proton (H⁺) donor and a base is a proton (H⁺) acceptor; any anion or neutral species with a lone pair can act as a base. For example, in H₂CO₃ + H₂O ⇌ H₃O⁺ + HCO₃⁻, the acids are H₂CO₃ and H₃O⁺, and the bases are HCO₃⁻ and H₂O. The broader Lewis definition defines an acid as an electron-pair acceptor and a base as an electron-pair donor, forming a coordinate covalent bond. In the heme group, O₂ binds to Fe²⁺: O₂ donates an electron pair and is the Lewis base, while Fe²⁺ accepts the electron pair and is the Lewis acid.",
        "sourceRefs": [
          "wiki/course/context/module-4-context.md:21-40"
        ]
      },
      {
        "id": "section-2",
        "title": "Conjugate Acid-Base Pairs",
        "content": "A conjugate base is an acid minus H⁺, and a conjugate acid is a base plus H⁺. In NH₃ + H₂O ⇌ NH₄⁺ + OH⁻, considered in the forward direction, NH₃ is the base and H₂O is the acid; NH₄⁺ is the conjugate acid of NH₃, and OH⁻ is the conjugate base of H₂O. Considered in the reverse direction, NH₄⁺ is the acid and OH⁻ is the base; NH₃ is the conjugate base of NH₄⁺, and H₂O is the conjugate acid of OH⁻.",
        "sourceRefs": [
          "wiki/course/context/module-4-context.md:44-59"
        ]
      },
      {
        "id": "section-3",
        "title": "Acid/Base Strength",
        "content": "For the acid dissociation HA + H₂O ⇌ H₃O⁺ + A⁻, the acid dissociation constant is K_a = [H₃O⁺][A⁻] / [HA]; a larger K_a means a stronger acid, and since pK_a = –log K_a, a lower pK_a means a stronger acid. For the base dissociation B + H₂O ⇌ HB⁺ + OH⁻, the base dissociation constant is K_b = [HB⁺][OH⁻] / [B]; a larger K_b means a stronger base, and since pK_b = –log K_b, a lower pK_b means a stronger base.",
        "sourceRefs": [
          "wiki/course/context/module-4-context.md:63-79"
        ]
      },
      {
        "id": "section-4",
        "title": "Amphoteric Substances",
        "content": "Amphoteric substances can act as both an acid and a base. The conjugate base of a weak polyprotic acid is always amphoteric. Bicarbonate (HCO₃⁻) is an example: as a base, HCO₃⁻ + H₂O ⇌ H₂CO₃ + OH⁻; as an acid, HCO₃⁻ + H₂O ⇌ CO₃²⁻ + H₃O⁺. Amino acids are all amphoteric.",
        "sourceRefs": [
          "wiki/course/context/module-4-context.md:81-87"
        ]
      },
      {
        "id": "section-5",
        "title": "pH and pOH",
        "content": "pH = –log[H⁺] (equivalently –log[H₃O⁺]), so [H⁺] = 10^(–pH). Pure water has [H⁺] = 10⁻⁷ M, giving a neutral pH of 7 at 25°C. A pH below 7 is acidic, a pH of 7 is neutral, and a pH above 7 is basic. Similarly, pOH = –log[OH⁻], so [OH⁻] = 10^(–pOH). At 25°C, pH + pOH = 14.",
        "sourceRefs": [
          "wiki/course/context/module-4-context.md:91-103"
        ]
      },
      {
        "id": "section-6",
        "title": "Buffer Solutions and the Bicarbonate Buffer System",
        "content": "A buffer resists pH change when small amounts of acid or base are added; it contains a weak acid plus its conjugate base (or a weak base plus its conjugate acid) in roughly equal concentrations. The bicarbonate buffer system is the most important buffer in blood, involving Reaction 1: H₂CO₃ ⇌ H⁺ + HCO₃⁻, and Reaction 2: CO₂ + H₂O ⇌ H₂CO₃. During exercise, muscles produce lactic acid, increasing H⁺; by Le Châtelier's principle, Reaction 1 shifts left, reducing free H⁺ and minimizing the pH drop. When holding one's breath, CO₂ accumulates, shifting Reaction 2 right to produce more H₂CO₃, which produces more H⁺, so pH decreases.",
        "sourceRefs": [
          "wiki/course/context/module-4-context.md:107-121"
        ]
      },
      {
        "id": "section-7",
        "title": "Quick Reference: Acid and Base Strength",
        "content": "A stronger acid has a larger K_a and a lower pK_a; a stronger base has a larger K_b and a lower pK_b. A stronger acid corresponds to a lower pH. For example, lactic acid (pK_a = 3.9) is a stronger acid than uric acid (pK_a = 5.6). The lowest [H₃O⁺] corresponds to the highest pH, as in seawater (pH 8.5). The least acidic substance has the highest pK_a, as with bicarbonate (pK_a = 10.33).",
        "sourceRefs": [
          "wiki/course/context/module-4-context.md:125-134"
        ]
      }
    ],
    "equations": [
      {
        "expression": "K_a = [H₃O⁺][A⁻] / [HA]",
        "meaning": "Acid dissociation constant; a larger K_a indicates a stronger acid.",
        "sourceRefs": [
          "wiki/course/context/module-4-context.md:66"
        ]
      },
      {
        "expression": "pK_a = –log K_a",
        "meaning": "Converts the acid dissociation constant to pK_a; a lower pK_a indicates a stronger acid.",
        "sourceRefs": [
          "wiki/course/context/module-4-context.md:69-70"
        ]
      },
      {
        "expression": "K_b = [HB⁺][OH⁻] / [B]",
        "meaning": "Base dissociation constant; a larger K_b indicates a stronger base.",
        "sourceRefs": [
          "wiki/course/context/module-4-context.md:75"
        ]
      },
      {
        "expression": "pK_b = –log K_b",
        "meaning": "Converts the base dissociation constant to pK_b; a lower pK_b indicates a stronger base.",
        "sourceRefs": [
          "wiki/course/context/module-4-context.md:78-79"
        ]
      },
      {
        "expression": "pH = –log[H⁺]",
        "meaning": "Defines pH from hydrogen ion concentration.",
        "sourceRefs": [
          "wiki/course/context/module-4-context.md:91"
        ]
      },
      {
        "expression": "pH + pOH = 14",
        "meaning": "Relationship between pH and pOH at 25°C.",
        "sourceRefs": [
          "wiki/course/context/module-4-context.md:103"
        ]
      }
    ],
    "workedExamples": [
      {
        "question": "In the reaction NH₃ + H₂O ⇌ NH₄⁺ + OH⁻ (forward direction), identify the acid, base, conjugate acid, and conjugate base.",
        "steps": [
          "Identify the proton donor and acceptor in the forward direction: H₂O donates a proton, so H₂O is the acid; NH₃ accepts a proton, so NH₃ is the base",
          "The conjugate acid is the base plus H⁺: NH₃ + H⁺ = NH₄⁺, so NH₄⁺ is the conjugate acid of NH₃",
          "The conjugate base is the acid minus H⁺: H₂O – H⁺ = OH⁻, so OH⁻ is the conjugate base of H₂O"
        ],
        "answer": "H₂O is the acid, NH₃ is the base, NH₄⁺ is the conjugate acid of NH₃, and OH⁻ is the conjugate base of H₂O.",
        "sourceRefs": [
          "wiki/course/context/module-4-context.md:48-54"
        ]
      },
      {
        "question": "Lactic acid has a pK_a of 3.9 and uric acid has a pK_a of 5.6. Which is the stronger acid?",
        "steps": [
          "Recall that a lower pK_a indicates a stronger acid",
          "Compare the two pK_a values: 3.9 (lactic acid) is lower than 5.6 (uric acid)",
          "Therefore lactic acid is the stronger acid"
        ],
        "answer": "Lactic acid is the stronger acid because it has the lower pK_a (3.9 vs. 5.6).",
        "sourceRefs": [
          "wiki/course/context/module-4-context.md:70",
          "wiki/course/context/module-4-context.md:132"
        ]
      }
    ],
    "checks": [
      {
        "question": "Is the following statement true or false? 'Under the Lewis definition, an acid donates an electron pair.'",
        "answer": "False",
        "explanation": "Under the Lewis definition, an acid is an electron-pair acceptor, not a donor; the base is the electron-pair donor.",
        "sourceRefs": [
          "wiki/course/context/module-4-context.md:34-36"
        ],
        "reviewTarget": "definitions: Brønsted-Lowry and Lewis"
      },
      {
        "question": "What makes a substance amphoteric, and what is one example given in the source material?",
        "answer": "An amphoteric substance can act as both an acid and a base; bicarbonate (HCO₃⁻) is the given example",
        "explanation": "The source states the conjugate base of a weak polyprotic acid is always amphoteric, and gives HCO₃⁻ as an example that can act as either acid or base.",
        "sourceRefs": [
          "wiki/course/context/module-4-context.md:81-86"
        ],
        "reviewTarget": "amphoteric substances"
      },
      {
        "question": "During exercise, lactic acid increases H⁺ in the blood. According to the source, what happens to Reaction 1 of the bicarbonate buffer (H₂CO₃ ⇌ H⁺ + HCO₃⁻)?",
        "choices": [
          "It shifts right, producing more H⁺",
          "It shifts left, reducing free H⁺",
          "It stops entirely",
          "It is unaffected by lactic acid"
        ],
        "answer": "It shifts left, reducing free H⁺",
        "explanation": "By Le Châtelier's principle, increased H⁺ from lactic acid shifts Reaction 1 left, which reduces free H⁺ and minimizes the pH drop.",
        "sourceRefs": [
          "wiki/course/context/module-4-context.md:117-119"
        ],
        "reviewTarget": "buffer solutions and the bicarbonate buffer system"
      },
      {
        "question": "A solution has [H⁺] = 10⁻³ M. Is it acidic, neutral, or basic?",
        "answer": "Acidic",
        "explanation": "[H⁺] = 10⁻³ M corresponds to pH = 3, which is below 7, and a pH below 7 is classified as acidic.",
        "sourceRefs": [
          "wiki/course/context/module-4-context.md:91-98"
        ],
        "reviewTarget": "pH and pOH"
      }
    ],
    "practiceQuestions": [
      {
        "question": "Which definition of acids and bases is described as most important for the MCAT in the source material?",
        "choices": [
          "Lewis",
          "Brønsted-Lowry",
          "Arrhenius",
          "None are emphasized over the others"
        ],
        "answer": "Brønsted-Lowry",
        "explanation": "The source explicitly labels the Brønsted-Lowry definition as 'Most important for MCAT.'",
        "sourceRefs": [
          "wiki/course/context/module-4-context.md:21"
        ],
        "reviewTarget": "definitions: Brønsted-Lowry and Lewis"
      },
      {
        "question": "If K_a for acid X is larger than K_a for acid Y, which acid is stronger?",
        "answer": "Acid X, because a larger K_a indicates a stronger acid",
        "explanation": "The source states that a larger K_a corresponds to a stronger acid.",
        "sourceRefs": [
          "wiki/course/context/module-4-context.md:68"
        ],
        "reviewTarget": "acid/base strength"
      },
      {
        "question": "What two components must a buffer solution contain in roughly equal concentrations?",
        "choices": [
          "A strong acid and a strong base",
          "A weak acid and its conjugate base (or a weak base and its conjugate acid)",
          "Only water and a salt",
          "Two strong acids"
        ],
        "answer": "A weak acid and its conjugate base (or a weak base and its conjugate acid)",
        "explanation": "The source defines a buffer as containing a weak acid plus conjugate base (or weak base plus conjugate acid) in roughly equal concentrations.",
        "sourceRefs": [
          "wiki/course/context/module-4-context.md:107-109"
        ],
        "reviewTarget": "buffer solutions and the bicarbonate buffer system"
      },
      {
        "question": "Seawater has a pH of 8.5. What does this imply about its [H₃O⁺] relative to a solution with a lower pH?",
        "answer": "Seawater has a lower [H₃O⁺] than the more acidic solution, since the source states the lowest [H₃O⁺] corresponds to the highest pH",
        "explanation": "pH is inversely related to [H₃O⁺]; the source gives seawater's pH of 8.5 as an example of the lowest [H₃O⁺] corresponding to the highest pH among its examples.",
        "sourceRefs": [
          "wiki/course/context/module-4-context.md:133"
        ],
        "reviewTarget": "quick reference: acid and base strength"
      }
    ],
    "sourceRefs": [
      "wiki/course/context/module-4-context.md",
      "wiki/acids-bases.md",
      "wiki/.understand-anything/knowledge-graph.json"
    ],
    "sourceGaps": []
  },
  {
    "id": "module-5",
    "title": "Chapter 3: Biochemistry Basics — Summary",
    "objectives": [
      "Recall the key equations from thermodynamics, kinetics, redox, and acid/base chemistry covered in Chapter 3",
      "Connect high-yield facts across the four major topics into one review",
      "Use the chapter summary to identify which prior module to revisit for a given fact"
    ],
    "sections": [
      {
        "id": "section-1",
        "title": "Overview",
        "content": "This chapter covers foundational biochemistry concepts tested on the MCAT: thermodynamics, kinetics, redox reactions, and acid/base chemistry. The source material for this chapter is the Princeton Review MCAT Biochemistry Review, Chapter 3.",
        "sourceRefs": [
          "wiki/course/context/module-5-context.md:20",
          "wiki/course/context/module-5-context.md:99"
        ]
      },
      {
        "id": "section-2",
        "title": "Major Topics Recap",
        "content": "Thermodynamics: Gibbs free energy is ∆G = ∆H – T∆S; ∆G < 0 is spontaneous (exergonic) and ∆G > 0 is nonspontaneous (endergonic); standard free energy is ∆G°′ = –RT ln K'_eq (at pH 7, 1 M solutes); actual cellular ∆G = ∆G°′ + RT ln Q; Le Châtelier's principle governs how Q versus K_eq drives reaction direction; two factors determine spontaneity in cells — intrinsic properties (K_eq) and concentrations (RT ln Q). Kinetics: thermodynamics is not the same as kinetics, since ∆G says nothing about rate; activation energy (E_a) is the barrier to reaching the transition state [TS]‡; catalysts and enzymes lower E_a by stabilizing the transition state but do not change ∆G or K_eq; enzymes are biological catalysts with a kinetic role only. Oxidation-reduction: oxidation is loss of electrons/hydrogen or gain of oxygen, reduction is gain of electrons/hydrogen or loss of oxygen; redox pairs always have one species oxidized and one reduced; in metabolism, catabolism is oxidative and releases energy while anabolism is reductive and requires ATP; glucose oxidation is C₆H₁₂O₆ + 6 O₂ → 6 CO₂ + 6 H₂O. Acids and bases: under Brønsted-Lowry, an acid is an H⁺ donor and a base is an H⁺ acceptor; under Lewis, an acid is an electron-pair acceptor and a base is an electron-pair donor; conjugate pairs differ by one H⁺; a lower pK_a means a stronger acid and a lower pK_b means a stronger base; amphoteric substances (such as HCO₃⁻ and amino acids) can act as either acid or base; pH = –log[H⁺] and pH + pOH = 14 at 25°C; buffers contain a weak acid plus its conjugate base to resist pH change; the bicarbonate buffer (CO₂ + H₂O ⇌ H₂CO₃ ⇌ H⁺ + HCO₃⁻) is key in blood.",
        "sourceRefs": [
          "wiki/course/context/module-5-context.md:26-55"
        ]
      },
      {
        "id": "section-3",
        "title": "High-Yield Facts for MCAT",
        "content": "ATP is the primary energy currency, storing energy in high-energy phosphate bonds. ∆G < 0 means spontaneous, and ∆G = 0 means equilibrium. Enzymes lower activation energy (E_a) but do not change ∆G or K_eq. Catalysts speed up both forward and reverse reactions equally. Redox reactions follow the mnemonic OIL RIG (Oxidation Is Loss, Reduction Is Gain). A lower pK_a means a stronger acid, and a higher pK_a means a weaker acid (more basic). The bicarbonate buffer is the main blood buffer, and CO₂ accumulation causes pH to drop. Amphoteric substances such as HCO₃⁻ and amino acids can either donate or accept H⁺.",
        "sourceRefs": [
          "wiki/course/context/module-5-context.md:75-82"
        ]
      }
    ],
    "equations": [
      {
        "expression": "∆G = ∆H – T∆S",
        "meaning": "Thermodynamic spontaneity equation, relating free energy, enthalpy, and entropy.",
        "sourceRefs": [
          "wiki/course/context/module-5-context.md:63"
        ]
      },
      {
        "expression": "∆G°′ = –RT ln K'_eq",
        "meaning": "Relates standard free energy change to the equilibrium constant.",
        "sourceRefs": [
          "wiki/course/context/module-5-context.md:64"
        ]
      },
      {
        "expression": "∆G = ∆G°′ + RT ln Q",
        "meaning": "Gives the actual cellular ∆G from standard free energy and the reaction quotient.",
        "sourceRefs": [
          "wiki/course/context/module-5-context.md:65"
        ]
      },
      {
        "expression": "pH = –log[H⁺]",
        "meaning": "Defines acidity in terms of hydrogen ion concentration.",
        "sourceRefs": [
          "wiki/course/context/module-5-context.md:66"
        ]
      },
      {
        "expression": "pH + pOH = 14",
        "meaning": "Acid-base relationship at 25°C.",
        "sourceRefs": [
          "wiki/course/context/module-5-context.md:67"
        ]
      },
      {
        "expression": "pK_a = –log K_a",
        "meaning": "Converts the acid dissociation constant into pK_a, a measure of acid strength.",
        "sourceRefs": [
          "wiki/course/context/module-5-context.md:68"
        ]
      },
      {
        "expression": "pK_b = –log K_b",
        "meaning": "Converts the base dissociation constant into pK_b, a measure of base strength.",
        "sourceRefs": [
          "wiki/course/context/module-5-context.md:69"
        ]
      }
    ],
    "workedExamples": [
      {
        "question": "Using the chapter's high-yield facts, if an enzyme is added to a reaction, what happens to ∆G and K_eq?",
        "steps": [
          "Recall the high-yield fact: enzymes lower E_a but do not change ∆G or K_eq",
          "An enzyme is a biological catalyst, and catalysts have a purely kinetic role",
          "Therefore adding the enzyme leaves ∆G and K_eq unchanged"
        ],
        "answer": "Neither ∆G nor K_eq changes; the enzyme only lowers the activation energy and increases the rate.",
        "sourceRefs": [
          "wiki/course/context/module-5-context.md:77"
        ]
      }
    ],
    "checks": [
      {
        "question": "Is the following statement true or false, according to the chapter summary? 'Catalysts speed up the forward reaction more than the reverse reaction.'",
        "answer": "False",
        "explanation": "The chapter summary states catalysts speed up both forward and reverse reactions equally.",
        "sourceRefs": [
          "wiki/course/context/module-5-context.md:78"
        ],
        "reviewTarget": "high-yield facts for MCAT"
      },
      {
        "question": "According to the high-yield facts, what happens to pH when CO₂ accumulates in the blood?",
        "answer": "pH drops",
        "explanation": "The chapter summary states the bicarbonate buffer is the main blood buffer and CO₂ accumulation causes pH to drop.",
        "sourceRefs": [
          "wiki/course/context/module-5-context.md:81"
        ],
        "reviewTarget": "high-yield facts for MCAT"
      },
      {
        "question": "Which two substances are given in the chapter summary as examples of amphoteric substances?",
        "choices": [
          "HCO₃⁻ and amino acids",
          "Glucose and ATP",
          "H₂O and OH⁻ only",
          "CO₂ and O₂"
        ],
        "answer": "HCO₃⁻ and amino acids",
        "explanation": "The summary lists HCO₃⁻ and amino acids as examples of amphoteric substances that can donate or accept H⁺.",
        "sourceRefs": [
          "wiki/course/context/module-5-context.md:82"
        ],
        "reviewTarget": "high-yield facts for MCAT"
      }
    ],
    "practiceQuestions": [
      {
        "question": "According to the chapter summary's Major Topics, which equation governs the actual free energy change in a cell?",
        "choices": [
          "∆G = ∆H – T∆S",
          "∆G°′ = –RT ln K'_eq",
          "∆G = ∆G°′ + RT ln Q",
          "pH = –log[H⁺]"
        ],
        "answer": "∆G = ∆G°′ + RT ln Q",
        "explanation": "The Major Topics section lists 'Actual cellular ∆G: ∆G = ∆G°′ + RT ln Q' under thermodynamics.",
        "sourceRefs": [
          "wiki/course/context/module-5-context.md:30"
        ],
        "reviewTarget": "major topics recap"
      },
      {
        "question": "Per the chapter summary, what two factors determine spontaneity of a reaction in a cell?",
        "answer": "Intrinsic properties (K_eq) and concentrations (RT ln Q)",
        "explanation": "The Major Topics section under thermodynamics states this is the key takeaway: two factors determine spontaneity in cells.",
        "sourceRefs": [
          "wiki/course/context/module-5-context.md:32"
        ],
        "reviewTarget": "major topics recap"
      },
      {
        "question": "What is the source cited for this chapter's content?",
        "answer": "Princeton Review MCAT Biochemistry Review, Chapter 3",
        "explanation": "The article explicitly cites this as its source at the end of the chapter summary.",
        "sourceRefs": [
          "wiki/course/context/module-5-context.md:99"
        ],
        "reviewTarget": "overview"
      }
    ],
    "sourceRefs": [
      "wiki/course/context/module-5-context.md",
      "wiki/chapter-3-summary.md",
      "wiki/.understand-anything/knowledge-graph.json"
    ],
    "sourceGaps": []
  }
];
