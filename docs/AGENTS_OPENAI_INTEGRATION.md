# Agents OpenAI Integration Verification

## ✅ All 6 Agents Integrate with OpenAI

Each agent calls OpenAI with:

1. **System Prompt** - The full prompt from Product.md
2. **User Message** - The input data formatted as JSON
3. **Response Format** - JSON object for structured responses
4. **Error Handling** - Fallback logic if OpenAI fails

---

### **1. Selector Agent** (`selector.py`)

**System Prompt**: SELECTOR_SYSTEM_PROMPT

- Lines 8-17: Full prompt embedded
- Prompt: "You select a reference design source..."

**OpenAI Call**:

```python
response = client.chat.completions.create(
    model="gpt-4-turbo-preview",
    messages=[
        {"role": "system", "content": SELECTOR_SYSTEM_PROMPT},
        {"role": "user", "content": json.dumps(user_message, indent=2)}
    ],
    response_format={"type": "json_object"}
)
```

**Input**: business_name, category, render_prefs, data_richness  
**Output**: Design source with name, url, style_keywords, layout_notes, license_note

---

### **2. Architect Agent** (`architect.py`)

**System Prompt**: ARCHITECT_SYSTEM_PROMPT

- Lines 8-17: Full prompt embedded
- Prompt: "Design a section/component blueprint..."

**OpenAI Call**:

```python
response = client.chat.completions.create(
    model="gpt-4-turbo-preview",
    messages=[
        {"role": "system", "content": ARCHITECT_SYSTEM_PROMPT},
        {"role": "user", "content": json.dumps(user_message, indent=2)}
    ],
    response_format={"type": "json_object"}
)
```

**Input**: business_name, category, design_source, data_richness, render_prefs  
**Output**: Layout plan with sections (hero, gallery, about, reviews, credits, map)

---

### **3. Mapper Agent** (`mapper.py`)

**System Prompt**: MAPPER_SYSTEM_PROMPT

- Lines 9-12: Full prompt embedded
- Prompt: "Bind real data into the layout plan..."

**OpenAI Call**:

```python
response = client.chat.completions.create(
    model="gpt-4-turbo-preview",
    messages=[
        {"role": "system", "content": MAPPER_SYSTEM_PROMPT},
        {"role": "user", "content": json.dumps(user_message, indent=2)}
    ],
    response_format={"type": "json_object"}
)
```

**Input**: layout_plan, place_payload, render_prefs  
**Output**: Content map with resolved_content for each section + sanitization policy

---

### **4. Generator Agent** (`generator.py`)

**System Prompt**: GENERATOR_SYSTEM_PROMPT

- Lines 8-19: Full prompt embedded
- Prompt: "Generate a single-page bundle..."

**OpenAI Call**:

```python
response = client.chat.completions.create(
    model="gpt-4-turbo-preview",
    messages=[
        {"role": "system", "content": GENERATOR_SYSTEM_PROMPT},
        {"role": "user", "content": json.dumps(user_message, indent=2)}
    ],
    response_format={"type": "json_object"},
    temperature=0.7
)
```

**Input**: business_name, render_prefs, layout_plan, content_map  
**Output**: Bundle with index_html, styles_css, app_js + meta

---

### **5. QA Agent** (`qa.py`)

**System Prompt**: QA_SYSTEM_PROMPT

- Lines 8-14: Full prompt embedded
- Prompt: "Validate the bundle for a11y..."

**OpenAI Call**:

```python
response = client.chat.completions.create(
    model="gpt-4-turbo-preview",
    messages=[
        {"role": "system", "content": QA_SYSTEM_PROMPT},
        {"role": "user", "content": json.dumps(user_message, indent=2)}
    ],
    response_format={"type": "json_object"}
)
```

**Input**: bundle (HTML/CSS/JS), render_prefs  
**Output**: Report (a11y, performance, policy) + final_bundle

---

### **6. Orchestrator** (`orchestrator.py`)

**System Prompt**: ORCHESTRATOR_SYSTEM_PROMPT

- Lines 9-31: Full prompt embedded
- Prompt: "You are the Orchestrator..."

**Role**: Coordinates all 5 agents (does not call OpenAI directly)

- Calls: selector, architect, mapper, generator, qa
- Manages the 6-step workflow
- Assembles final response with audit trail

---

## OpenAI Client Setup

**File**: `backend/app/agents/client.py`

```python
class OpenAIClient:
    def __init__(self):
        self.client = OpenAI(api_key=settings.openai_api_key)

    def get_client(self):
        return self.client
```

**Usage**: All agents import and use:

```python
from app.agents.client import openai_client

client = openai_client.get_client()
```

---

## Integration Flow

```
orchestrator.py
    ↓
    ├──→ selector.py ──→ OpenAI (gpt-4-turbo-preview)
    ├──→ architect.py ──→ OpenAI (gpt-4-turbo-preview)
    ├──→ mapper.py ──→ OpenAI (gpt-4-turbo-preview)
    ├──→ generator.py ──→ OpenAI (gpt-4-turbo-preview)
    └──→ qa.py ──→ OpenAI (gpt-4-turbo-preview)
```

---

## Verification Checklist

- ✅ All 5 agent functions call OpenAI
- ✅ Each agent has a unique system prompt
- ✅ All prompts embedded (not referenced)
- ✅ Response format is JSON object
- ✅ Error handling with fallbacks
- ✅ OpenAI client properly initialized
- ✅ Model: gpt-4-turbo-preview
- ✅ Orchestrator coordinates all 5 agents

---

## Error Handling

Each agent has:

```python
try:
    response = client.chat.completions.create(...)
    result = json.loads(response.choices[0].message.content)
    return result
except Exception as e:
    # Return fallback result
    return fallback_data
```

This ensures the system continues working even if OpenAI API fails.

