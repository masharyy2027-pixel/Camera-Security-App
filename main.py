import asyncio
import os
import time
from datetime import datetime
from pathlib import Path

import cv2
import flet as ft
import flet_camera as fc
import flet_audio as fta

APP_NAME = "Camera Security"
DEFAULT_PASSWORD = "11227788"
ALARM_FILE = "assets/alarm.wav"
CASCADE_FILE = "assets/haarcascade_frontalface_default.xml"


def app_storage(page: ft.Page) -> Path:
    # Android app-private home directory; no broad storage permission required.
    base = Path.home() / "CameraSecurity"
    base.mkdir(parents=True, exist_ok=True)
    return base


async def main(page: ft.Page):
    page.title = APP_NAME
    page.theme_mode = ft.ThemeMode.DARK
    page.bgcolor = "#07111B"
    page.padding = 14
    page.scroll = ft.ScrollMode.AUTO
    page.horizontal_alignment = ft.CrossAxisAlignment.STRETCH

    data_dir = app_storage(page)
    gallery_dir = data_dir / "Gallery"
    gallery_dir.mkdir(exist_ok=True)
    password_file = data_dir / "password.txt"
    password = password_file.read_text(encoding="utf-8").strip() if password_file.exists() else DEFAULT_PASSWORD

    state = {
        "camera": None,
        "initialized": False,
        "streaming": False,
        "security": False,
        "filter": "Normal",
        "last_alert": 0.0,
        "last_frame": None,
        "last_detected": False,
        "frame_count": 0,
        "countdown_end": 0.0,
        "logged_in": False,
    }

    # OpenCV wheels bundle the standard Haar cascade data directory.
    cascade_path = Path(cv2.data.haarcascades) / "haarcascade_frontalface_default.xml"
    face_cascade = cv2.CascadeClassifier(str(cascade_path))
    cascade_ok = not face_cascade.empty()

    alarm = fta.Audio(src=ALARM_FILE, volume=1.0, autoplay=False)
    page.services.append(alarm)

    def snack(message: str):
        page.snack_bar = ft.SnackBar(content=ft.Text(message))
        page.snack_bar.open = True
        page.update()

    def save_frame(frame, prefix):
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        target = gallery_dir / f"{prefix}_{stamp}.jpg"
        cv2.imwrite(str(target), frame)
        return target

    def process_frame(encoded: bytes):
        import numpy as np
        arr = np.frombuffer(encoded, dtype=np.uint8)
        frame = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        if frame is None:
            return None, False
        # Reduce processing size for a smoother experience on mid-range phones.
        h, w = frame.shape[:2]
        if w > 640:
            scale = 640.0 / w
            frame = cv2.resize(frame, (640, int(h * scale)), interpolation=cv2.INTER_AREA)

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = []
        if cascade_ok and state["frame_count"] % 3 == 0:
            faces = face_cascade.detectMultiScale(gray, scaleFactor=1.25, minNeighbors=5, minSize=(45, 45))
            state["last_faces"] = faces
        else:
            faces = state.get("last_faces", [])

        detected = len(faces) > 0
        for (x, y, fw, fh) in faces:
            cv2.rectangle(frame, (x, y), (x + fw, y + fh), (0, 255, 0), 2)
            cv2.putText(frame, "Enemy", (x, max(22, y - 8)), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 0, 255), 2)

        mode = state["filter"]
        if mode == "Black & White":
            frame = cv2.cvtColor(cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY), cv2.COLOR_GRAY2BGR)
        elif mode == "Night Vision":
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            enhanced = cv2.equalizeHist(gray)
            green = cv2.merge((enhanced * 0, enhanced, enhanced * 0))
            frame = cv2.addWeighted(frame * 0, 0.0, green, 1.0, 0)
            # Subtle phosphor-style green tint.
            frame[:, :, 1] = cv2.convertScaleAbs(frame[:, :, 1], alpha=1.35, beta=8)

        state["frame_count"] += 1
        return frame, detected

    # ---------- LOGIN ----------
    password_input = ft.TextField(
        label="Password / كلمة المرور",
        password=True,
        can_reveal_password=True,
        autofocus=True,
        border_color="#1C8B65",
    )
    login_error = ft.Text("", color="#FF6868")

    def show_about(_=None):
        page.dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Camera Security | حول البرنامج"),
            content=ft.Column(
                tight=True,
                controls=[
                    ft.Text("نظام كاميرا أمنية ذكي / Smart Security Camera"),
                    ft.Text("• كشف الوجوه الآلي / Auto Face Detection"),
                    ft.Text("• تنبيه Enemy بإطار أخضر ووسم أحمر"),
                    ft.Text("• إنذار صوتي والتقاط تلقائي عند تفعيل الحماية"),
                    ft.Text("• فلاتر: عادي، أبيض وأسود، رؤية ليلية خضراء"),
                    ft.Text("• معرض صور وتغيير كلمة المرور"),
                    ft.Divider(),
                    ft.Text("Developer: Hussein Al-Bayati"),
                    ft.Text("Instagram: @bgq_v"),
                ],
            ),
            actions=[ft.TextButton("Close / إغلاق", on_click=lambda e: close_dialog())],
        )
        page.dialog.open = True
        page.update()

    def close_dialog():
        if page.dialog:
            page.dialog.open = False
            page.update()

    def login(_):
        nonlocal password
        if password_input.value == password:
            state["logged_in"] = True
            build_main_screen()
        else:
            login_error.value = "كلمة المرور غير صحيحة / Wrong password"
            page.update()

    def build_login():
        page.clean()
        page.add(
            ft.Container(
                padding=22,
                border_radius=20,
                bgcolor="#101F2D",
                content=ft.Column(
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    tight=True,
                    controls=[
                        ft.Icon(ft.Icons.SHIELD_MOON, size=64, color="#27D98B"),
                        ft.Text("CAMERA SECURITY", size=24, weight=ft.FontWeight.BOLD, color="#EAF7F2"),
                        ft.Text("نظام الكاميرا الأمنية", size=17, color="#9EB8B1"),
                        password_input,
                        login_error,
                        ft.FilledButton("دخول / LOGIN", icon=ft.Icons.LOCK_OPEN, on_click=login, width=220),
                        ft.TextButton("حول البرنامج / ABOUT", on_click=show_about),
                        ft.Text(f"تلميح / Hint: {password[:2]}••••{password[-2:]}", color="#78938D", size=12),
                    ],
                ),
            )
        )

    # ---------- MAIN SCREEN ----------
    camera_status = ft.Text("Camera not started", color="#A9C0B8", size=12)
    security_badge = ft.Container(
        padding=8, border_radius=20, bgcolor="#542020",
        content=ft.Text("SECURITY OFF", color="white", weight=ft.FontWeight.BOLD, size=12),
    )
    detection_status = ft.Text("No person detected", color="#A9C0B8", size=13)
    frame_image = ft.Image(src=None, fit=ft.ImageFit.CONTAIN, expand=True)
    camera = fc.Camera(expand=True, preview_enabled=False)
    filter_dropdown = ft.Dropdown(
        label="Filter / الفلتر",
        value="Normal",
        options=[
            ft.dropdown.Option("Normal"),
            ft.dropdown.Option("Black & White"),
            ft.dropdown.Option("Night Vision"),
        ],
        on_select=lambda e: state.update({"filter": e.control.value or "Normal"}),
        dense=True,
    )
    gallery_list = ft.Column(spacing=6, scroll=ft.ScrollMode.AUTO, height=150)

    def refresh_gallery():
        gallery_list.controls.clear()
        files = sorted(gallery_dir.glob("*.jpg"), key=lambda p: p.stat().st_mtime, reverse=True)[:30]
        if not files:
            gallery_list.controls.append(ft.Text("لا توجد صور بعد / Gallery is empty", color="#9EB8B1"))
        for file in files:
            gallery_list.controls.append(
                ft.ListTile(
                    leading=ft.Icon(ft.Icons.IMAGE, color="#27D98B"),
                    title=ft.Text(file.name, size=12),
                    subtitle=ft.Text(datetime.fromtimestamp(file.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S"), size=10),
                )
            )
        page.update()

    def set_security(_):
        state["security"] = not state["security"]
        if state["security"]:
            security_badge.bgcolor = "#075C3A"
            security_badge.content.value = "SECURITY ON"
            security_badge.content.color = "white"
            snack("تم تفعيل الحماية / Security enabled")
        else:
            security_badge.bgcolor = "#542020"
            security_badge.content.value = "SECURITY OFF"
            snack("تم إيقاف الحماية / Security disabled")
        page.update()

    async def capture_manual(_):
        if state["last_frame"] is None:
            snack("انتظر حتى تعمل الكاميرا أولاً")
            return
        save_frame(state["last_frame"], "Manual")
        refresh_gallery()
        snack("تم حفظ الصورة في المعرض")

    async def start_camera(_=None):
        try:
            cams = await camera.get_available_cameras()
            if not cams:
                camera_status.value = "No camera found"
                page.update()
                return
            # Prefer the back camera.
            selected = next((c for c in cams if c.lens_direction == fc.CameraLensDirection.BACK), cams[0])
            state["camera"] = selected
            await camera.initialize(
                description=selected,
                resolution_preset=fc.ResolutionPreset.LOW,
                enable_audio=False,
                image_format_group=fc.ImageFormatGroup.JPEG,
            )
            if not await camera.supports_image_streaming():
                camera_status.value = "Camera streaming not supported on this device"
                page.update()
                return
            await camera.start_image_stream()
            state["initialized"] = True
            state["streaming"] = True
            camera_status.value = "Camera active / الكاميرا تعمل"
            page.update()
        except Exception as ex:
            camera_status.value = f"Camera error: {ex}"
            page.update()

    def on_stream_image(e: fc.CameraImageEvent):
        try:
            # Throttle processing to avoid overloading the phone.
            if state["frame_count"] % 2:
                state["frame_count"] += 1
                return
            frame, detected = process_frame(e.bytes)
            if frame is None:
                return
            state["last_frame"] = frame.copy()
            ok, encoded = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 78])
            if ok:
                frame_image.src = encoded.tobytes()
                frame_image.update()
            if detected:
                detection_status.value = "PERSON DETECTED / تم اكتشاف شخص"
                detection_status.color = "#FF5555"
                now = time.monotonic()
                if state["security"] and now - state["last_alert"] > 5:
                    state["last_alert"] = now
                    save_frame(frame, "Alert")
                    try:
                        alarm.play()
                    except Exception:
                        pass
            else:
                detection_status.value = "No person detected / لا يوجد شخص"
                detection_status.color = "#A9C0B8"
            detection_status.update()
        except Exception:
            # Keep the camera preview alive if a single frame cannot be decoded.
            return

    camera.on_stream_image = on_stream_image

    def change_password(_):
        new_pass = ft.TextField(label="New password", password=True, can_reveal_password=True)
        def save_pass(_):
            nonlocal password
            value = new_pass.value or ""
            if len(value) < 4:
                snack("كلمة المرور يجب أن تكون 4 أحرف على الأقل")
                return
            password = value
            password_file.write_text(password, encoding="utf-8")
            close_dialog()
            snack("تم تغيير كلمة المرور")
        page.dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Change Password / تغيير الرمز"),
            content=new_pass,
            actions=[
                ft.TextButton("Cancel", on_click=lambda e: close_dialog()),
                ft.FilledButton("Save", on_click=save_pass),
            ],
        )
        page.dialog.open = True
        page.update()

    def build_main_screen():
        page.clean()
        page.add(
            ft.Column(
                expand=True,
                spacing=12,
                controls=[
                    ft.Row(
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        controls=[
                            ft.Row(
                                controls=[
                                    ft.Icon(ft.Icons.SHIELD_MOON, color="#27D98B", size=30),
                                    ft.Column(
                                        spacing=0,
                                        controls=[
                                            ft.Text("CAMERA SECURITY", size=19, weight=ft.FontWeight.BOLD),
                                            ft.Text("نظام الكاميرا الأمنية", size=12, color="#91AFA5"),
                                        ],
                                    ),
                                ],
                            ),
                            security_badge,
                        ],
                    ),
                    ft.Container(
                        height=330,
                        bgcolor="#02080D",
                        border=ft.border.all(1, "#1D5B48"),
                        border_radius=16,
                        padding=4,
                        content=ft.Stack(
                            expand=True,
                            controls=[
                                frame_image,
                                ft.Container(
                                    alignment=ft.Alignment.TOP_LEFT,
                                    padding=8,
                                    content=ft.Text("LIVE", color="#FF5555", weight=ft.FontWeight.BOLD, size=12),
                                ),
                            ],
                        ),
                    ),
                    camera_status,
                    detection_status,
                    ft.Row(
                        wrap=True,
                        alignment=ft.MainAxisAlignment.CENTER,
                        controls=[
                            ft.FilledButton("Start Camera", icon=ft.Icons.VIDEOCAM, on_click=start_camera),
                            ft.FilledButton("Capture", icon=ft.Icons.CAMERA_ALT, on_click=capture_manual),
                            ft.FilledButton("Security ON/OFF", icon=ft.Icons.SHIELD, on_click=set_security),
                        ],
                    ),
                    filter_dropdown,
                    ft.Row(
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        controls=[
                            ft.Text("Gallery / المعرض", weight=ft.FontWeight.BOLD, size=16),
                            ft.TextButton("Refresh", icon=ft.Icons.REFRESH, on_click=lambda e: refresh_gallery()),
                        ],
                    ),
                    ft.Container(
                        bgcolor="#101F2D",
                        border_radius=12,
                        padding=8,
                        content=gallery_list,
                    ),
                    ft.Row(
                        wrap=True,
                        controls=[
                            ft.OutlinedButton("Change Password", icon=ft.Icons.KEY, on_click=change_password),
                            ft.OutlinedButton("About", icon=ft.Icons.INFO_OUTLINE, on_click=show_about),
                        ],
                    ),
                ],
            )
        )
        refresh_gallery()
        # Initialize the camera after the UI has been attached.
        page.run_task(start_camera)

    build_login()


if __name__ == "__main__":
    ft.run(main)
