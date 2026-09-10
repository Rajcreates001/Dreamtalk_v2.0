# DreamTalk Astra — Frontend ↔ Backend contract

This documents the **real** backend endpoints the frontend consumes. The
backend/AI is built separately in **Codex**; the frontend tracks these routes
(no mock data). The canonical client is `src/lib/api.ts`.

Base URL: `NEXT_PUBLIC_API_URL` (default `http://localhost:5001`).
Auth: bearer token from `localStorage.access_token` on protected routes.
Wire format is `snake_case`.

> The Create-Twin flow (`/create-twin`, `src/features/create/`) drives the
> Digital Twin engine below. It requires a signed-in user.

## Create-Twin flow (`/api/v1/digital-twins`)

All routes require `Authorization: Bearer <token>`.

| Step | Method / path | Notes |
| --- | --- | --- |
| Create | `POST /api/v1/digital-twins` | body `{ name* , description?, category?, language? }` → twin (`id`, statuses) |
| Appearance upload | `POST /{id}/appearance/upload` | `multipart/form-data`, field **`files`** (one or more) → `202` |
| Appearance result | `GET /{id}/appearance/result` | poll → `{ status, face_detected, quality_score, preview_url, landmarks_2d_count, blendshapes_count }` |
| Voice upload | `POST /{id}/voice/upload` | `multipart/form-data`, field **`files`** → `202` |
| Voice result | `GET /{id}/voice/result` | poll → `{ status, is_cloned, is_synthetic, quality_score, preview_url }` |
| Update | `PUT /{id}` | e.g. `{ language }` |
| Run pipeline | `POST /api/v1/digital-twins/pipeline` | body `{ twin_id }` → `{ pipeline_id, status }` |
| Pipeline status | `GET /{id}/pipeline/status` | poll → `{ status, progress?, stage? }` |
| Get twin | `GET /{id}` | full twin model |

**Status vocabulary** (`PipelineStatus`): `pending`, `processing`,
`complete` (canonical success), `completed`, `cloned`, `failed`.
The frontend treats `complete|completed|cloned|*_complete` as success and
`failed` as error; anything else keeps polling.

## Languages (`/api/v1/avatar/languages`)

`GET` → `[{ code, name, native }]`. The frontend renders whatever the backend
returns; if the route is unavailable the language picker shows an empty state
(no hardcoded fallback).

## Notes for Codex alignment

- The frontend polls result/status endpoints; keep them idempotent and cheap.
- Upload endpoints must accept the multipart field name **`files`**.
- Errors: return non-2xx with `{ "detail": "..." }`; the UI shows friendly copy.
- There is **no mock layer** in the app — every call hits this backend.
- Avatar realtime/speech routes (`/api/avatar/*`, websocket) are owned by Codex
  and still evolving; the frontend studio will wire to them once their shapes
  settle. Coordinate route prefixes (`/api/avatar` vs `/api/v1/avatar`) there.
