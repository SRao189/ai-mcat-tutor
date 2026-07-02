window.PUBLIC_COURSE_PREVIEW = [
  {
    id: "module-1",
    order: "01",
    title: "Thermodynamics",
    sections: 5,
    workedExamples: 2,
    practiceQuestions: 2,
    checks: 2,
    summary: "Energy forms, entropy, Gibbs free energy, equilibrium, and reaction direction under cellular conditions.",
    firstSection: {
      title: "Key Concepts",
      content: "Energy exists in two primary forms: kinetic energy and potential energy. In biological systems, ATP stores potential energy in its phosphate bonds."
    },
    workedExample: {
      question: "Can delta G be negative if delta G degrees prime is positive?",
      answer: "Yes. If RT ln Q is sufficiently negative, the overall delta G can still become negative."
    },
    practice: {
      question: "Which relationship best describes delta G, delta G degrees prime, and Q?",
      choices: [
        "delta G = delta G degrees prime + RT ln K_eq",
        "delta G = delta G degrees prime + RT ln Q",
        "delta G degrees prime = delta G + RT ln Q",
        "Q = delta G degrees prime + RT ln delta G"
      ],
      answerIndex: 1
    }
  },
  {
    id: "module-2",
    order: "02",
    title: "Kinetics and Activation Energy",
    sections: 4,
    workedExamples: 1,
    practiceQuestions: 3,
    checks: 3,
    summary: "Reaction rates, activation barriers, transition states, catalysts, and why spontaneous does not mean fast.",
    firstSection: {
      title: "Thermodynamics vs. Kinetics",
      content: "Thermodynamics describes whether a reaction is favorable and where it ends. Kinetics describes how fast it happens and whether activation energy blocks it."
    },
    workedExample: {
      question: "Why does wood not combust at room temperature if burning has a negative delta G?",
      answer: "Because the reaction still has an activation energy barrier. A match supplies the initial energy needed to start it."
    },
    practice: {
      question: "Which statement best distinguishes thermodynamics from kinetics?",
      choices: [
        "Thermodynamics gives rate and kinetics gives spontaneity",
        "Thermodynamics gives spontaneity and endpoint, kinetics gives rate",
        "They both measure the same thing",
        "Thermodynamics only applies to enzymes"
      ],
      answerIndex: 1
    }
  },
  {
    id: "module-3",
    order: "03",
    title: "Oxidation and Reduction (Redox)",
    sections: 5,
    workedExamples: 2,
    practiceQuestions: 3,
    checks: 3,
    summary: "Electron transfer, oxidation states, mnemonic reasoning, and redox in metabolism.",
    firstSection: {
      title: "Core Concept",
      content: "Oxidation is loss of electrons and reduction is gain of electrons. These always occur together because electrons lost by one species are gained by another."
    },
    workedExample: {
      question: "In Fe3+ to Fe2+, is iron oxidized or reduced?",
      answer: "Reduced. The charge decreases from 3+ to 2+, meaning iron gains an electron."
    },
    practice: {
      question: "Which mnemonic correctly captures oxidation and reduction?",
      choices: [
        "OIL RIG: Oxidation Is Loss, Reduction Is Gain",
        "OIL RIG: Oxidation Is Gain, Reduction Is Loss",
        "RIG OIL: Reduction Is Gain of oxygen",
        "There is no mnemonic"
      ],
      answerIndex: 0
    }
  },
  {
    id: "module-4",
    order: "04",
    title: "Acids and Bases",
    sections: 7,
    workedExamples: 2,
    practiceQuestions: 4,
    checks: 4,
    summary: "Bronsted-Lowry and Lewis definitions, conjugate pairs, buffers, pH, and acid-base strength.",
    firstSection: {
      title: "Definitions",
      content: "For MCAT work, the Bronsted-Lowry definition matters most: acids donate protons and bases accept protons. The Lewis model expands that to electron-pair donation and acceptance."
    },
    workedExample: {
      question: "In NH3 + H2O reversible NH4+ + OH-, identify acid, base, conjugate acid, and conjugate base.",
      answer: "H2O is the acid, NH3 is the base, NH4+ is the conjugate acid, and OH- is the conjugate base."
    },
    practice: {
      question: "Which acid-base definition is emphasized as most important for the MCAT?",
      choices: [
        "Lewis",
        "Bronsted-Lowry",
        "Arrhenius",
        "None are emphasized"
      ],
      answerIndex: 1
    }
  },
  {
    id: "module-5",
    order: "05",
    title: "Biochemistry Basics Summary",
    sections: 3,
    workedExamples: 1,
    practiceQuestions: 3,
    checks: 3,
    summary: "A chapter-level recap of thermodynamics, kinetics, redox, and acid-base chemistry.",
    firstSection: {
      title: "Overview",
      content: "This chapter consolidates high-yield biochemistry ideas tested on the MCAT, including free energy, activation energy, redox logic, and acid-base chemistry."
    },
    workedExample: {
      question: "If an enzyme is added to a reaction, what happens to delta G and K_eq?",
      answer: "Neither changes. The enzyme lowers activation energy and increases rate without changing thermodynamic state."
    },
    practice: {
      question: "Which equation governs the actual free energy change in a cell?",
      choices: [
        "delta G = delta H - T delta S",
        "delta G degrees prime = -RT ln K_eq",
        "delta G = delta G degrees prime + RT ln Q",
        "pH = -log[H+]"
      ],
      answerIndex: 2
    }
  }
];
