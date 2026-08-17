import os
import sys
import cv2
import json
import time
import shutil
import tempfile
import subprocess
import numpy as np
import imageio_ffmpeg
from PyQt6.QtCore import QThread, pyqtSignal

def get_ffmpeg_path():
    """Returns the absolute path to FFmpeg binary from imageio-ffmpeg or PATH."""
    try:
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception as e:
        print(f"Error locating FFmpeg: {e}")
        return "ffmpeg"

def get_media_properties(video_path):
    """
    Extracts video and audio metadata using OpenCV and/or FFmpeg.
    Returns a dictionary with width, height, fps, duration, total_frames,
    has_audio, thumbnail RGB numpy array, and file size.
    """
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"File not found: {video_path}")
        
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise ValueError(f"Could not open video: {video_path}")
        
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    if fps <= 0 or np.isnan(fps):
        fps = 30.0
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    duration = total_frames / fps if fps > 0 else 0
    
    # Extract middle frame for thumbnail
    middle_idx = max(0, total_frames // 2)
    cap.set(cv2.CAP_PROP_POS_FRAMES, middle_idx)
    ret, frame_bgr = cap.read()
    if not ret:
        cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
        ret, frame_bgr = cap.read()
        
    cap.release()
    
    thumbnail_rgb = None
    if ret and frame_bgr is not None:
        thumbnail_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        
    # Check audio stream presence via ffmpeg
    has_audio = False
    ffmpeg_exe = get_ffmpeg_path()
    try:
        startupinfo = None
        if os.name == 'nt':
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = subprocess.SW_HIDE
            
        probe_cmd = [
            ffmpeg_exe,
            "-i", video_path,
            "-hide_banner"
        ]
        result = subprocess.run(
            probe_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            startupinfo=startupinfo,
            text=True,
            errors="ignore"
        )
        output = result.stderr + result.stdout
        if "Audio:" in output:
            has_audio = True
            
        # Extract precise duration from ffmpeg if opencv duration was 0 or inaccurate
        if "Duration:" in output:
            import re
            m = re.search(r"Duration:\s*(\d+):(\d+):(\d+\.\d+)", output)
            if m:
                h, mins, s = map(float, m.groups())
                ff_dur = h * 3600 + mins * 60 + s
                if ff_dur > 0:
                    duration = ff_dur
    except Exception as e:
        print(f"Probe error on {video_path}: {e}")
        
    # Timestamp for download/creation order
    try:
        c_time = os.path.getctime(video_path)
        m_time = os.path.getmtime(video_path)
        file_ts = min(c_time, m_time)
        import datetime
        dt_str = datetime.datetime.fromtimestamp(file_ts).strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        file_ts = time.time()
        dt_str = ""

    return {
        "path": video_path,
        "name": os.path.basename(video_path),
        "width": width,
        "height": height,
        "fps": fps,
        "total_frames": total_frames,
        "duration": duration,
        "has_audio": has_audio,
        "thumbnail": thumbnail_rgb,
        "size_bytes": os.path.getsize(video_path) if os.path.exists(video_path) else 0,
        "timestamp": file_ts,
        "datetime_str": dt_str
    }

def format_duration(seconds):
    """Formats seconds into MM:SS or HH:MM:SS."""
    if not seconds or seconds < 0:
        return "00:00"
    seconds = int(round(seconds))
    mins, secs = divmod(seconds, 60)
    hours, mins = divmod(mins, 60)
    if hours > 0:
        return f"{hours:02d}:{mins:02d}:{secs:02d}"
    return f"{mins:02d}:{secs:02d}"

def format_file_size(size_bytes):
    """Formats bytes into human readable size (KB, MB, GB)."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"

class VideoCombinerWorker(QThread):
    """
    Worker thread to merge multiple video files sequentially with smooth fade transitions
    (video xfade and audio acrossfade) without freezing the GUI.
    """
    progress_changed = pyqtSignal(int)          # Current step progress (0-100)
    overall_progress_changed = pyqtSignal(int)  # Overall merge progress (0-100)
    status_changed = pyqtSignal(str)           # Informative text
    finished = pyqtSignal(bool, str, dict)      # (success, message, output_metadata)
    
    def __init__(self, video_paths, output_path, transition_duration=0.75, transition_type="fade"):
        super().__init__()
        self.video_paths = list(video_paths)
        self.output_path = output_path
        self.transition_duration = float(transition_duration)
        self.transition_type = transition_type  # 'fade', 'dissolve', 'wipeleft', 'fadeblack', etc.
        self._is_cancelled = False
        self._current_process = None
        self._temp_dir = None
        
    def cancel(self):
        """Cancels the active operation and terminates any running FFmpeg subprocess."""
        self._is_cancelled = True
        if self._current_process is not None:
            try:
                self._current_process.terminate()
                time.sleep(0.2)
                if self._current_process.poll() is None:
                    self._current_process.kill()
            except Exception as e:
                print(f"Error terminating FFmpeg process: {e}")
                
    def run(self):
        self._is_cancelled = False
        n_videos = len(self.video_paths)
        
        if n_videos < 2:
            self.finished.emit(False, "Please select at least 2 videos to combine.", {})
            return
            
        # Check files existence
        for p in self.video_paths:
            if not os.path.exists(p):
                self.finished.emit(False, f"Video file not found: {os.path.basename(p)}", {})
                return
                
        try:
            self._temp_dir = tempfile.mkdtemp(prefix="dola_merge_")
            self.status_changed.emit("Analyzing input videos properties...")
            self.overall_progress_changed.emit(5)
            
            # Step 1: Probe each video
            clip_infos = []
            max_w = 0
            max_h = 0
            target_fps = 30.0
            
            for idx, p in enumerate(self.video_paths):
                if self._is_cancelled:
                    break
                info = get_media_properties(p)
                clip_infos.append(info)
                if info["width"] > max_w:
                    max_w = info["width"]
                if info["height"] > max_h:
                    max_h = info["height"]
                    
            if self._is_cancelled:
                self._cleanup()
                self.finished.emit(False, "Combine operation cancelled.", {})
                return
                
            # Ensure width and height are even numbers (requirement for h264/yuv420p)
            max_w = max(1280, (max_w + 1) // 2 * 2)
            max_h = max(720, (max_h + 1) // 2 * 2)
            
            self.status_changed.emit(f"Target resolution: {max_w}x{max_h} @ {int(target_fps)} fps")
            self.overall_progress_changed.emit(10)
            
            # Step 2: Normalize clips
            # Each clip is normalized to:
            # - Exact resolution (aspect ratio preserved using black padding)
            # - 30 fps
            # - yuv420p pixel format
            # - Stereo audio at 44.1kHz (or silent audio track generated if clip had none)
            normalized_clips = []
            normalized_durations = []
            
            ffmpeg_exe = get_ffmpeg_path()
            startupinfo = None
            if os.name == 'nt':
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = subprocess.SW_HIDE
                
            total_clips = len(clip_infos)
            for idx, info in enumerate(clip_infos):
                if self._is_cancelled:
                    break
                    
                in_path = info["path"]
                base_name = os.path.basename(in_path)
                out_norm_path = os.path.join(self._temp_dir, f"norm_{idx:03d}.mp4")
                
                self.status_changed.emit(f"Normalizing clip ({idx+1}/{total_clips}): {base_name}...")
                
                # Video filter: scale down/up to fit inside max_w x max_h, pad to exact max_w x max_h with black bars
                # setsar=1 ensures square pixels
                vf_scale_pad = (
                    f"scale={max_w}:{max_h}:force_original_aspect_ratio=decrease,"
                    f"pad={max_w}:{max_h}:(ow-iw)/2:(oh-ih)/2:black,"
                    f"fps={target_fps},"
                    f"setsar=1,"
                    f"format=yuv420p"
                )
                
                # Audio filter:
                # If audio is present, resample to 44100Hz stereo.
                # If no audio, generate silent audio matching the clip duration.
                cmd = [
                    ffmpeg_exe, "-y",
                    "-i", in_path
                ]
                
                if info["has_audio"]:
                    cmd.extend([
                        "-vf", vf_scale_pad,
                        "-af", "aresample=async=1:sample_rate=44100,aformat=sample_fmts=fltp:sample_rates=44100:channel_layouts=stereo",
                        "-c:v", "libx264",
                        "-preset", "ultrafast",
                        "-crf", "18",
                        "-c:a", "aac",
                        "-b:a", "192k",
                        "-shortest",
                        out_norm_path
                    ])
                else:
                    # Generate silent audio via anevalsrc
                    dur = max(0.5, info["duration"])
                    cmd = [
                        ffmpeg_exe, "-y",
                        "-i", in_path,
                        "-f", "lavfi", "-t", str(dur), "-i", "anullsrc=r=44100:cl=stereo",
                        "-vf", vf_scale_pad,
                        "-c:v", "libx264",
                        "-preset", "ultrafast",
                        "-crf", "18",
                        "-c:a", "aac",
                        "-b:a", "192k",
                        "-shortest",
                        out_norm_path
                    ]
                    
                self._current_process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    startupinfo=startupinfo
                )
                
                _, stderr_data = self._current_process.communicate()
                
                if self._is_cancelled:
                    break
                    
                if self._current_process.returncode != 0:
                    err_msg = stderr_data.decode("utf-8", errors="ignore") if stderr_data else "Unknown error"
                    raise RuntimeError(f"Error normalizing video '{base_name}':\n{err_msg[-400:]}")
                    
                # Probe actual normalized clip duration
                norm_info = get_media_properties(out_norm_path)
                normalized_durations.append(norm_info["duration"])
                normalized_clips.append(out_norm_path)
                
                # Update progress
                clip_pct = int(((idx + 1) / total_clips) * 100)
                overall_pct = 10 + int(((idx + 1) / total_clips) * 35)
                self.progress_changed.emit(clip_pct)
                self.overall_progress_changed.emit(overall_pct)
                
            if self._is_cancelled:
                self._cleanup()
                self.finished.emit(False, "Combine operation cancelled.", {})
                return
                
            # Step 3: Construct FFmpeg xfade + acrossfade filter complex
            self.status_changed.emit("Building smooth transition pipeline...")
            self.overall_progress_changed.emit(50)
            
            trans_d = self.transition_duration
            # Ensure transition duration doesn't exceed half the shortest clip
            min_clip_dur = min(normalized_durations)
            if trans_d >= min_clip_dur / 2.0:
                trans_d = max(0.2, min_clip_dur / 2.0 - 0.1)
                
            # Transition type mapping
            xfade_transition = self.transition_type.lower()
            if xfade_transition not in ["fade", "dissolve", "fadeblack", "wipeleft", "wiperight", "smoothleft", "smoothright", "circlecrop"]:
                xfade_transition = "fade"
                
            # Build filter graph
            filter_parts = []
            n = len(normalized_clips)
            
            last_v = "[0:v]"
            last_a = "[0:a]"
            current_offset = normalized_durations[0] - trans_d
            
            for i in range(1, n):
                next_v = f"[{i}:v]"
                next_a = f"[{i}:a]"
                out_v = f"[v_trans_{i}]" if i < n - 1 else "[v_out]"
                out_a = f"[a_trans_{i}]" if i < n - 1 else "[a_out]"
                
                # Video xfade
                filter_parts.append(
                    f"{last_v}{next_v}xfade=transition={xfade_transition}:duration={trans_d:.2f}:offset={current_offset:.3f}{out_v}"
                )
                
                # Audio acrossfade
                filter_parts.append(
                    f"{last_a}{next_a}acrossfade=d={trans_d:.2f}:c1=tri:c2=tri{out_a}"
                )
                
                last_v = out_v
                last_a = out_a
                
                if i < n - 1:
                    current_offset += normalized_durations[i] - trans_d
                    
            filter_complex_str = ";".join(filter_parts)
            
            # Step 4: Execute final merge FFmpeg command
            self.status_changed.emit("Rendering combined video with smooth transitions...")
            self.overall_progress_changed.emit(55)
            
            final_cmd = [
                ffmpeg_exe, "-y",
                "-nostats",
                "-loglevel", "error"
            ]
            for clip_p in normalized_clips:
                final_cmd.extend(["-i", clip_p])
                
            final_cmd.extend([
                "-filter_complex", filter_complex_str,
                "-map", "[v_out]",
                "-map", "[a_out]",
                "-c:v", "libx264",
                "-preset", "medium",
                "-crf", "19",
                "-pix_fmt", "yuv420p",
                "-c:a", "aac",
                "-b:a", "256k",
                "-progress", "pipe:1",
                self.output_path
            ])
            
            # Ensure destination directory exists
            os.makedirs(os.path.dirname(os.path.abspath(self.output_path)), exist_ok=True)
            
            self._current_process = subprocess.Popen(
                final_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                startupinfo=startupinfo,
                universal_newlines=True,
                errors="ignore"
            )
            
            # Total expected final duration
            total_final_duration = sum(normalized_durations) - (n - 1) * trans_d
            stderr_buffer = []
            
            # Monitor progress
            while True:
                if self._is_cancelled:
                    break
                line = self._current_process.stdout.readline()
                if not line:
                    if self._current_process.poll() is not None:
                        break
                    time.sleep(0.01)
                    continue
                    
                line = line.strip()
                if line.startswith("out_time_us="):
                    try:
                        us = int(line.split("=")[1])
                        sec = us / 1_000_000.0
                        if total_final_duration > 0:
                            pct = min(99, int((sec / total_final_duration) * 100))
                            overall_pct = 55 + int(pct * 0.44)
                            self.progress_changed.emit(pct)
                            self.overall_progress_changed.emit(min(99, overall_pct))
                    except:
                        pass
                elif line.startswith("progress=") and line.endswith("end"):
                    break
                elif not line.startswith("frame=") and not line.startswith("fps=") and not line.startswith("bitrate=") and not line.startswith("total_size=") and not line.startswith("out_time=") and not line.startswith("dup_frames=") and not line.startswith("drop_frames=") and not line.startswith("speed="):
                    # Capture potential error messages from stderr that are routed to stdout
                    if line:
                        stderr_buffer.append(line)
                    
            self._current_process.wait()
            
            if self._is_cancelled:
                self._cleanup()
                if os.path.exists(self.output_path):
                    try: os.remove(self.output_path)
                    except: pass
                self.finished.emit(False, "Combine operation cancelled by user.", {})
                return
                
            if self._current_process.returncode != 0:
                err_text = "\n".join(stderr_buffer[-10:]) if stderr_buffer else "FFmpeg merge failed."
                self._cleanup()
                self.finished.emit(False, f"Combine failed: {err_text}", {})
                return
                
            # Verify output file
            if not os.path.exists(self.output_path) or os.path.getsize(self.output_path) == 0:
                self._cleanup()
                self.finished.emit(False, "Combined output file was not created properly.", {})
                return
                
            self.overall_progress_changed.emit(100)
            self.progress_changed.emit(100)
            self.status_changed.emit("Combined video generated successfully!")
            
            # Get final output metadata
            final_meta = get_media_properties(self.output_path)
            
            self._cleanup()
            self.finished.emit(True, f"Successfully merged {n_videos} videos with smooth transitions!", final_meta)
            
        except Exception as e:
            self._cleanup()
            if os.path.exists(self.output_path):
                try: os.remove(self.output_path)
                except: pass
            if not self._is_cancelled:
                self.finished.emit(False, f"Error combining videos:\n{str(e)}", {})
            else:
                self.finished.emit(False, "Combine operation cancelled.", {})
                
    def _cleanup(self):
        """Removes temporary working directory."""
        if self._temp_dir and os.path.exists(self._temp_dir):
            try:
                shutil.rmtree(self._temp_dir, ignore_errors=True)
            except Exception as e:
                print(f"Error cleaning temp dir: {e}")
            self._temp_dir = None
