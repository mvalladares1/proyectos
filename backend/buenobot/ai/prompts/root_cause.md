# BUENOBOT v3.0 - Root Cause Analysis Prompt

You are performing root cause analysis on security and quality findings.

## Your Task

Analyze the provided findings and identify underlying root causes:
1. Group related findings that share common causes
2. Identify systemic issues vs isolated problems
3. Trace each finding to its likely origin
4. Suggest preventive measures

## Input Evidence

```
{evidence}
```

## Output Format (JSON)

```json
{
    "root_causes": [
        {
            "cause": "Brief description",
            "category": "security|architecture|testing|process|knowledge",
            "evidence_ids": ["finding_1", "finding_2"],
            "affected_components": ["component1", "component2"],
            "explanation": "Detailed technical explanation",
            "preventive_measures": ["measure1", "measure2"]
        }
    ],
    "patterns_detected": [
        {
            "pattern": "Pattern name",
            "frequency": "how often it appears",
            "examples": ["example1", "example2"]
        }
    ],
    "systemic_vs_isolated": {
        "systemic_issues": ["issue1", "issue2"],
        "isolated_issues": ["issue3"]
    }
}
```

## Guidelines

- Look for patterns across multiple findings
- Consider codebase architecture and team practices
- Distinguish between symptoms and causes
- Prioritize systemic fixes over point solutions
