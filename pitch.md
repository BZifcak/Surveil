# Surveil

### AI-powered campus surveillance that acts before disaster strikes.

---

## The Problem

Campus security cameras are everywhere. They just aren't working.

**91% of US campuses have video surveillance systems** — yet the footage is almost entirely used _after_ incidents occur, not to prevent them.[^1] A single security officer cannot realistically monitor 9, 16, or 32 feeds simultaneously without missing something. The cameras record. Nobody watches.

The consequences are measurable:

- Over **23,400 on-campus criminal incidents** are reported annually at US postsecondary institutions.[^2]
- The average **active shooter incident lasts 12.5 minutes**. The average law enforcement response time is **18 minutes**.[^3] That 5.5-minute gap is the window where lives are lost.
- Security footage helps resolve incidents **50% faster** — but only after the fact.[^1]

The infrastructure exists. The gap is in _real-time human attention_.

---

## The Solution

**Surveil** is a live surveillance dashboard that watches your cameras so your officers don't have to.

It integrates with existing camera infrastructure, runs AI detection continuously across all feeds simultaneously, and immediately surfaces threats — ranked by severity — to the people who need to act on them.

When a weapon is spotted, a fight breaks out, or a fire starts, Surveil flags it instantly. No lag. No missed feeds. No waiting for a recording to be reviewed after the fact.

---

## How It Works

```
Camera feeds  →  AI detection  →  Prioritized alerts  →  Officer response
```

Surveil monitors multiple live camera streams in parallel. A multi-model AI pipeline runs continuously on each feed, detecting:

| Priority | Event                                 |
| -------- | ------------------------------------- |
| Critical | Weapon detected, Physical altercation |
| High     | Fire / smoke                          |
| Medium   | Person fallen                         |
| Low      | Person detected, Motion               |

Detections are surfaced on the dashboard in real time with bounding boxes overlaid on the live feed, timestamped alerts, and a priority-sorted incident log. Officers see the highest-severity events first — they never need to manually scan feeds to find a problem.

---

## Why It Matters

Current surveillance is **reactive by design**. Surveil makes it **proactive**.

The 18-minute response gap to active threats is not primarily a staffing problem — campuses cannot afford to put a human behind every camera. It is an _attention_ problem. AI does not blink, does not get fatigued, and does not miss a feed because it was watching another screen.

Surveil doesn't replace security officers. It makes the ones you have dramatically more effective by telling them exactly where to look, the moment something happens.

---

## The Stack

- **Python / FastAPI** backend — real-time MJPEG video streaming
- **YOLOv8** — multi-model AI detection pipeline (person, fire/smoke, weapons, falls)
- **WebSocket** event bus — sub-second alert delivery to the dashboard
- **React** frontend — multi-camera live view with overlaid detection events

---

[^1]: Campus Safety Magazine, _More Than 8 in 10 Campuses Use Their Security Cameras Daily_, 2024 Video Surveillance Survey. https://www.campussafetymagazine.com/insights/more-than-8-in-10-campuses-use-security-cameras-daily-2024-video-surveillance-survey-finds/164797/

[^2]: National Center for Education Statistics, _Fast Facts: College Crime (804)_. https://nces.ed.gov/fastfacts/display.asp?id=804

[^3]: ALICE Training Institute, _Understanding Active Shooter Statistics & Incident Response Times_. https://www.alicetraining.com/blog/understanding-active-shooter-statistics-incident-response-times/
