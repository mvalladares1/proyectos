# BUENOBOT v3.0 - Output Contract Definitions

# This directory contains YAML contract definitions for API endpoints.
# These contracts define:
# - Expected response schema
# - Business rules validation
# - Performance expectations
# - Security requirements

# How to add a new contract:
# 1. Create a new YAML file named after the endpoint (e.g., recepciones_mp.yaml)
# 2. Define the endpoint, method, and expected schema
# 3. Add business rules with severity levels
# 4. The OutputContractCheck will validate responses against these contracts

# Contract structure:
# ```yaml
# endpoint: /api/v1/endpoint/
# method: GET
# description: Brief description
# 
# response:
#   type: object|array
#   required: [field1, field2]
#   properties:
#     field1:
#       type: string|integer|number|boolean
#       enum: [val1, val2]  # optional
#       pattern: "regex"     # optional
#       minimum: 0           # optional for numbers
# 
# rules:
#   - name: rule_name
#     description: What this rule validates
#     severity: critical|high|medium|low
#     check: |
#       Python expression that evaluates to True if valid
# 
# performance:
#   max_response_time_ms: 5000
# 
# security:
#   - name: security_requirement
#     severity: critical
#     note: Additional context
# ```

# Severity levels:
# - critical: Fails the gate immediately (potential data leak or security issue)
# - high: Fails the gate (requires immediate attention)
# - medium: Warning only
# - low: Informational
