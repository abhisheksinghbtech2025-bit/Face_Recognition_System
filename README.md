<<<<<<< HEAD
# 🔐 Advanced Face Detection Security System

A complete Python security system with face detection, recognition,
liveness detection, multi-camera support, alerts, attendance and reports.

---

## 📁 Project Structure

```
FaceSecuritySystem/
├── main.py                    ← Run this to start
├── setup.py                   ← Run once to set up DB
├── requirements.txt
├── config/
│   └── config.py              ← All settings
├── database/
│   ├── schema.sql
│   └── db_manager.py
├── modules/
│   ├── face_detector.py
│   ├── face_recognizer.py
│   ├── liveness.py
│   ├── low_light.py
│   ├── camera_manager.py
│   ├── camera_coordinator.py
│   ├── dataset_manager.py
│   ├── logger.py
│   ├── alert_manager.py
│   └── report_exporter.py
├── ui/
│   ├── splash_screen.py
│   ├── login_window.py
│   ├── dashboard.py
│   ├── camera_panel.py
│   ├── multi_camera_panel.py
│   ├── dataset_panel.py
│   ├── logs_panel.py
│   ├── alerts_panel.py
│   └── reports_panel.py
├── dataset/faces/             ← Face images
├── logs/snapshots/            ← Alert snapshots
└── exports/                   ← PDF & Excel files
```

---

## ⚡ Quick Start

```bash
pip install -r requirements.txt
python setup.py
python main.py
```

**Default login:** admin / Admin@123

---

## 🛠 Common Fixes

| Error | Fix |
|-------|-----|
| ModuleNotFoundError | pip install -r requirements.txt |
| MySQL connection error | Start MySQL, check password in config.py |
| dlib fails to install | pip install cmake first |
| Camera not opening | Try index 0, 1, or 2 |
=======
# Face_Recognition_System
Face Recognition Security System with attendance tracking, liveness detection, multi-camera support, and centralized database. Includes admin dashboard, alerts system, and report export.
>>>>>>> 571fcee6982ad7c43515b1e443e6110e1ae65d17
