# Lean AI

An AI-guided assembly assistant for the shop floor. A camera watches the workstation, the app walks the operator through each assembly step, an AI model checks the result of every step against reference photos, and the time spent on each action is logged and classified using lean manufacturing categories (VA, NVA, NNVA).

## What it does

1. **Guides the operator.** Pick a product, and the app shows the current step and its instruction, with a live camera view.
2. **Detects activity.** Frame differencing inside a configurable zone of the camera image tells the app when the operator is actually assembling and when they are idle.
3. **Verifies each step.** When the operator clicks *Verify Step*, the part of the camera frame inside the work zone is sent to a vision model together with the reference images and the rules for that step. The model returns `correct`, `wrong` or `waiting` with a short explanation. A `correct` result moves the app on to the next step automatically; *Previous* and *Next* buttons are also available.
4. **Logs every action.** Each action is timed and tagged as value-added (VA), non-value-added (NVA) or necessary non-value-added (NNVA). The AI verification itself is logged as NNVA.
5. **Reports.** After the last step, a lean analytics summary shows total VA, NVA and NNVA time, overall efficiency, charts, and a unified action timeline that can be downloaded as a file.

An optional second analysis path sends the recorded clip of each step to a separate video-analysis server (Nemotron) and merges the detected actions into the same timeline.

## Supported products

| Product | Steps |
|---|---|
| Lamp Assembly | LED module installation, internal diffuser spacer, outer diffuser cover, mounting base, completion |
| Keychain Assembly | Keychain assembly, sticker application, completion |

Each step is defined in `lamp_steps.py` or `keychain_steps.py` with:
- `instruction`: what the operator should do
- `verification_goal`: what the AI should judge
- `must_have`: conditions that must be visible for the step to pass
- `must_not_require`: things the AI must not demand yet (parts that come in later steps)
- `action_type`: VA, NVA or NNVA
- `reference_images`: acceptable example photos in `references/`

## Tech stack

- Python and Streamlit for the interface
- OpenCV for camera capture and motion detection
- OpenAI vision model (`gpt-4.1-mini`) for step verification
- Google Gemini (`gemini-2.5-flash`) verifier included in `gemini/` as an alternative, not used by `app.py` by default
- pandas for the timeline and analytics
- Optional: a Nemotron video-analysis server reached over HTTP

## Getting started

### Requirements
- Python 3.10 or newer
- A webcam
- An OpenAI API key

### Setup

```bash
git clone https://github.com/syzwanzaidi/lean-ai.git
cd lean-ai

python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

`requirements.txt` is saved with UTF-16 encoding. If pip cannot read it on your system, re-save it as UTF-8 and run the install again.

Create a `.env` file in the project root:

```env
OPENAI_API_KEY=your_openai_key
# Only needed if you use the Gemini verifier in gemini/
GEMINI_API_KEY=your_gemini_key
```

The app needs `OPENAI_API_KEY` to start, because the verifier client is created when the app loads.

### Run

```bash
streamlit run app.py
```

Open the URL Streamlit prints (usually http://localhost:8501), choose a product in the sidebar and follow the steps.

## Configuration

Settings live as constants at the top of `app.py`:

| Setting | Purpose |
|---|---|
| `CAMERA_INDEX` | Which camera to use (0 is the default webcam) |
| `ZONE` | The part of the frame, as ratios, where motion is measured |
| `MOTION_THRESHOLD` | How much change in the zone counts as assembling |
| `MIN_ACTION_DURATION` | Shortest movement that is logged as an action |
| `IDLE_GRACE_SECONDS` | How long the operator can pause before the action is closed |
| `NEMOTRON_URL` | Address of the optional video-analysis server |

If the camera does not open, click *Reset Camera* in the app and refresh the page.

### Optional: Nemotron timeline

Run a compatible video-analysis server and point `NEMOTRON_URL` at it (the default is `http://127.0.0.1:8000/analyze`). The app posts a recorded clip of each step with its `step_id` and `step_title`, and expects JSON with an `actions` list where each action has `start_time`, `end_time`, `duration_seconds`, `action_name` and `action_type`. The server itself is not part of this repository.

## Adding a new product

1. Create a steps file like `lamp_steps.py` with a `STEPS` list. Put the final "Assembly Completed" step last.
2. Add 2 to 4 reference photos per step under `references/<product>/`.
3. Import the file in `app.py` and add it to the `PRODUCTS` dictionary.

## Project structure

```
app.py                  Streamlit app: camera, step flow, analytics
lamp_steps.py           Lamp assembly step definitions
keychain_steps.py       Keychain assembly step definitions
openai_verifier.py      Vision-based step verification (OpenAI)
gemini/                 Alternative Gemini verifier and test scripts
motion_detector.py      Frame-difference motion scoring
action_logger.py        Action timing and logging
zone_config.py / .json  Zone helper and saved zone values (the app currently reads ZONE from app.py)
references/             Reference photos per product and step
```

## Notes

- Verification is designed for a live demo: it ignores position, rotation, lighting and cable shape, and only judges the current step.
- Captured frames and clips, local videos and `.env` are git-ignored.

## Author

Muhammad Syazwan Syahmi Bin Mat Zaidi. [GitHub](https://github.com/syzwanzaidi) | [Portfolio](https://syzwanzaidi-portfolio.vercel.app/)
