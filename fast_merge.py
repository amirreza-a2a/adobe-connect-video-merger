#!/home/amirreza-a2a/Scripts/.scriptsENV/bin/python3

import os
import re
import subprocess
from datetime import datetime

def get_time_from_xml(xml_file):
    """
    Extract the exact recording date and time from the XML metadata file.
    Example format in XML: Sat May 23 10:10:59 2026
    """
    if not os.path.exists(xml_file):
        return None
    try:
        with open(xml_file, 'r', encoding='utf-8') as f:
            content = f.read()
            match = re.search(r"([A-Z][a-z]{2}\s+[A-Z][a-z]{2}\s+\d{2}\s+\d{2}:\d{2}:\d{2}\s+\d{4})", content)
            if match:
                return datetime.strptime(match.group(1), "%a %b %d %H:%M:%S %Y")
    except Exception as e:
        print(f"⚠️ Error reading XML file {xml_file}: {e}")
    return None

def has_audio_stream(file_path):
    cmd = f"ffprobe -v error -select_streams a -show_entries stream=codec_type -of default=noprint_wrappers=1:nokey=1 {file_path}"
    res = subprocess.run(cmd.split(), stdout=subprocess.PIPE, text=True)
    return "audio" in res.stdout.strip()

def main():
    print("🔍 Parsing XML files and extracting timestamps...")
    
    # 1. فیلتر کردن فایل‌های صوتی خراب/خالی
    all_audio_candidates = sorted([f for f in os.listdir('.') if f.startswith('cameraVoip') and f.endswith('.flv')])
    audio_files = []
    for a in all_audio_candidates:
        if has_audio_stream(a):
            audio_files.append(a)
        else:
            print(f"⚠️ فایل {a} استریم صوتی ندارد (احتمالاً خالی است) و نادیده گرفته شد.")

    # 2. پیدا کردن هوشمند ویدیوی اصلی
    screenshares = [f for f in os.listdir('.') if f.startswith('screenshare') and f.endswith('.flv')]
    if screenshares:
        main_video = max(screenshares, key=os.path.getsize)
    else:
        video_candidates = ['mainstream.flv', 'ftstage2.flv']
        main_video = next((v for v in video_candidates if os.path.exists(v)), None)

    if not main_video or not audio_files:
        print("❌ Main video file or audio tracks could not be found.")
        return

    print(f"🎥 Main Video: {main_video}")
    print(f"🎵 Audio Files: {', '.join(audio_files)}")

    times = {}
    v_time = get_time_from_xml(main_video.replace('.flv', '.xml'))
    if v_time:
        times[main_video] = v_time
        
    for a in audio_files:
        a_time = get_time_from_xml(a.replace('.flv', '.xml'))
        if a_time:
            times[a] = a_time

    if not times:
        print("❌ Time metadata not found in any XML files.")
        return

    base_time = min(times.values())

    v_delay_sec = (times.get(main_video, base_time) - base_time).total_seconds()
    v_offset_cmd = f"-itsoffset {v_delay_sec} " if v_delay_sec > 0 else ""
    
    inputs = [f"{v_offset_cmd}-i {main_video}"]
    filter_complex = []
    amix_inputs = ""
    
    for idx, a in enumerate(audio_files, start=1):
        inputs.append(f"-i {a}")
        a_delay_ms = int((times.get(a, base_time) - base_time).total_seconds() * 1000)
        filter_complex.append(f"[{idx}:a]adelay={a_delay_ms}|{a_delay_ms}[a{idx}]")
        amix_inputs += f"[a{idx}]"

    filter_complex.append(f"{amix_inputs}amix=inputs={len(audio_files)}:dropout_transition=0[aout]")

    filter_str = "; ".join(filter_complex)
    inputs_str = " ".join(inputs)
    output_file = "final_class_synced.mkv"
    
    # 3. تغییر در مپ ویدیو (اضافه شدن علامت سؤال)
    cmd = f'ffmpeg -y {inputs_str} -filter_complex "{filter_str}" -map 0:v? -map "[aout]" -c:v copy -c:a aac {output_file}'

    print("\n🎬 Rendering and mixing via FFmpeg (this might take a few moments)...")
    
    result = subprocess.run(cmd, shell=True)
    if result.returncode == 0:
        print(f"\n✨ Processing complete! Final video generated: {output_file}")
    else:
        print("\n❌ FFmpeg execution failed.")

if __name__ == "__main__":
    main()