## Plan: Next-Gen MiniMax-Style Builder & MML Engine

Upgrade the builder to deliver a world-class, creative, and adaptive website generation experience—outperforming current AI competitors in speed, diversity, and quality.

### Steps

1. **Live Generation Progress UI**
   - Replace static progress with animated, real-time stages: "Analyzing", "Designing", "Generating", "Optimizing", "Finalizing".
   - Use Server-Sent Events (SSE) for smooth updates, or fallback to polling if needed.

2. **Project-Based File Organization**
   - Store each generation as a project with name, description, timestamp, and files.
   - Render a sidebar with project folders and file trees, not just a flat list.

3. **Hybrid Template Diversity Engine**
   - Organize 30+ hard-coded layout templates in a dedicated Python folder.
   - Use LLM to analyze prompt and user chat, then:
     - Select, remix, and mutate templates for unique structure.
     - Mix in LLM-generated sections/components for extra creativity.
   - Enable smooth, modern animations and effects in all layouts. (based on user prompt also)

4. **Self-Improving Generation**
   - Log each generation and user feedback.
   - Use logs to fine-tune LLM prompts and template selection.
   - Allow LLM to learn from user chat and past outputs for continuous improvement.

5. **Rich Completion Summaries**
   - Replace "Done!" with a detailed summary: project name, features, tech stack, color palette, animations, and suggested next steps.

6. **Performance & Output Optimization**
   - Develop advanced methods for caching, parallel generation, and asset optimization.
   - Benchmark against OpenAI, Qwen, and others for speed, creativity, and code quality.

### Further Considerations & Hot Improvements

1. **Real-time Progress**: Prefer SSE for instant feedback; fallback to polling if infra is limited.
2. **Template Diversity Approach**: Combine 30+ hard-coded layouts (organized in a folder) with LLM-driven remixing and augmentation for 100x more creative, fast, and unique results.
3. **Self-Learning Engine**: Log every generation and user feedback; use this data to improve template selection, LLM prompts, and even animations over time.
4. **Advanced Output Quality**: Use both static and LLM-generated code for best of both worlds—speed, reliability, and creativity.
5. **Benchmarking**: After implementation, run head-to-head tests (speed, code quality, design diversity, user satisfaction) vs. OpenAI, Qwen, MiniMax, etc. Aim for a score of 100/100 in creative web generation.

---

**This plan is saved in `docs/NEXTGEN_BUILDER_PLAN.md` for ongoing reference and iteration.**