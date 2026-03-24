# Token Counts for Each Summary Category

## Overview

This document provides the **maximum token limits** allocated to each summary category in the LLM generation system.

---

## Token Allocation by Category

### 1. **Observations Summary**
- **Base Tokens:** 2,500 tokens
- **Purpose:** Lists all lab values, vital signs, and measurements with ranges
- **Reasoning:** Needs maximum space because it lists many individual observation values
- **Priority:** HIGHEST - Most data-dense category

### 2. **Patient Summary**
- **Base Tokens:** 1,000 tokens
- **Purpose:** Comprehensive overview of all patient data
- **Reasoning:** Combines demographics, conditions, observations, and notes into coherent narrative
- **Priority:** VERY HIGH - Synthesizes all information

### 3. **Care Plans**
- **Base Tokens:** 700 tokens
- **Purpose:** Care plan suggestions and recommendations
- **Reasoning:** Needs substantial space for structured recommendations
- **Priority:** HIGH - Structured output requires clarity

### 4. **Default (Any Other Category)**
- **Base Tokens:** 600 tokens
- **Purpose:** Fallback for unknown category types
- **Priority:** MEDIUM

### 5. **Conditions Summary**
- **Base Tokens:** 500 tokens
- **Purpose:** List of medical conditions
- **Reasoning:** Typically concise - conditions are descriptive but not lengthy
- **Priority:** MEDIUM

### 6. **Notes Summary**
- **Base Tokens:** 500 tokens
- **Purpose:** Summary of clinical notes
- **Reasoning:** Moderate space needed for summarizing clinical documentation
- **Priority:** MEDIUM

### 7. **Demographics**
- **Base Tokens:** 300 tokens
- **Purpose:** Basic patient demographics
- **Reasoning:** Very short output - just name, age, gender, location
- **Priority:** LOW - Minimal data

---

## Table Summary

| Category | Base Tokens | Max Tokens | Data Density | Priority |
|----------|-------------|------------|--------------|----------|
| **Observations** | 2,500 | 800* | Very High | HIGHEST |
| **Patient Summary** | 1,000 | 800* | High | VERY HIGH |
| **Care Plans** | 700 | 700 | Medium-High | HIGH |
| **Default** | 600 | 600 | Medium | MEDIUM |
| **Conditions** | 500 | 500 | Medium | MEDIUM |
| **Notes** | 500 | 500 | Medium | MEDIUM |
| **Demographics** | 300 | 300 | Low | LOW |

\* *Observations and Patient Summary are limited to 800 tokens by the global MAX_NEW_TOKENS setting*

---

## How Token Limits Are Applied

### Step 1: Category Detection
The system analyzes the user prompt to detect the category:
```python
if "TASK:\nSummary of patient's medical records:" in user_prompt:
    base_tokens = 1000  # Patient Summary
elif "clinical observations include:" in user_prompt:
    base_tokens = 2500  # Observations
elif "conditions summary" in user_prompt:
    base_tokens = 500  # Conditions
# ... etc
```

### Step 2: Global Cap Application
The base tokens are capped by the global maximum:
```python
MAX_NEW_TOKENS = 800  # Environment variable default
max_tokens = min(base_tokens, MAX_NEW_TOKENS)
```

This means:
- Observations: min(2500, 800) = **800 tokens**
- Patient Summary: min(1000, 800) = **800 tokens**
- Care Plans: min(700, 800) = **700 tokens**
- Conditions: min(500, 800) = **500 tokens**
- Notes: min(500, 800) = **500 tokens**
- Demographics: min(300, 800) = **300 tokens**

### Step 3: Memory-Based Reduction (Dynamic)
If GPU memory is under pressure, tokens are further reduced:
```python
if memory_usage > 0.90:
    max_tokens = min(max_tokens, 150)  # Emergency
elif memory_usage > 0.80:
    max_tokens = min(max_tokens, 300)  # High pressure
elif memory_usage > 0.70:
    max_tokens = min(max_tokens, 500)  # Moderate pressure
elif memory_usage > 0.60:
    max_tokens = min(max_tokens, 700)  # Light pressure
```

---

## Input Data Limits (Before Tokenization)

These limits control how much data is sent to the LLM:

### For Normal Categories (observations, conditions, notes, demographics):
```python
MAX_CONDITIONS = 50      # conditions after deduplication
MAX_OBSERVATIONS = 100   # observations (all rows)
MAX_NOTES = 3           # recent notes
MAX_NOTE_CHARS = 2500   # characters per note
```

### For Complex Categories (patient_summary, care_plans):
```python
max_conditions = 30      # Reduced to prevent OOM
max_observations = 50    # Reduced to prevent OOM
max_notes = 2           # Reduced to prevent OOM
max_note_chars = 2000   # Reduced to prevent OOM
```

---

## Token Count Flow

```
Input Data
    ↓
[Data Fetching with Limits]
    ↓
MAX_CONDITIONS items
MAX_OBSERVATIONS items  
MAX_NOTES items
    ↓
[Prompt Generation]
    ↓
User Prompt (variable size)
    ↓
[Category Detection]
    ↓
Base Token Limit (2,500 for observations)
    ↓
[Global Cap]
    ↓
min(Base, MAX_NEW_TOKENS) → 800 tokens
    ↓
[Memory Check]
    ↓
Adjusted Token Limit (if memory pressure)
    ↓
[LLM Generation]
    ↓
Output Text (max 800 tokens for observations)
```

---

## Key Takeaways

### ✅ Observations Gets Most Tokens
- **800 tokens** (capped by global max)
- Highest priority for data-dense output
- Lists all lab values with ranges

### ✅ Patient Summary Gets High Tokens
- **800 tokens** (capped by global max)
- Synthesizes all patient information
- Creates comprehensive narrative

### ✅ Other Categories Are Balanced
- Care Plans: 700 tokens
- Conditions: 500 tokens
- Notes: 500 tokens
- Demographics: 300 tokens

### ⚠️ All Categories Capped by Global Max
- `MAX_NEW_TOKENS = 800` (environment variable)
- Prevents excessive output
- Balances quality vs. performance

### 🔄 Dynamic Reduction Under Memory Pressure
- Observes GPU memory usage
- Reduces tokens automatically if needed
- Prevents out-of-memory errors

---

## Configuration

### Environment Variables

```bash
# Global token maximum
LLM_MAX_NEW_TOKENS=800

# Input data limits
LLM_MAX_CONDITIONS=50
LLM_MAX_OBSERVATIONS=100
LLM_MAX_NOTES=3
LLM_MAX_NOTE_CHARS=2500
```

### To Change Token Limits

1. **Edit global maximum:**
   ```bash
   export LLM_MAX_NEW_TOKENS=1200  # Increase all categories
   ```

2. **Edit category-specific limits:**
   - Modify `_get_category_token_limit()` in `backend/app/core/llm.py`

---

## Current Effective Limits

| Category | Effective Limit |
|----------|----------------|
| Observations | **800 tokens** |
| Patient Summary | **800 tokens** |
| Care Plans | **700 tokens** |
| Conditions | **500 tokens** |
| Notes | **500 tokens** |
| Demographics | **300 tokens** |

*Effective limits may be further reduced under GPU memory pressure*

---

**Last Updated:** December 2024  
**Status:** ✅ Current token allocation as implemented in `backend/app/core/llm.py`
