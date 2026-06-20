#!/home/amirreza-a2a/Scripts/.scriptsENV/bin/python3

import os
import re
import subprocess
from datetime import datetime

def get_time_from_xml(xml_file):
    if not os.path.exists(xml_file):
        return None
    try:
        with open(xml_file, 'r', encoding='utf-8') as f:
            content = f.read()
            match = re.search(r"([A-Z][a-z]{2}\s+[A-Z][a-z]{2}\s+\d{2}\s+\d{2}:\d{2}:\d{2}\s+\d{4})", content)
            if match:
                return datetime.strptime(match.group(1), "%a %b %d %H:%M:%S %Y")
    except Exception:
        pass
    return None

def get_duration(file_path):
    cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", file_path]
    try:
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        return float(res.stdout.strip())
    except Exception:
        return 0.0

def has_audio_stream(file_path):
    cmd = ["ffprobe", "-v", "error", "-select_streams", "a", "-show_entries", "stream=codec_type", "-of", "default=noprint_wrappers=1:nokey=1", file_path]
    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    return "audio" in res.stdout.strip()

def analyze_timeline():
    print("🔍 فاز ۱: آنالیز تایم‌لاین و مهندسی زمان‌بندی...")
    audio_candidates = [f for f in os.listdir('.') if f.startswith('cameraVoip') and f.endswith('.flv')]
    video_candidates = [f for f in os.listdir('.') if f.startswith('screenshare') and f.endswith('.flv')]
    
    valid_audios = [a for a in audio_candidates if has_audio_stream(a)]
    
    assets = []
    all_times = []
    
    for f in valid_audios + video_candidates:
        start_dt = get_time_from_xml(f.replace('.flv', '.xml'))
        if start_dt:
            all_times.append(start_dt)
            assets.append({
                'file': f, 
                'start_dt': start_dt, 
                'type': 'audio' if f in valid_audios else 'video'
            })
    
    if not all_times:
        print("❌ هیچ متادیتای زمانی (XML) یافت نشد.")
        return None
        
    T0 = min(all_times)
    
    for asset in assets:
        asset['offset_sec'] = (asset['start_dt'] - T0).total_seconds()
        asset['duration'] = get_duration(asset['file'])
        asset['end_sec'] = asset['offset_sec'] + asset['duration']
        
    total_duration = max([a['end_sec'] for a in assets])
    return {'T0': T0, 'assets': assets, 'total_duration': total_duration}

def process_media(timeline):
    print("🛠 فاز ۲ و ۳: تولید فیلترهای مهندسی صدا و تصویر (Gap Filling)...")
    assets = timeline['assets']
    total_dur = timeline['total_duration']

    audios = [a for a in assets if a['type'] == 'audio']
    videos = [v for v in assets if v['type'] == 'video']
    videos.sort(key=lambda x: x['offset_sec'])

    inputs = []
    filter_complex = []
    input_idx = 0

    # ----- پردازش صدا -----
    amix_labels = ""
    for a in audios:
        inputs.append(f"-i {a['file']}")
        delay_ms = int(a['offset_sec'] * 1000)
        filter_complex.append(f"[{input_idx}:a]adelay={delay_ms}|{delay_ms}[a{input_idx}]")
        amix_labels += f"[a{input_idx}]"
        input_idx += 1

    if audios:
        filter_complex.append(f"{amix_labels}amix=inputs={len(audios)}:dropout_transition=0[aout]")
    else:
        # اگر کلاسی کلاً صدا نداشت، یک صدای خالی (سکوت) تولید کن
        inputs.append("-f lavfi -i anullsrc")
        filter_complex.append(f"[{input_idx}:a]anull[aout]")
        input_idx += 1

    # ----- پردازش تصویر و پر کردن گپ‌ها -----
    video_concat_labels = ""
    concat_count = 0
    curr_time = 0.0

    # استانداردسازی فریم‌ریت و رزولوشن برای چسباندن (Concat)
    fps = 10
    resolution = "1920x1088"

    for v in videos:
        inputs.append(f"-i {v['file']}")
        v_idx = input_idx
        input_idx += 1

        gap = v['offset_sec'] - curr_time
        if gap > 0.5: # پر کردن گپ با ویدیوی سیاه
            filter_complex.append(f"color=c=black:s={resolution}:r={fps}:d={gap}[b{concat_count}]")
            video_concat_labels += f"[b{concat_count}]"
            concat_count += 1

        # نرمال‌سازی ویدیوی اصلی
        filter_complex.append(f"[{v_idx}:v]fps={fps},scale={resolution},format=yuv420p[v{concat_count}]")
        video_concat_labels += f"[v{concat_count}]"
        concat_count += 1

        curr_time = v['end_sec']

    # پر کردن گپ احتمالی از آخرین ویدیو تا پایان کلاس
    end_gap = total_dur - curr_time
    if end_gap > 0.5:
        filter_complex.append(f"color=c=black:s={resolution}:r={fps}:d={end_gap}[b{concat_count}]")
        video_concat_labels += f"[b{concat_count}]"
        concat_count += 1

    if concat_count > 0:
        filter_complex.append(f"{video_concat_labels}concat=n={concat_count}:v=1:a=0[vout]")
    else:
        # اگر کلاسی کلاً اسکرین‌شیر نداشت، کل ویدیو رو سیاه کن
        filter_complex.append(f"color=c=black:s={resolution}:r={fps}:d={total_dur}[vout]")

    filter_str = "; ".join(filter_complex)
    input_str = " ".join(inputs)
    
    out_file = "final_class_synced.mp4"

    # ----- فاز ۴: رندر نهایی -----
    print(f"\n🎬 فاز ۴: در حال رندر به H.264 (این پروسه زمان‌بر است، لطفا شکیبا باشید)...")
    cmd = f'ffmpeg -y {input_str} -filter_complex "{filter_str}" -map "[vout]" -map "[aout]" -c:v libx264 -preset veryfast -crf 26 -c:a aac -b:a 64k -t {total_dur} {out_file}'
    
    result = subprocess.run(cmd, shell=True)
    if result.returncode == 0:
        print(f"\n✨ عالی! تدوین کلاس به پایان رسید: {out_file}")
    else:
        print("\n❌ خطایی در حین اجرای FFmpeg رخ داد.")

def main():
    timeline = analyze_timeline()
    if timeline:
        process_media(timeline)

if __name__ == "__main__":
    main()