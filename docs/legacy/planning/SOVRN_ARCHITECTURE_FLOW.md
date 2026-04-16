# SOVRN Organized System Architecture: Feature Flow

This document outlines the clean, organized flow of the production-ready SOVRN system. It moves away from chaotic sequential processing to a modular, event-driven architecture that ensures speed, reliability, and maintainability.

## 1. High-Level System Topology

The system is divided into four distinct planes, ensuring separation of concerns:

1.  **Interaction Plane (Frontend)**: Real-time UI, Canvas, and State Management.
2.  **Orchestration Plane (Control Layer)**: Traffic control, job queuing, and session management.
3.  **Intelligence Plane (AI Core)**: Specialized models running in parallel pools.
4.  **Data Plane (Persistence)**: Local vector store, project state, and asset management.

```mermaid
graph TD
    subgraph "Interaction Plane"
        A[User Browser] -->|WebSocket Stream| B[Live Canvas]
        A -->|Commands| C[Command Center]
    end

    subgraph "Orchestration Plane"
        C --> D[API Gateway]
        D --> E[Session Manager]
        E --> F[Job Queue (Redis)]
        F -->|Dispatch| G[Worker Pool]
    end

    subgraph "Intelligence Plane"
        G --> H[Sketch Agent Pool]
        G --> I[Architect Agent Pool]
        G --> J[Stylist Agent Pool]
        G --> K[Engineer Agent Pool]
        H & I & J & K --> L[Model Router]
        L --> M[Inference Engine (MLX/vLLM)]
    end

    subgraph "Data Plane"
        N[Project DB (Postgres)]
        O[Vector Store (Chroma/Milvus)]
        P[Asset Store (Local FS/S3)]
        Q[State Log (CRDT)]
    end

    G -.-> N
    G -.-> O
    G -.-> P
    B <-->|Sync| Q
```

---

## 2. The Core Generation Flow (The "Happy Path")

This is the standardized lifecycle of a single website generation request, optimized for speed and user feedback.

### Phase 1: Intent & Context (0s - 2s)
*Goal: Understand exactly what to build without hallucination.*

1.  **User Input**: User enters prompt ("A minimalist portfolio for a photographer").
2.  **Context Retrieval**:
    *   System queries **Local RAG** for user's brand history (fonts, colors, past preferences).
    *   System performs **Intent Classification** (Type: Portfolio, Style: Minimalist, Industry: Photography).
3.  **Output**: A structured `GenerationContext` JSON object.

### Phase 2: Speculative Sketching (2s - 5s)
*Goal: Provide immediate visual feedback and structural options.*

1.  **Parallel Execution**: The `Sketch Agent` (tiny model) generates **3 distinct structural skeletons** simultaneously.
    *   *Skeleton A*: Grid-heavy layout.
    *   *Skeleton B*: Single-page scroll.
    *   *Skeleton C*: Gallery-focused.
2.  **Streaming**: Skeletons are streamed to the frontend as low-fidelity wireframes.
3.  **Selection**: User clicks one skeleton (or AI auto-selects the highest confidence score).
    *   *System Action*: Discards unselected branches to save compute.

### Phase 3: Parallel Component Expansion (5s - 15s)
*Goal: Flesh out the chosen skeleton with high-quality code.*

Once a skeleton is selected, the system spawns **Parallel Worker Threads** based on the sitemap:

*   **Worker 1 (Hero/Nav)**: Runs `Architect` (structure) + `Stylist` (Tailwind classes).
*   **Worker 2 (Content/Features)**: Runs `Architect` + `Copywriter` (text) + `Stylist`.
*   **Worker 3 (Footer/Contact)**: Runs `Architect` + `Stylist`.
*   **Worker 4 (Logic/Interactivity)**: Runs `Engineer` (React hooks, JS logic).

**Synchronization**: All workers write to a shared **CRDT Document** (Yjs), ensuring no merge conflicts occur when assembling the final file.

### Phase 4: Self-Healing & Validation (15s - 17s)
*Goal: Ensure the code actually works before showing it.*

1.  **Static Analysis**: A lightweight linter scans the generated AST (Abstract Syntax Tree).
2.  **Error Detection**: If a tag is unclosed or a React hook is invalid:
    *   The `Fixer Agent` (rule-based or tiny model) patches the specific node.
    *   Retry count increments.
3.  **Success**: Code passes validation.

### Phase 5: Live Rendering & Handoff (17s+)
*Goal: Seamless transition from generation to editing.*

1.  **DOM Injection**: Validated components are injected into the live preview canvas.
2.  **State Lock**: The generation session closes; the **Editor Session** opens.
3.  **Persist**: Full project state saved to Postgres + Vector Store updated with new design patterns.

