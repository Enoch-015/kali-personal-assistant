# AI Orchestration Flow (as implemented)

This diagram reflects the current LangGraph pipeline in `src/orchestration/graph.py`, including review and retry behavior.

## High-level workflow

```
START
        → interpret_request       # Parse natural language into OrchestrationRequest (or pass through structured)
        → route_request           # Choose workflow (broadcast/generic or caller-specified)
        → policy_check            # Apply policy store; may require human or block
        → fetch_context           # Retrieve memory (Graphiti if enabled; demo fallback)
        → plan_actions            # Build coarse plan
        → agent_reflection        # Summarize reasoning/risks
        → select_plugin           # Pick plugin (metadata override > channel > demo)
        → render_payload          # Render message/template
        → [branch]
                        dispatch path: execute_plugin → review_outcome
                        skip path:                 └→ review_outcome (if no plugin)
        → review_outcome          # Sentinel governance pass
        → review_agent            # Decide RETRY vs COMPLETE
                        RETRY → route_request  # Clears dispatch state, increments retry_count
                        COMPLETE → update_memory → finalize → END
```

## Review + retry focus

```
AgentSentinel.review()
        - Classifies issues: PLUGIN, PLANNING, POLICY, CONTEXT, VALIDATION, EXECUTION, OTHER
        - Marks actionable vs non-actionable; captures severity
        - Adds recommendations and routing_context (e.g., failed_plugin, policy_reason)
        - Records successful_steps for observability

ReviewAgent.evaluate()
        - If critical non-actionable: COMPLETE (no retry)
        - Else if actionable and retries remain: RETRY (re-route with added notes)
        - Else: COMPLETE

Retry route_request()
        - Carries forward working_notes, review_notes, recommendations
        - Resets plugin-specific state before replanning
```

## Signals carried between stages

- working_notes: cumulative breadcrumbs used by router/reasoner
- selected_workflow: chosen path (broadcast/generic/custom)
- policy_decision: allow/require_human/block + tags
- retrieved_context/context_validation: memory snapshots + relevance check
- planned_actions / analysis_summary: plan and reflection
- selected_plugin / rendered_message / plugin_result: dispatch details
- review_feedback / review_action / retry_count: governance loop state
- memory_updates: summaries prepared for Graphiti commit

## Event channels (async mode)

- Requests published to Redis: `kali:agent.requests`
- Status/state published to Redis: `kali:agent.status`
