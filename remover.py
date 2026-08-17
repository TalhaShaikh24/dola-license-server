import os
import cv2
import numpy as np
import subprocess
import imageio_ffmpeg
import time
import concurrent.futures
import threading
from PyQt6.QtCore import QThread, pyqtSignal

def get_video_info(video_path):
    """
    Reads video metadata and returns a dictionary of information.
    """
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"Video file not found: {video_path}")
    
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise ValueError(f"Could not open video file: {video_path}")
        
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    
    # Calculate duration
    duration = 0
    if fps > 0:
        duration = total_frames / fps
        
    cap.release()
    
    return {
        "width": width,
        "height": height,
        "fps": fps,
        "total_frames": total_frames,
        "duration": duration
    }

def get_video_preview_frame(video_path, frame_index=None):
    """
    Extracts a single frame from the video at frame_index (defaults to middle frame).
    Returns the frame as an RGB numpy array and the video info.
    """
    info = get_video_info(video_path)
    total_frames = info["total_frames"]
    
    if frame_index is None or frame_index < 0 or frame_index >= total_frames:
        frame_index = total_frames // 2
        
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise ValueError(f"Could not open video file: {video_path}")
        
    cap.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
    ret, frame = cap.read()
    cap.release()
    
    if not ret:
        # Fallback to the first frame if middle frame fails
        cap = cv2.VideoCapture(video_path)
        ret, frame = cap.read()
        cap.release()
        if not ret:
            raise ValueError(f"Could not read any frames from video: {video_path}")
            
    # Convert BGR to RGB
    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    return frame_rgb, info

def create_mask_for_frame(frame_shape, roi, threshold=200, dilation_size=2, frame_bgr=None):
    """
    Creates a binary mask for the video frame.
    roi: dict containing x, y, width, height, ref_width, ref_height
    threshold: brightness threshold for detecting white text (0-255)
    dilation_size: kernel radius to expand mask boundaries
    frame_bgr: the BGR video frame
    """
    height, width = frame_shape[:2]
    
    # Scale ROI if reference dimensions differ from current frame dimensions
    ref_w = roi.get("ref_width", width)
    ref_h = roi.get("ref_height", height)
    
    rx1 = roi["x"] / ref_w
    ry1 = roi["y"] / ref_h
    rx2 = (roi["x"] + roi["width"]) / ref_w
    ry2 = (roi["y"] + roi["height"]) / ref_h
    
    x1 = int(rx1 * width)
    y1 = int(ry1 * height)
    x2 = int(rx2 * width)
    y2 = int(ry2 * height)
    
    # Clamp to frame boundaries
    x1 = max(0, min(x1, width - 1))
    y1 = max(0, min(y1, height - 1))
    x2 = max(x1 + 1, min(x2, width))
    y2 = max(y1 + 1, min(y2, height))
    
    # Create empty mask
    mask = np.zeros((height, width), dtype=np.uint8)
    
    if frame_bgr is not None:
        # Extract ROI in BGR
        roi_img = frame_bgr[y1:y2, x1:x2]
        
        # Detect bright pixels (white text)
        # B, G, R channels must all be above the threshold
        b_ch = roi_img[:, :, 0]
        g_ch = roi_img[:, :, 1]
        r_ch = roi_img[:, :, 2]
        
        text_cond = (b_ch >= threshold) & (g_ch >= threshold) & (r_ch >= threshold)
        roi_mask = np.where(text_cond, 255, 0).astype(np.uint8)
        
        # Apply dilation to grow the mask slightly to cover edges and anti-aliased shadows
        if dilation_size > 0:
            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (dilation_size * 2 + 1, dilation_size * 2 + 1))
            roi_mask = cv2.dilate(roi_mask, kernel)
            
        mask[y1:y2, x1:x2] = roi_mask
    else:
        # Fallback to full box masking if frame data is missing
        mask[y1:y2, x1:x2] = 255
        
    return mask

