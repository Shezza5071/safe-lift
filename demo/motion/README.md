# Safe Lift motion graphic

`../safe_lift_motion.mp4`: 68 s, 1920x1080, 30 fps, no audio (plays under a live voice-over).

Re-render after editing `film.py` (needs Pillow, ffmpeg and the Inter Display font):

```bash
mkdir -p parts
for s in 01_title 02_people 03_workers 04_insight 05_how 06_gate 07_alarm 08_privacy 09_close; do
  python film.py render $s parts/$s.mp4; echo "file 'parts/$s.mp4'" >> list.txt; done
ffmpeg -f concat -safe 0 -i list.txt -c copy -movflags +faststart ../safe_lift_motion.mp4
```

Check one frame first: `python film.py still 07_alarm 9.5 frame.png`.

Sources shown on screen: AIHW GEN data (people using aged care by region, 30 June 2025, via H4H); Safe Work Australia WHS profile, nursing, care and support workforce; SafeWork SA (Oct 2024); Cochrane review CD005958.pub3; Model Code of Practice: Hazardous manual tasks; REBA (Hignett & McAtamney 2000).
