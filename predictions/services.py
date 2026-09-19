from dataclasses import dataclass
@dataclass
class ProbabilityResult:
    probability: float
    confidence: float
    rationale: dict

def baseline_corner_probability(avg_for: float, avg_against: float, line: float) -> ProbabilityResult:
    """Placeholder estatístico inicial; será substituído pelo ensemble calibrado após ingestão histórica."""
    expected=max(0.1,(avg_for+avg_against)/2)
    distance=expected-line
    probability=max(5.0,min(95.0,50.0 + distance*8.0))
    confidence=min(85.0,40.0 + abs(distance)*5.0)
    return ProbabilityResult(round(probability,2),round(confidence,2),{'expected_corners':round(expected,2),'line':line})
