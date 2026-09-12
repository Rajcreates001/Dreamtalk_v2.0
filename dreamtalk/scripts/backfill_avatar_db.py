"""Backfill existing avatar-runtime profiles into Postgres.

The runtime kept profiles only in results/avatar_runtime_profiles.json until
the avatar_profiles / avatar_profile_assets tables were added. This mirrors the
ones already on disk so nothing created before that change is left out.
"""
import asyncio
import json
import os
import sys

sys.path.insert(0, "/app")

REGISTRY = os.environ.get(
    "AVATAR_REGISTRY", "/app/dreamtalk/results/avatar_runtime_profiles.json")


async def main() -> int:
    from dreamtalk.backend.services.avatar_runtime import AvatarRuntimeService

    with open(REGISTRY, encoding="utf-8") as fh:
        raw = json.load(fh)
    profiles = raw.get("profiles", raw)
    svc = AvatarRuntimeService()

    ok = skipped = failed = 0
    for pid, profile in profiles.items():
        profile.setdefault("id", pid)
        if not profile.get("user_id"):
            skipped += 1
            continue
        if await svc._persist_profile_to_db(profile):
            ok += 1
        else:
            failed += 1
    print(f"backfilled={ok} skipped_no_user={skipped} failed={failed} "
          f"of {len(profiles)} profiles")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
