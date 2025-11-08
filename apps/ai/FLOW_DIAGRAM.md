# Intelligent Review System - Flow Diagram

## Overview Flow

```
┌─────────────────────────────────────────────────────────────┐
│                    Workflow Execution                        │
└─────────────────┬───────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────────┐
│              AgentSentinel.review()                         │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ Analyze:                                              │  │
│  │  • Plugin results → PLUGIN issues                    │  │
│  │  • Planning completeness → PLANNING issues           │  │
│  │  • Policy decisions → POLICY issues                  │  │
│  │  • Context availability → CONTEXT issues             │  │
│  │  • Validation results → VALIDATION issues            │  │
│  │  • Errors → EXECUTION issues                         │  │
│  │                                                       │  │
│  │ Track:                                                │  │
│  │  • Successful steps                                  │  │
│  │  • Actionable vs non-actionable issues               │  │
│  │                                                       │  │
│  │ Generate:                                             │  │
│  │  • Recommendations                                   │  │
│  │  • Routing context                                   │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────┬───────────────────────────────────────────┘
                  │
                  ▼
         ┌────────────────┐
         │ ReviewFeedback │
         │  + Issues      │
         │  + Notes       │
         │  + Context     │
         └────────┬───────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────────┐
│              ReviewAgent.evaluate()                          │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ Analyze Issues:                                       │  │
│  │  ┌─────────────────────────────────────────────┐    │  │
│  │  │ actionable = [i for i in issues if i.actionable] │ │  │
│  │  │ non_actionable = [i for i in issues if not]     │ │  │
│  │  └─────────────────────────────────────────────┘    │  │
│  │                                                       │  │
│  │ Decision Logic:                                       │  │
│  │  ┌─────────────────────────────────────────────┐    │  │
│  │  │ if critical_non_actionable:                      │ │  │
│  │  │     return COMPLETE  # Don't retry              │ │  │
│  │  │ elif actionable and retries_left:               │ │  │
│  │  │     return RETRY  # Try with context            │ │  │
│  │  │ else:                                            │ │  │
│  │  │     return COMPLETE  # Done trying              │ │  │
│  │  └─────────────────────────────────────────────┘    │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────┬───────────────────────────────────────────┘
                  │
       ┌──────────┴──────────┐
       │                     │
       ▼                     ▼
  ┌─────────┐         ┌──────────┐
  │ COMPLETE│         │  RETRY   │
  └─────────┘         └────┬─────┘
                           │
                           ▼
         ┌─────────────────────────────────────┐
         │    route_request() [RETRY PATH]     │
         │  ┌──────────────────────────────┐   │
         │  │ Add to working notes:         │   │
         │  │  • Previous stage            │   │
         │  │  • Successful steps          │   │
         │  │  • Issue categories          │   │
         │  │  • Recommendations           │   │
         │  │  • Routing constraints:      │   │
         │  │    - Avoid failed plugins    │   │
         │  │    - Policy constraints      │   │
         │  └──────────────────────────────┘   │
         └─────────────────┬───────────────────┘
                           │
                           ▼
              ┌────────────────────────┐
              │ Workflow Re-execution  │
              │ (with better context)  │
              └────────────────────────┘
```

## Issue Categorization Flow

```
Workflow State Analysis
        │
        ├─── Plugin Result? ──────────────► PLUGIN issue
        │     └─ failed recipients          (actionable: true)
        │
        ├─── Empty Plan? ─────────────────► PLANNING issue
        │                                    (actionable: true)
        │
        ├─── Policy Constraint? ──────────► POLICY issue
        │     └─ requires_human = true      (actionable: false)
        │
        ├─── Low Context? ────────────────► CONTEXT issue
        │     └─ empty snippets             (actionable: true)
        │
        ├─── Validation Failed? ──────────► VALIDATION issue
        │                                    (actionable: true)
        │
        └─── Execution Error? ────────────► EXECUTION issue
              └─ exception occurred         (actionable: true)
```

## Retry Decision Tree

```
                    ┌──────────────┐
                    │ Issues Found?│
                    └───────┬──────┘
                            │
              ┌─────────────┴─────────────┐
              │ Yes                       │ No
              ▼                           ▼
    ┌─────────────────────┐       ┌──────────┐
    │ Critical Non-       │       │ COMPLETE │
    │ Actionable Issues?  │       │ (Success)│
    └──────┬──────────────┘       └──────────┘
           │
    ┌──────┴───────┐
    │ Yes          │ No
    ▼              ▼
┌──────────┐  ┌───────────────┐
│ COMPLETE │  │ Retries Left? │
│(Escalate)│  └───────┬───────┘
└──────────┘          │
              ┌───────┴────────┐
              │ Yes            │ No
              ▼                ▼
        ┌──────────┐    ┌──────────┐
        │  RETRY   │    │ COMPLETE │
        │ (w/ctx)  │    │(Max tries)│
        └──────────┘    └──────────┘
```

## Routing Context Example

```
Initial Attempt:
┌─────────────────────────────────────┐
│ Request: "Send email notification"  │
│ Plugin: email-plugin                │
│ Recipients: [user1, user2]          │
└─────────────────┬───────────────────┘
                  │
                  ▼
          ┌───────────────┐
          │ Plugin Failed │
          │ user2 failed  │
          └───────┬───────┘
                  │
                  ▼
┌─────────────────────────────────────────────┐
│ Review Notes Generated:                     │
│ ┌─────────────────────────────────────────┐ │
│ │ routing_context: {                      │ │
│ │   "failed_plugin": "email-plugin",      │ │
│ │   "failed_recipients": ["user2"],       │ │
│ │   "successful_count": 1                 │ │
│ │ }                                       │ │
│ │ recommendations: [                      │ │
│ │   "Try alternative delivery channel"    │ │
│ │ ]                                       │ │
│ └─────────────────────────────────────────┘ │
└─────────────────┬───────────────────────────┘
                  │
                  ▼
Retry Attempt:
┌─────────────────────────────────────────────┐
│ working_notes: [                            │
│   "[Retry 1] Previous: reviewing",          │
│   "Successful: email sent to user1",        │
│   "Issues: plugin failure for user2",       │
│   "Recommendation: Try alt channel",        │
│   "Avoid plugin: email-plugin"              │
│ ]                                           │
│                                             │
│ → Routing agent can now:                   │
│   • Skip email-plugin                       │
│   • Try SMS or other channel                │
│   • Focus only on user2                     │
└─────────────────────────────────────────────┘
```

## Benefits Visualization

```
Before (Simple Review):
  ✗ Binary approval (yes/no)
  ✗ Simple issue list
  ✗ No categorization
  ✗ No routing hints
  ✗ Blind retries

After (Intelligent Review):
  ✓ Detailed issue analysis
  ✓ Category-based insights
  ✓ Actionability assessment
  ✓ Routing context for replanning
  ✓ Recommendation system
  ✓ Success tracking
  ✓ Smart retry decisions
```
