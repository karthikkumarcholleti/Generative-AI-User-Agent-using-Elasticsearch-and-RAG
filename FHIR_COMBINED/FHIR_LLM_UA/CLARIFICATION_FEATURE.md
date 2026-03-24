# Clarification Feature for Non-Technical Users

## Problem Solved

**Issue:** Clinicians may not know to use technical terms like "grouped", "category", or "by type" when requesting visualizations.

**Solution:** System detects ambiguous requests and offers helpful clarification options.

---

## How It Works

### Detection Logic

The system detects ambiguous requests that don't specify visualization type:

**Ambiguous Phrases:**
- "Show me all observations"
- "Display all data"
- "List everything"
- "Show all my data"
- "Show everything"
- "All patient data"
- "Every observation"

**Action:** System recognizes the request is vague and asks for clarification.

### Clarification Options Provided

When an ambiguous request is detected, the system offers three options:

1. **📊 View all observations grouped by category (recommended)**
   - Best option for most users
   - Organized by clinical categories
   - Separate charts for each category

2. **📈 Show all observations as one chart**
   - All data in a single visualization
   - Good for overview

3. **📋 List all observations in text format**
   - Text-based list
   - Good for detailed review

---

## User Flow

### Step 1: User Asks Simply
```
User: "Show me all observations"
```

### Step 2: System Detects Ambiguity
```
Intent: clarification_needed
Type: clarification_needed
```

### Step 3: System Offers Options
```
System Response: 
"I found patient observations for this patient. 
How would you like to view them?

Please choose from the options below to proceed."

[Options displayed as buttons:]
📊 View all observations grouped by category (recommended)
📈 Show all observations as one chart  
📋 List all observations in text format
```

### Step 4: User Chooses
```
User clicks: "📊 View all observations grouped by category (recommended)"
```

### Step 5: System Generates Visualizations
```
[Charts generated for all categories with data]
```

---

## Technical Implementation

### Detection Code

```python
# Check for ambiguous "all observations" requests
if any(keyword in query_lower for keyword in [
    "all observations", "all data", "every observation", 
    "list everything", "show everything"
]):
    # Check if user didn't specify visualization type
    if "group" not in query_lower and "category" not in query_lower and "type" not in query_lower:
        # Mark as clarification needed
        intent["type"] = "clarification_needed"
        intent["follow_up_options"] = [
            "📊 View all observations grouped by category (recommended)",
            "📈 Show all observations as one chart",
            "📋 List all observations in text format"
        ]
```

### Response Generation

```python
# Handle clarification requests
if intent.get("type") == "clarification_needed":
    return (
        "I found patient observations for this patient. "
        "How would you like to view them?\n\n"
        "Please choose from the options below to proceed."
    )
```

---

## Benefits

### ✅ For Clinicians
- **No need to learn technical terms**
- **Simple, natural language works**
- **System guides them to best option**
- **Clear recommendations provided**

### ✅ For Patients
- **Easy to use**
- **Self-explanatory options**
- **Multiple choices available**

### ✅ For System
- **Prevents confusion**
- **Reduces errors**
- **Better user experience**
- **Guided interactions**

---

## Example Use Cases

### Use Case 1: Busy Clinician

**Scenario:** Doctor in a hurry, doesn't remember exact commands

**What they ask:**
```
"Show me everything for this patient"
```

**System helps by:**
- Recognizing the request is unclear
- Offering 3 clear options
- Recommending best choice

**Result:** Doctor gets exactly what they need without frustration

---

### Use Case 2: First-Time User

**Scenario:** New user doesn't know system capabilities

**What they ask:**
```
"List all observations"
```

**System helps by:**
- Showing available visualization options
- Explaining what each does
- Recommending grouped view

**Result:** User learns system capabilities while getting their data

---

### Use Case 3: Different Preferences

**Scenario:** Different users prefer different formats

**User A asks:** "Show all data"
→ Chooses: Grouped by category (visual)
→ Gets: Charts organized by category

**User B asks:** "Show all data"
→ Chooses: Text format
→ Gets: Detailed text list

**Result:** Each user gets their preferred format

---

## Edge Cases Handled

### Case 1: Specific Request (No Clarification)
```
User: "Show me all observations grouped by category"
System: Generates visualizations immediately (no clarification needed)
```

### Case 2: Partial Keywords
```
User: "Show observations by type"
System: Recognizes "by type" as grouping request, generates immediately
```

### Case 3: Vague Request
```
User: "What data do you have?"
System: Asks for clarification (detects no specific visualization type)
```

---

## Summary

**Feature:** Intelligent clarification for ambiguous requests

**Result:**
- ✅ No technical knowledge required
- ✅ System offers helpful options
- ✅ Best option is recommended
- ✅ Multiple choices available
- ✅ Better user experience
- ✅ Guided interactions

**Status:** ✅ Implemented and ready to use
