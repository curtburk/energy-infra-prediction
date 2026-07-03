# Grid Anomaly Prediction — Lessons Learned

## Phase 0

- **Backend Phase 3 was mostly completable in Phase 0.** The spec was detailed enough that all 8 API endpoints, the orchestrator, data models, and mock inference could be built without waiting for real model integration. Phase 3 in the implementation plan is effectively done — only integration tests remain.
- **Mock mode is essential.** With `MOCK_MODELS=true`, the entire API works end-to-end without any GPU. This unblocks frontend development completely and allows demo flow testing immediately.
- **State machine validation on the Job model catches bugs early.** Invalid transitions raise immediately rather than silently producing bad state.
- **ffprobe fallback matters.** Not every dev machine has ffprobe installed, so the video metadata probe returns sensible defaults on failure rather than crashing the upload endpoint.

## Code review (post Phase 0 build)

- **`datetime.now(timezone.utc).isoformat()` produces `+00:00`, not `Z`.** Appending `"Z"` after `isoformat()` on timezone-aware datetimes gives malformed `+00:00Z`. Use `strftime("%Y-%m-%dT%H:%M:%SZ")` instead.
- **Port conflicts are real.** Port 8000 was already taken by competitive-intel-orchestrator. Assigned 8094 to this demo. Always check existing port assignments before defaulting.
- **Don't duplicate validation logic.** Had ffprobe parsing in both `routes.py` and a standalone `validator.py` that was never called. One callsite = one implementation.
- **Don't duplicate Pydantic model hierarchies.** Had `BoundingBox` in models and `BoundingBoxSchema` in schemas with identical fields. API schemas should import and reuse domain models where shapes match.
- **Type everything, especially mock data.** `EquipmentResult.current_state` was typed as bare `Dict`, so mock data used raw dicts and summary counting used fragile `.get()` string matching. Typed `CurrentState` model makes mock data and real model output use the same contract.
- **Mock data must be deterministic for demos.** `random.randint()` in mock detection meant different results on different runs. Demos need reproducible output.
- **Dead code accumulates fast.** `ErrorResponse`, `list_all()`, `get_by_status()`, `ALLOWED_CONTENT_TYPES`, unused imports — all created "just in case" but never wired up. Remove it; git has history.
- **Docker Compose services that depend on nonexistent code crash.** Frontend service depending on `npm install` with no `package.json` yet should be behind a profile.