def copy_audio_ffmpeg(original_video, processed_video, output_video):
    """
    Merges audio from original_video with the processed_video (which has no audio)
    using the static FFmpeg executable provided by imageio-ffmpeg.
    """
    try:
        ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
    except Exception as e:
        print(f"Could not get FFmpeg executable from imageio-ffmpeg: {e}")
        return False
        
    # Command to copy video stream from processed_video and audio from original_video
    # -map 0:v copy video from first input
    # -map 1:a? copy audio from second input if it exists
    # -c:v copy copies video without re-encoding (since it is already processed)
    # -c:a copy copies audio stream without re-encoding
    cmd = [
        ffmpeg_exe,
        "-y",
        "-i", processed_video,
        "-i", original_video,
        "-map", "0:v",
        "-map", "1:a?",
        "-c:v", "copy",
        "-c:a", "copy",
        output_video
    ]
    
    try:
        # Run subprocess silently on Windows (hide console window)
        startupinfo = None
        if os.name == 'nt':
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = subprocess.SW_HIDE
            
        process = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            startupinfo=startupinfo,
            check=True
        )
        return True
    except subprocess.CalledProcessError as e:
        print(f"FFmpeg error: {e.stderr.decode('utf-8', errors='ignore')}")
        return False
    except Exception as e:
        print(f"FFmpeg execution failed: {e}")
        return False

