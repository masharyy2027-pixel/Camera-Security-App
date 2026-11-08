# Camera Security — Flet Android

## Included
- Password login (default: `11227788`)
- Back-camera preview and OpenCV Haar face detection
- Green face rectangle and red `Enemy` label
- Security mode, automatic alert image capture, and sound alert
- Manual capture and gallery
- Filters: Normal, Black & White, Night Vision (green)
- Change password and About screen

## Build
This project uses Flet, not Buildozer.

GitHub Actions:
1. Upload the contents of this folder to the root of a GitHub repository.
2. Open Actions.
3. Select **Build Camera Security APK**.
4. Press **Run workflow** (or push to main).
5. Download the `Camera-Security-APK` artifact from the completed run.

## Important testing note
The camera plugin streams frames to Python; the app uses OpenCV to process them.
Camera behavior, audio playback, and face-detection performance must be tested on the target Android phone before treating the APK as production-ready.

Default password: `11227788`
