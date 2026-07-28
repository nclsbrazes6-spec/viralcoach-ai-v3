import subprocess
from pathlib import Path

def extract_frames(video_path: str, output_folder: str):
    output = Path(output_folder)
    output.mkdir(parents=True, exist_ok=True)

    subprocess.run([
        "ffmpeg",
        "-y",
        "-i", video_path,
        "-vf", "fps=1",
        f"{output}/frame_%04d.jpg"
    ], check=True)

    return list(output.glob("*.jpg"))


def extract_audio(video_path: str, output_file: str):
    output = Path(output_file)
    output.parent.mkdir(parents=True, exist_ok=True)

    subprocess.run([
        "ffmpeg",
        "-y",
        "-i", video_path,
        "-vn",
        "-acodec", "pcm_s16le",
        "-ar", "16000",
        "-ac", "1",
        str(output)
    ], check=True)

    return output