class WatermarkRemoverWorker(QThread):
    """
    Worker thread to process videos sequentially without blocking the GUI.
    """
    # Signals to communicate with the GUI
    progress_changed = pyqtSignal(int)          # Current video progress (0-100)
    batch_progress_changed = pyqtSignal(int)    # Overall folder batch progress (0-100)
    status_changed = pyqtSignal(str)           # Informative text status
    finished = pyqtSignal(bool, str)            # (success_status, summary_message)
    videos_processed = pyqtSignal(list)         # List of successfully processed output file paths
    
    def __init__(self, video_paths, output_dir, roi, threshold=200, dilation_size=2, 
                 inpaint_radius=3, inpaint_method="Telea", is_batch=False, mask_mode="Static Text",
                 is_overwrite=False, cpu_threads=1):
        super().__init__()
        self.video_paths = video_paths
        self.output_dir = output_dir
        self.roi = roi
        self.threshold = threshold
        self.dilation_size = dilation_size
        self.inpaint_radius = inpaint_radius
        self.inpaint_method = cv2.INPAINT_TELEA if inpaint_method == "Telea" else cv2.INPAINT_NS
        self.is_batch = is_batch
        self.mask_mode = mask_mode
        self.is_overwrite = is_overwrite
        self.cpu_threads = cpu_threads
        self._is_cancelled = False
        self.processed_output_paths = []
        
    def cancel(self):
        self._is_cancelled = True
        
    def run(self):
        self._is_cancelled = False
        total_videos = len(self.video_paths)
        
        if total_videos == 0:
            self.finished.emit(False, "No video files selected.")
            return
            
        processed_count = 0
        errors = []
        
        for idx, video_path in enumerate(self.video_paths):
            if self._is_cancelled:
                break
                
            video_name = os.path.basename(video_path)
            self.status_changed.emit(f"Processing ({idx+1}/{total_videos}): {video_name}")
            
            # Formulate output paths
            if self.is_overwrite:
                # We will process to a temporary file, then replace the original
                dir_name = os.path.dirname(video_path)
                name_part, ext = os.path.splitext(video_name)
                
                temp_silent_path = os.path.join(dir_name, f"temp_silent_{name_part}{ext}")
                temp_final_path = os.path.join(dir_name, f"temp_final_{name_part}{ext}")
                output_path = temp_final_path
            else:
                if self.is_batch:
                    output_path = os.path.join(self.output_dir, video_name)
                    if os.path.abspath(video_path) == os.path.abspath(output_path):
                        name_part, ext = os.path.splitext(video_name)
                        output_path = os.path.join(self.output_dir, f"{name_part}_no_watermark{ext}")
                else:
                    output_path = self.output_dir
                    
                dir_name = os.path.dirname(output_path)
                base_name = os.path.basename(output_path)
                temp_silent_path = os.path.join(dir_name, f"temp_silent_{base_name}")
                temp_final_path = output_path
                
            try:
                success = self._process_single_video(video_path, temp_silent_path)
                
                if success and not self._is_cancelled:
                    self.status_changed.emit(f"Merging audio for: {video_name}")
                    # Copy audio using FFmpeg
                    merge_success = copy_audio_ffmpeg(video_path, temp_silent_path, temp_final_path)
                    
                    # Cleanup the temporary silent video
                    if os.path.exists(temp_silent_path):
                        try:
                            os.remove(temp_silent_path)
                        except Exception as cleanup_err:
                            print(f"Error removing temporary file {temp_silent_path}: {cleanup_err}")
                            
                    if self.is_overwrite:
                        # Replace the original file with the final merged file
                        if merge_success and os.path.exists(temp_final_path):
                            try:
                                os.remove(video_path)
                                os.rename(temp_final_path, video_path)
                                processed_count += 1
                                self.processed_output_paths.append(video_path)
                            except Exception as replace_err:
                                errors.append(f"{video_name}: Failed to replace original file. {str(replace_err)}")
                                if os.path.exists(temp_final_path):
                                    os.remove(temp_final_path)
                        else:
                            # Fallback: if audio merge failed, replace original with silent video
                            if os.path.exists(temp_final_path):
                                os.remove(temp_final_path)
                            if os.path.exists(temp_silent_path):
                                try:
                                    os.remove(video_path)
                                    os.rename(temp_silent_path, video_path)
                                    processed_count += 1
                                    self.processed_output_paths.append(video_path)
                                    errors.append(f"{video_name}: Watermark removed but failed to copy audio.")
                                except Exception as replace_err:
                                    errors.append(f"{video_name}: Failed to replace original file with silent fallback. {str(replace_err)}")
                            else:
                                errors.append(f"{video_name}: Failed to merge audio and replace file.")
                    else:
                        # Standard output mode
                        if merge_success:
                            processed_count += 1
                            self.processed_output_paths.append(output_path)
                        else:
                            # Fallback: if audio merge failed, rename the silent video as the output
                            if os.path.exists(output_path):
                                os.remove(output_path)
                            os.rename(temp_silent_path, output_path)
                            processed_count += 1
                            self.processed_output_paths.append(output_path)
                            errors.append(f"{video_name}: Watermark removed but failed to copy audio.")
                else:
                    # Clean up temp file on failure/cancel
                    if os.path.exists(temp_silent_path):
                        os.remove(temp_silent_path)
                    if self.is_overwrite and os.path.exists(temp_final_path):
                        os.remove(temp_final_path)
                    if not self._is_cancelled:
                        errors.append(f"{video_name}: Failed during frame inpainting.")
                        
            except Exception as e:
                # Cleanup temp files
                if os.path.exists(temp_silent_path):
                    try: os.remove(temp_silent_path)
                    except: pass
                if self.is_overwrite and os.path.exists(temp_final_path):
                    try: os.remove(temp_final_path)
                    except: pass
                errors.append(f"{video_name}: {str(e)}")
                
            # Update batch progress
            if self.is_batch:
                batch_pct = int(((idx + 1) / total_videos) * 100)
                self.batch_progress_changed.emit(batch_pct)
                
        # Emit processed paths if any
        if self.processed_output_paths:
            self.videos_processed.emit(self.processed_output_paths)
            
        # Final status
        if self._is_cancelled:
            self.finished.emit(False, "Process cancelled by user.")
        elif processed_count == total_videos:
            self.finished.emit(True, f"Successfully processed {processed_count} video(s).")
        elif processed_count > 0:
            err_msg = "\n".join(errors)
            self.finished.emit(True, f"Processed {processed_count}/{total_videos} videos successfully. Issues:\n{err_msg}")
        else:
            err_msg = "\n".join(errors)
            self.finished.emit(False, f"Failed to process videos:\n{err_msg}")
            
    def _process_single_video(self, input_path, temp_output_path):
        """
        Reads input video, inpaints watermark frame by frame in parallel, and writes to temp_output_path.
        """
        cap = cv2.VideoCapture(input_path)
        if not cap.isOpened():
            raise ValueError("Could not open input video file.")
            
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        
        if total_frames <= 0:
            total_frames = 1 # Prevent division by zero
            
        # Pre-generate static mask if required (to avoid frame-to-frame flickering)
        static_mask = None
        if self.mask_mode in ["Static Text", "Full Box"]:
            # Grab a frame to generate the static mask (we use the middle frame)
            ref_idx = total_frames // 2
            cap.set(cv2.CAP_PROP_POS_FRAMES, ref_idx)
            ret_ref, ref_frame = cap.read()
            if not ret_ref:
                # Fallback to the first frame
                cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                ret_ref, ref_frame = cap.read()
            
            # Reset back to start of video
            cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            
            if ret_ref:
                if self.mask_mode == "Static Text":
                    static_mask = create_mask_for_frame(ref_frame.shape, self.roi, self.threshold, self.dilation_size, ref_frame)
                else: # Full Box
                    # Pass None for frame_bgr to force full box masking
                    static_mask = create_mask_for_frame(ref_frame.shape, self.roi, self.threshold, self.dilation_size, None)
            
        # Initialize VideoWriter
        # mp4v codec is widely available on Windows out of the box
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        writer = cv2.VideoWriter(temp_output_path, fourcc, fps, (width, height))
        
        if not writer.isOpened():
            # Fallback to another codec if mp4v fails (e.g. XVID)
            fallback_path = temp_output_path.replace(".mp4", "_fallback.avi")
            fourcc_fb = cv2.VideoWriter_fourcc(*'XVID')
            writer = cv2.VideoWriter(fallback_path, fourcc_fb, fps, (width, height))
            if not writer.isOpened():
                cap.release()
                raise ValueError("Could not initialize VideoWriter with standard codecs.")
            temp_output_path = fallback_path
            
        # Initialize parallel frame processing pipeline
        num_workers = self.cpu_threads
        sem = threading.BoundedSemaphore(num_workers * 2)
        results_lock = threading.Lock()
        completed_frames = {}
        worker_exception = None
        
        def inpaint_worker_task(f_idx, f_frame, f_mask):
            nonlocal worker_exception
            try:
                # Apply inpainting (releases the GIL in OpenCV native C++ wrapper)
                res = cv2.inpaint(f_frame, f_mask, self.inpaint_radius, self.inpaint_method)
                with results_lock:
                    completed_frames[f_idx] = res
            except Exception as ex:
                worker_exception = ex
            finally:
                sem.release()
                
        next_frame_to_write = 0
        read_idx = 0
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=num_workers) as executor:
            while True:
                if self._is_cancelled or worker_exception:
                    break
                    
                ret, frame = cap.read()
                if not ret:
                    break
                    
                # Throttle reader to prevent high memory consumption (maximum of num_workers * 2 queued frames)
                sem.acquire()
                
                # Determine mask for this frame
                if static_mask is not None:
                    mask = static_mask
                else:
                    mask = create_mask_for_frame(frame.shape, self.roi, self.threshold, self.dilation_size, frame)
                    
                # Submit inpaint task to CPU thread pool
                executor.submit(inpaint_worker_task, read_idx, frame, mask)
                read_idx += 1
                
                # Write finished frames sequentially to VideoWriter
                while True:
                    with results_lock:
                        if next_frame_to_write in completed_frames:
                            frame_to_write = completed_frames.pop(next_frame_to_write)
                        else:
                            break
                            
                    writer.write(frame_to_write)
                    next_frame_to_write += 1
                    
                    # Emit progress update (throttled)
                    if next_frame_to_write % max(1, total_frames // 100) == 0 or next_frame_to_write == total_frames:
                        pct = int((next_frame_to_write / total_frames) * 100)
                        self.progress_changed.emit(pct)
                        
            # Wait for any active threads to terminate
            executor.shutdown(wait=True)
            
            # Write any leftover frames in order
            while next_frame_to_write < read_idx:
                if worker_exception:
                    raise worker_exception
                    
                frame_to_write = None
                with results_lock:
                    if next_frame_to_write in completed_frames:
                        frame_to_write = completed_frames.pop(next_frame_to_write)
                        
                if frame_to_write is not None:
                    writer.write(frame_to_write)
                    next_frame_to_write += 1
                    
                    if next_frame_to_write % max(1, total_frames // 100) == 0 or next_frame_to_write == total_frames:
                        pct = int((next_frame_to_write / total_frames) * 100)
                        self.progress_changed.emit(pct)
                else:
                    # Relinquish CPU slice briefly
                    time.sleep(0.001)
                    
        cap.release()
        writer.release()
        
        if worker_exception:
            raise worker_exception
            
        return not self._is_cancelled
