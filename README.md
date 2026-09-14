# Vision AI — Home Assistant Camera Detection System

AI-powered camera vision analysis for Home Assistant. Triggers on motion/person/vehicle/animal detection from your cameras, sends camera frames to Google Gemini (free tier) for structured AI analysis, stores detection history in SQLite, and delivers phone notifications, TTS announcements, and persistent notifications.

## Features

- **AI Camera Analysis** — Sends live camera frames to Google Gemini for structured analysis (object counts, descriptions)
- **Multi-Camera Support** — Works with binary_sensor-style cameras and event-style cameras
- **SQLite Detection Database** — Full detection history with metadata (custom component, HACS-installable)
- **Live Scene Tracking** — Re-polls cameras every 60s when objects are present, updates live sensors
- **Phone Notifications** — Per-type styling (color, icon, channel) with camera snapshot thumbnails
- **TTS Announcements** — Voice alerts on TTS media players with 3-minute cooldown
- **Daily Counters** — Global and per-camera detection counts, reset at midnight
- **Snapshot Management** — Configurable local/media-mount storage with automatic retention cleanup

## Architecture

```
Camera Detection Event
        │
        ▼
┌─────────────────────────────┐
│  vision_ai_camera_analysis  │ ← Main automation
│  (AI analysis via Gemini)   │
├─────────────────────────────┤
│  Outputs:                   │
│  • SQLite record            │ → vision_ai.record_detection
│  • input_text (latest)      │ → input_text.vision_last_{area}
│  • Counter increment        │ → counter.{area}_{type}_today
│  • vision_detection event   │ → consumed by live tracker
│  • Phone notification       │ → notify.*
│  • TTS announcement         │ → tts.speak on media players
│  • Persistent notification  │ → HA dashboard
│  • Snapshot (optional)      │ → local and/or media mount
└─────────────────────────────┘
        │
        ▼ (vision_detection event)
┌─────────────────────────────┐
│  vision_live_scene_tracker  │ ← Re-polls if objects present
│  (60s interval, 10 min max) │
│  Updates input_number.*_live│
└─────────────────────────────┘
```

## Components

### Custom Component (HACS)

`custom_components/vision_ai/` — SQLite detection database with three HA services:

| Service | Description |
|---------|-------------|
| `vision_ai.record_detection` | Insert a detection record (called by automation) |
| `vision_ai.query_detections` | Query recent detections (camera, type, time window) |
| `vision_ai.get_stats` | Summary statistics for a time window |

Database: `/config/vision_ai_detections.db` (WAL mode, indexed on timestamp/camera/type)

### Automations

| File | Description |
|------|-------------|
| `vision_ai_camera_analysis.yaml` | Main pipeline: AI analysis → snapshots → counters → notifications |
| `vision_baseline_snapshots.yaml` | Quiet baseline capture for temporal comparison |
| `vision_live_scene_tracker.yaml` | Re-polls cameras with objects present (60s × 10 iterations) |
| `vision_reset_daily_detection_counters.yaml` | Reset all daily counters at midnight |
| `vision_cleanup_old_snapshots.yaml` | Delete old snapshots on a schedule |
| `examples/garage_door_ai_control.yaml` | Optional example: AI-verified garage door voice control |

### Helpers (YAML)

These must be added to `configuration.yaml` on HAOS. Each file documents the section it belongs to.

| File | Description |
|------|-------------|
| `counters.yaml` | Global + per-camera daily detection counts (**EXAMPLE camera IDs** — rename to match yours) |
| `input_numbers.yaml` | Per-camera live scene object counts (**EXAMPLE_*** names) |
| `input_texts.yaml` | Last analysis / last detection type per camera (**EXAMPLE_*** names) |
| `timers.yaml` | TTS cooldown timer |
| `input_booleans.yaml` | Master notification toggle |
| `shell_commands.yaml` | Snapshot cleanup / prior-image copy commands |

### Dashboard

`dashboards/ai_vision_tab.yaml` — Example AI Vision Lovelace view with:
- Global detection totals
- Per-camera daily breakdowns (**example entities** — adapt to your helpers)
- Live scene counts
- Last AI analysis text
- Automation status and triggers
- AI cost tracking (optional sensors)

## Cameras

Configure **your** camera entities in the automation triggers. The helper and dashboard files use illustrative names (`driveway`, `backyard`, `front_door`, `front_yard`, etc.) as examples — replace them with your entity IDs and area names.

Typical patterns:
- **Binary-sensor cameras** (person/vehicle/animal/motion) → trigger on `binary_sensor.*` state changes
- **Event cameras** → trigger on `event.*` entities

## Installation

### 1. Custom Component (via HACS or manual)

**HACS:** Add this repository as a custom integration repository in HACS.

**Manual:** Copy `custom_components/vision_ai/` to your HA `/config/custom_components/` directory. Restart HA, then add the integration via Settings → Devices & Services → Add Integration → Vision AI.

### 2. Helpers

Add the contents of each file in `helpers/` to the appropriate section in your `configuration.yaml` (after adapting example camera IDs):

```yaml
counter:
  # Paste contents of helpers/counters.yaml

input_number:
  # Paste contents of helpers/input_numbers.yaml

input_text:
  # Paste contents of helpers/input_texts.yaml

timer:
  # Paste contents of helpers/timers.yaml

input_boolean:
  # Paste contents of helpers/input_booleans.yaml

shell_command:
  # Paste contents of helpers/shell_commands.yaml
```

Restart HA after adding helpers (YAML helpers cannot be reloaded).

### 3. Secrets

Add to `/config/secrets.yaml` on HAOS (**never commit real values**):

```yaml
vision_dashboard_token: YOUR_DASHBOARD_TOKEN
```

| Key | Used by | Notes |
|-----|---------|-------|
| `vision_dashboard_token` | Optional notification deep-link buttons | Placeholder for an optional external vision dashboard; omit if unused |

The automation can load this via `!secret vision_dashboard_token` in a variables block.

See `secrets.yaml.example` in this repo.

### 4. Automations

Import or paste each automation under `automations/` into Home Assistant (UI or YAML), adapting camera entities and notify/TTS targets to your setup. Replace `YOUR_MEDIA_MOUNT` and `YOUR_VISION_HOST` placeholders.

### 5. Dashboard

Add `dashboards/ai_vision_tab.yaml` as a view in your Lovelace dashboard after renaming example entities to match your helpers.

## AI Provider

Primary: **Google Gemini** via `ai_task.generate_data` (entity: `ai_task.google_ai_task`). Free tier limits apply. The `ai_label` variable in the main automation controls the notification prefix — update it when switching providers.

## License

MIT — see [LICENSE](LICENSE).
