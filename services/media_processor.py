import os
from faster_whisper import WhisperModel
from moviepy import VideoFileClip

# 1. OPTIMIZATION: Use 'small.en' (English-only) for high accuracy and speed on Mac M2
print("Loading Optimized English Whisper Model...")
whisper_model = WhisperModel("small.en", device="cpu", compute_type="int8")

def extract_audio_from_video(video_path: str, output_audio_path: str) -> str:
    """
    Priority 2: Converts a video file into an audio file.
    """
    print(f"🎬 Extracting audio from video: {video_path}")
    try:
        video = VideoFileClip(video_path)
        video.audio.write_audiofile(output_audio_path)
        video.close()
        print("✅ Audio extraction complete.")
        return output_audio_path
    except Exception as e:
        raise RuntimeError(f"Failed to extract audio from video: {str(e)}")

def transcribe_audio(audio_path: str) -> str:
    """
    Priority 1 & 2: Transcribes English audio into text with high speed.
    """
    print(f"🎙️ Transcribing audio: {audio_path}")
    try:
        # 2. OPTIMIZATION: Hardcode language="en" to skip detection time
        # 3. OPTIMIZATION: Enable vad_filter=True to instantly skip silent audio
        segments, info = whisper_model.transcribe(
            audio_path, 
            language="en", 
            vad_filter=True,
            beam_size=5 
        )
        
        # Combine all transcription segments into one string efficiently
        full_transcript = [segment.text for segment in segments]
        final_text = " ".join(full_transcript).strip()
        
        print("✅ Fast English Transcription complete.")
        return final_text
    
    except Exception as e:
        raise RuntimeError(f"Failed to transcribe audio: {str(e)}")