---

## 3. Data Flow Schema

Clean data structures are vital for modularity. The system passes these immutable objects between agents.

### A. The `SiteStrategy` Object
*Produced by: Strategist Agent*
```json
{
  "project_id": "uuid",
  "intent": "portfolio",
  "target_audience": "creative_professionals",
  "brand_palette": {
    "primary": "#FF5733",
    "secondary": "#2C3E50",
    "font_family": "Inter"
  },
  "sitemap": [
    {"id": "hero", "type": "section", "priority": 1},
    {"id": "gallery", "type": "component", "priority": 2},
    {"id": "contact", "type": "form", "priority": 3}
  ]
}
```

### B. The `ComponentSpec` Object
*Produced by: Architect/Stylist Agents*
```json
{
  "component_id": "hero_01",
  "type": "ReactFunction",
  "props_schema": { "title": "string", "image_url": "string" },
  "tailwind_classes": "flex h-screen items-center bg-gray-900 text-white",
  "dependencies": ["framer-motion", "lucide-react"],
  "content_source": "rag_retrieved_copy_v2"
}
```

### C. The `CodeArtifact` Object
*Produced by: Engineer Agent*
```json
{
  "file_path": "/src/components/Hero.tsx",
  "code_string": "export default function Hero(...) { ... }",
  "checksum": "sha256_hash",
  "validation_status": "passed",
  "lint_errors": []
}
```

---

## 4. Error Handling & Recovery Loops

An organized system must handle failure gracefully without crashing the user experience.

| Failure Scenario | Detection Point | Recovery Strategy | User Experience |
| :--- | :--- | :--- | :--- |
| **Model Hallucination** | Linter / Validator | Trigger `Fixer Agent` to rewrite specific block. Max 3 retries. | "Refining code..." (Spinner on specific block) |
| **GPU OOM (Out of Memory)** | Inference Engine | Automatically offload to CPU or switch to smaller quantized model (Q2_K). | Slight slowdown, no crash. Toast notification: "Optimizing for memory." |
| **RAG Retrieval Fail** | Context Loader | Fallback to default brand guidelines stored in config. | Generation continues with generic styles. |
| **Merge Conflict** | CRDT Sync | Atomic locking on component IDs. Last-write-wins based on timestamp. | Invisible to user; handled in backend. |
| **Prompt Injection** | Input Sanitizer | Block request immediately. Log security event. | Error message: "Invalid input detected." |

---

## 5. Module Responsibilities Matrix

To keep the codebase clean, every module has a single responsibility.

| Module | Responsibility | Input | Output | Tech Stack |
| :--- | :--- | :--- | :--- | :--- |
| **Gateway** | Auth, Rate Limiting, Routing | HTTP/WebSocket Request | Session Token | FastAPI / Nginx |
| **Orchestrator** | Job Dispatch, Dependency Graph | `GenerationContext` | Task IDs | Celery / Redis |
| **Sketch Agent** | Low-fidelity Layout Gen | Prompt Embedding | HTML Skeleton | TinyLLM (<1B) |
| **Architect** | Component Tree Structure | `SiteStrategy` | JSON Component Tree | Llama-3-8B |
| **Stylist** | CSS/Tailwind Application | Component Tree | Tailwind Classes | Mistral-7B (Fine-tuned) |
| **Engineer** | Logic & Wiring | Component Spec + Styles | `.tsx` Source Code | Llama-3-8B |
| **Linter** | Syntax Validation | Source Code | Pass/Fail + Fixes | ESLint / Custom AST |
| **Renderer** | DOM Construction | Code Artifacts | Live Preview | Next.js / Sandpack |
| **Memory** | Long-term Storage | Project Artifacts | Vector Embeddings | ChromaDB / Postgres |

---

## 6. The "Clean Code" Principles for SOVRN

To maintain this architecture, the development team must adhere to these rules:

1.  **Immutable State**: Once an agent produces a `ComponentSpec`, it cannot be modified in place. Changes create a new version.
2.  **Schema-First Design**: All communication between agents must be validated against Pydantic schemas. No loose JSON.
3.  **Async Everywhere**: No blocking calls in the main thread. All AI inference happens in background workers.
4.  **Testable Agents**: Each agent (Sketch, Architect, etc.) must have unit tests with fixed inputs and expected JSON outputs.
5.  **Graceful Degradation**: If the GPU fails, the system must degrade to CPU, not crash. If the large model fails, fallback to the small model.

This organized flow ensures SOVRN is not just a script, but a robust, scalable platform capable of competing with enterprise solutions while maintaining its offline-first privacy promise.