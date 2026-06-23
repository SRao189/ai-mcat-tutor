{
  "audit": [
    {
      "json_location": "module-1.sections[0].content",
      "claim": "The most important potential energy storage molecule in biological systems is ATP, with energy stored in the ester bonds between its phosphate groups.",
      "status": "unsupported",
      "why_not_supported": "The source states that ATP stores energy in 'ester bonds between phosphate groups,' but this is chemically inaccurate. ATP's high-energy bonds are phosphoanhydride bonds (between phosphate groups), not ester bonds. Ester bonds are found in molecules like phospholipids or acetyl-CoA, not between phosphate groups in ATP. The source contains this error and does not correct it.",
      "closest_source_evidence": "wiki/thermodynamics.md: 'Most important potential energy storage molecule: ATP (energy in ester bonds between phosphate groups)'",
      "required_correction": "Change 'ester bonds' to 'phosphoanhydride bonds' to reflect accurate biochemistry. Alternatively, if the source is to be strictly followed, the claim must be marked as unsupported due to factual inaccuracy."
    },
    {
      "json_location": "module-1.sections[3].content",
      "claim": "K'_eq is the equilibrium constant calculated as [C]^c[D]^d / [A]^a[B]^b at equilibrium.",
      "status": "partially supported",
      "why_not_supported": "The source uses K'_eq and defines it with the same notation as K_eq, but does not explicitly define the prime (') as indicating biochemical standard conditions (pH 7, 1 M solutes except H⁺). The notation K'_eq is introduced without explanation in the source, and while the biochemical standard is defined for ∆G°′, the link between the prime symbol and the definition of K'_eq is implied but not explicitly stated in the equation context.",
      "closest_source_evidence": "wiki/thermodynamics.md: 'K'_eq = [C]^c[D]^d / [A]^a[B]^b at equilibrium' and '∆G°′ — biochemical standard: 1 M all solutes except H⁺, pH 7'",
      "required_correction": "Clarify in the content that K'_eq is the equilibrium constant under biochemical standard conditions (pH 7, 1 M solutes except H⁺), to align with the definition of ∆G°′. Add: 'K'_eq is the equilibrium constant under biochemical standard conditions (pH 7, 1 M solutes except H⁺)'"
    },
    {
      "json_location": "module-1.sections[4].content",
      "claim": "When Q < K_eq, ∆G < 0 and the forward reaction is spontaneous. When Q > K_eq, ∆G > 0 and the reverse reaction is spontaneous. When Q = K_eq, ∆G = 0 and the system is at equilibrium.",
      "status": "partially supported",
      "why_not_supported": "The source uses both K_eq and K'_eq inconsistently. In the Gibbs Free Energy section, it defines K'_eq for standard conditions. In the Reaction Quotient section, it writes 'Q < K_eq' without the prime. This creates ambiguity: is K_eq here the same as K'_eq? The source does not clarify whether K_eq in the Q comparison refers to the biochemical standard equilibrium constant (K'_eq) or a general equilibrium constant. This inconsistency undermines precision.",
      "closest_source_evidence": "wiki/thermodynamics.md: 'Q < K_eq → ∆G < 0' and earlier 'K'_eq = [C]^c[D]^d / [A]^a[B]^b at equilibrium'",
      "required_correction": "Replace all instances of 'K_eq' in the Q section with 'K'_eq' to maintain consistency with the biochemical standard notation established for ∆G°′. Clarify that K'_eq is the equilibrium constant under biochemical standard conditions."
    },
    {
      "json_location": "module-1.workedExamples[1].answer",
      "claim": "The reaction shifts forward to consume the added reactant.",
      "status": "partially supported",
      "why_not_supported": "The source supports Le Châtelier’s principle as 'Adding reactants (Q < K) drives forward', but uses 'K' without the prime. The source does not specify whether 'K' here refers to K_eq or K'_eq. In a cellular context, the relevant equilibrium constant is K'_eq (biochemical standard), but the source does not explicitly tie the principle to K'_eq in this context. The answer assumes K_eq = K'_eq without justification.",
      "closest_source_evidence": "wiki/thermodynamics.md: 'Le Châtelier's principle: Adding reactants (Q < K) drives forward; adding products (Q > K) drives backward'",
      "required_correction": "Clarify that 'K' in Le Châtelier’s principle refers to K'_eq (the biochemical standard equilibrium constant), to align with the ∆G°′ framework. Change to: 'Adding reactants (Q < K'_eq) drives forward.'"
    },
    {
      "json_location": "module-1.checks[0].explanation",
      "claim": "∆G < 0 indicates a spontaneous (thermodynamically favorable) reaction, but says nothing about the reaction rate. Kinetics (activation energy) determines speed, not thermodynamics.",
      "status": "partially supported",
      "why_not_supported": "While the source states that ∆G says nothing about rate (in 'Key Questions Answered': 'Does K_eq indicate reaction rate? No'), it does not explicitly mention 'activation energy' or 'kinetics' in the thermodynamics section. The term 'kinetics' is referenced in the 'See also' and in the knowledge graph, but the thermodynamics article itself does not define or mention activation energy. The explanation introduces 'kinetics (activation energy)' as a concept not defined in the source article.",
      "closest_source_evidence": "wiki/thermodynamics.md: 'Does K_eq indicate reaction rate? No — only relative concentrations at equilibrium'",
      "required_correction": "Remove reference to 'activation energy' and 'kinetics' as defined terms. Instead, say: '∆G < 0 indicates a spontaneous reaction, but says nothing about how fast it occurs.'"
    }
  ],
  "summary": "Five claims are flagged: one unsupported (ATP ester bonds), three partially supported (K'_eq notation inconsistency, K_eq vs K'_eq ambiguity in Q analysis, Le Châtelier’s K ambiguity), and one partially supported due to introduction of external terminology (activation energy). The module relies on source content that contains internal inconsistencies and inaccuracies. Corrections must align strictly with source wording while resolving ambiguities."
}
