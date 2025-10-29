# Agent Architecture

## ✅ All 6 Agents Call OpenAI

### **The Orchestrator is the Main Agent**

The **Orchestrator** is the primary AI agent that:

1. **Calls OpenAI** to get an orchestration plan based on the business data
2. **Coordinates** the other 5 specialized agents
3. **Assembles** the final response with audit trail

Then it calls 5 specialized agents (each also calling OpenAI):

- **Selector** - Chooses design source
- **Architect** - Plans layout
- **Mapper** - Binds content
- **Generator** - Creates bundle
- **QA** - Validates output

---

## Complete Flow

```
1. API Request → /api/build
   ↓
2. Fetch Google Data → google_fetcher
   ↓
3. Orchestrator (Main AI Agent)
   ├── Calls OpenAI to get orchestration plan
   ├── Validates inputs
   ├── Infers business intent
   └── Coordinates 5 specialized agents
       ↓
   ├── Selector AI Agent → OpenAI
   ├── Architect AI Agent → OpenAI
   ├── Mapper AI Agent → OpenAI
   ├── Generator AI Agent → OpenAI
   └── QA AI Agent → OpenAI
   ↓
4. Assemble final response with audit trail
   ↓
5. Save bundle to artifacts/
   ↓
6. Return to API
```

---

## OpenAI Integration Points

### 1. **Orchestrator** (Main Agent)

- **File**: `orchestrator.py`
- **Prompt**: ORCHESTRATOR_SYSTEM_PROMPT (lines 10-31)
- **Model**: gpt-4-turbo-preview
- **Temperature**: 0.3 (more deterministic)
- **Call**: Lines 77-88
- **Input**: place data, render_prefs, category, data_richness
- **Output**: Orchestration plan + coordinates other agents

### 2. **Selector** (Design Source Agent)

- **File**: `selector.py`
- **Prompt**: SELECTOR_SYSTEM_PROMPT (lines 8-17)
- **Model**: gpt-4-turbo-preview
- **Call**: Lines 81-88
- **Input**: business_name, category, render_prefs, data_richness
- **Output**: Design source recommendation

### 3. **Architect** (Layout Planning Agent)

- **File**: `architect.py`
- **Prompt**: ARCHITECT_SYSTEM_PROMPT (lines 8-17)
- **Model**: gpt-4-turbo-preview
- **Call**: Lines 170-177
- **Input**: business_name, category, design_source, data_richness, render_prefs
- **Output**: Layout plan with sections

### 4. **Mapper** (Content Binding Agent)

- **File**: `mapper.py`
- **Prompt**: MAPPER_SYSTEM_PROMPT (lines 9-12)
- **Model**: gpt-4-turbo-preview
- **Call**: Lines 102-109
- **Input**: layout_plan, place_payload, render_prefs
- **Output**: Content map with resolved data

### 5. **Generator** (Bundle Creation Agent)

- **File**: `generator.py`
- **Prompt**: GENERATOR_SYSTEM_PROMPT (lines 8-19)
- **Model**: gpt-4-turbo-preview
- **Temperature**: 0.7 (more creative for code generation)
- **Call**: Lines 78-86
- **Input**: business_name, render_prefs, layout_plan, content_map
- **Output**: index.html, styles.css, app.js

### 6. **QA** (Validation Agent)

- **File**: `qa.py`
- **Prompt**: QA_SYSTEM_PROMPT (lines 8-14)
- **Model**: gpt-4-turbo-preview
- **Call**: Lines 81-88
- **Input**: bundle (HTML/CSS/JS), render_prefs
- **Output**: Validation report + final bundle

---

## Prompts Embedded (Not Referenced)

All 6 agents have their **complete system prompts** embedded directly in the code:

```python
# Example from orchestrator.py
ORCHESTRATOR_SYSTEM_PROMPT = """You are the Orchestrator...
Your job: validate inputs, derive business intent...
Steps:
1) Validate and normalize...
2) Ask Design-Source Selector...
...
Constraints:
- Single page only.
- Strict escaping...
...
"""
```

**No "Ref: Product.md"** - everything is self-contained!

---

## Error Handling

Each agent has fallback logic:

```python
try:
    response = client.chat.completions.create(...)
    result = json.loads(response.choices[0].message.content)
    return result
except Exception as e:
    # Return fallback result
    return fallback_data
```

This ensures the system continues working even if individual agents fail.

---

## Summary

✅ **Orchestrator** calls OpenAI (main coordinator)  
✅ **5 Specialized Agents** each call OpenAI  
✅ **All prompts embedded** in code files  
✅ **Error handling** with fallbacks  
✅ **Complete audit trail** in final response

**Total: 6 OpenAI API calls per build**

