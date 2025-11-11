# SPDX-License-Identifier: NOASSERTION
# Copyright (c) 2025 Shahin

"""
ماژول ورودی/خروجی صوتی برای Sofware-AI
این ماژول مسئول تبدیل گفتار به متن و متن به گفتار است.
"""

import os
import queue
import threading
import logging
import tempfile
import subprocess
from typing import Optional, Callable, Any, cast, Literal
import speech_recognition as sr
from google.cloud import texttospeech
from gtts import gTTS
import sounddevice as sd
import soundfile as sf
from pydub import AudioSegment
import io

logger = logging.getLogger(__name__)

class VoiceInput: 
    """کلاس مدیریت ورودی صوتی (تبدیل گفتار به متن)"""
    def __init__(self) -> None:
        """مقداردهی اولیه تشخیص گفتار"""
        self.recognizer = sr.Recognizer()
        self.microphone = sr.Microphone()
        self.stop_listening: Optional[Callable[[], None]] = None
        self.audio_queue = queue.Queue()
        self.listening_thread: Optional[threading.Thread] = None
        self.is_listening = False
        self._setup_recognition()

    def _setup_recognition(self) -> None:
        """تنظیم پارامترهای تشخیص صدا و حذف نویز محیط"""
        with self.microphone as source:
            self.recognizer.adjust_for_ambient_noise(source, duration=1)
            # تنظیم حساسیت تشخیص صدا
            self.recognizer.energy_threshold = 4000
            self.recognizer.dynamic_energy_threshold = True

    def listen_once(self, timeout: Optional[int] = None) -> str:
        """یک‌بار گوش دادن و تبدیل گفتار به متن
        
        Args:
            timeout: زمان انتظار به ثانیه (None برای نامحدود)
            
        Returns:
            متن تشخیص داده شده یا رشته خالی در صورت خطا
        """
        try:
            with self.microphone as source:
                logger.info("Dar hale Goosh dadan...")
                audio = self.recognizer.listen(source, timeout=timeout)

            text = cast(Any, self.recognizer).recognize_google(audio, language="fa-IR")
            logger.info(f"Tashkhis Dade Shod: {text}")
            return text
        except sr.WaitTimeoutError:
            logger.warning("Zaman-e entezaar be payan resid.")
            return ""
        except sr.UnknownValueError:
            logger.error("Gofte shode ra nemitavan tashkhis dad.")
            return ""
        except sr.RequestError as e:
            logger.error(f"Khataye khadamat-e tashkhis: {str(e)}")
            return ""
        except Exception as e:
            logger.error(f"Khataye gheire montazere: {str(e)}")
            
        return ""
        
    def start_continuous(self, callback: Callable[[str], Any]) -> None:
        """شروع گوش دادن مداوم در یک thread جداگانه
        
        Args:
            callback: تابعی که با متن تشخیص داده شده فراخوانی می‌شود
        """
        def listener_thread():
            while self.is_listening:
                text = self.listen_once()
                if text:
                    callback(text)

        self.is_listening = True
        threading.Thread(target=listener_thread, daemon=True).start()

    def stop_continuous(self) -> None:
        """توقف گوش دادن مداوم"""
        self.is_listening = False

class VoiceOutput:
    """کلاس مدیریت خروجی صوتی (تبدیل متن به گفتار)
    
    این کلاس از دو سرویس TTS پشتیبانی می‌کند:
    - Google Cloud TTS (google-cloud): کیفیت بالاتر، پرداختی
    - gTTS (gtts): رایگان، کیفیت معقول
    """
    
    def __init__(self, tts_provider: Literal["google-cloud", "gtts"] = "google-cloud") -> None:
        """مقداردهی اولیه موتور تبدیل متن به گفتار
        
        Args:
            tts_provider: انتخاب سرویس TTS
                - "google-cloud": Google Cloud Text-to-Speech (نیاز به اعتبارنامه)
                - "gtts": gTTS سرویس رایگان
        """
        self.tts_provider = tts_provider
        self.speaking_queue = queue.Queue()
        self.is_speaking = False
        self.temp_dir = tempfile.mkdtemp()
        
        # مقداردهی سرویس Google Cloud (اگر استفاده شود)
        if self.tts_provider == "google-cloud":
            self.client = texttospeech.TextToSpeechClient()
            self.voice = texttospeech.VoiceSelectionParams(
                language_code="fa-IR",
                name="fa-IR-Standard-A"
            )
            self.audio_config = texttospeech.AudioConfig(
                audio_encoding=texttospeech.AudioEncoding.LINEAR16,
                speaking_rate=1.0,
                pitch=0.0,
                volume_gain_db=0.0
            )
            logger.info("TTS Provider: Google Cloud Text-to-Speech")
        else:
            logger.info("TTS Provider: gTTS (رایگان)")
        
        self._start_speaker_thread()

    def _synthesize_speech_google_cloud(self, text: str) -> bytes:
        """تبدیل متن به صدا با استفاده از Google Cloud TTS
        
        Args:
            text: متن برای تبدیل به گفتار
            
        Returns:
            داده‌های صوتی به صورت bytes
        """
        synthesis_input = texttospeech.SynthesisInput(text=text)
        response = self.client.synthesize_speech(
            input=synthesis_input,
            voice=self.voice,
            audio_config=self.audio_config
        )
        return response.audio_content

    def _synthesize_speech_gtts(self, text: str) -> bytes:
        """تبدیل متن به صدا با استفاده از gTTS
        
        Args:
            text: متن برای تبدیل به گفتار
            
        Returns:
            داده‌های صوتی به صورت bytes
        """
        temp_mp3 = os.path.join(self.temp_dir, "temp_gtts.mp3")
        try:
            # ایجاد و ذخیره فایل صوتی gTTS
            # gTTS کدهای زبان مختلفی را پشتیبانی می‌کند
            # برای فارسی از 'fa' استفاده می‌کنیم
            tts = gTTS(text=text, lang='fa', slow=False)
            tts.save(temp_mp3)
            
            # خواندن فایل MP3 و تبدیل به bytes
            with open(temp_mp3, 'rb') as f:
                audio_bytes = f.read()
            
            return audio_bytes
        except Exception as e:
            # اگر زبان فارسی کار نکرد، سعی کنیم با انگلیسی
            logger.warning(f"خطا در gTTS برای فارسی: {str(e)}")
            try:
                tts = gTTS(text=text, lang='en', slow=False)
                tts.save(temp_mp3)
                with open(temp_mp3, 'rb') as f:
                    audio_bytes = f.read()
                return audio_bytes
            except Exception as fallback_error:
                logger.error(f"خطا در gTTS حتی برای انگلیسی: {str(fallback_error)}")
                raise
        finally:
            # پاک‌سازی فایل موقت
            if os.path.exists(temp_mp3):
                os.remove(temp_mp3)

    def _synthesize_speech(self, text: str) -> bytes:
        """تبدیل متن به صدا با استفاده از سرویس انتخاب‌شده
        
        Args:
            text: متن برای تبدیل به گفتار
            
        Returns:
            داده‌های صوتی به صورت bytes
        """
        if self.tts_provider == "google-cloud":
            return self._synthesize_speech_google_cloud(text)
        else:
            return self._synthesize_speech_gtts(text)

    def _play_audio(self, audio_content: bytes, is_mp3: bool = False) -> None:
        """پخش صدا با استفاده از sounddevice و ffplay
        
        Args:
            audio_content: داده‌های صوتی به صورت bytes
            is_mp3: آیا فرمت صوتی MP3 است (برای gTTS)
        """
        if is_mp3:
            # برای gTTS که MP3 است
            temp_mp3 = os.path.join(self.temp_dir, "temp_audio.mp3")
            try:
                # ذخیره MP3
                with open(temp_mp3, 'wb') as f:
                    f.write(audio_content)
                
                # تلاش برای پخش MP3 با ffplay
                try:
                    import subprocess
                    subprocess.run(["ffplay", "-nodisp", "-autoexit", temp_mp3], 
                                 check=True, 
                                 stdout=subprocess.DEVNULL, 
                                 stderr=subprocess.DEVNULL,
                                 timeout=30)
                except Exception as play_error:
                    logger.warning(f"ffplay mojod nist ya kar nakard:\n{str(play_error)}")
                    logger.info("baraye pakhsh sahih ffmpeg ra nasb konid: choco install ffmpeg")
            finally:
                if os.path.exists(temp_mp3):
                    os.remove(temp_mp3)
        else:
            # برای Google Cloud که WAV است
            temp_wav = os.path.join(self.temp_dir, "temp_speech.wav")
            with open(temp_wav, "wb") as f:
                f.write(audio_content)
            
            try:
                data, samplerate = sf.read(temp_wav)
                sd.play(data, samplerate)
                sd.wait()
            finally:
                if os.path.exists(temp_wav):
                    os.remove(temp_wav)

    def _start_speaker_thread(self) -> None:
        """راه‌اندازی thread مدیریت صف گفتار"""
        def speaker_thread():
            while True:
                try:
                    text = self.speaking_queue.get()
                    if text is None:  # سیگنال توقف
                        break
                    
                    self.is_speaking = True
                    audio_content = self._synthesize_speech(text)
                    
                    # تعیین فرمت صوتی بر اساس سرویس
                    is_mp3 = self.tts_provider == "gtts"
                    self._play_audio(audio_content, is_mp3=is_mp3)
                except Exception as e:
                    logger.error(f"khata dar pokhsh goftar:\n{str(e)}")
                finally:
                    self.is_speaking = False
                    self.speaking_queue.task_done()
        
        self.speaker_thread = threading.Thread(target=speaker_thread, daemon=True)
        self.speaker_thread.start()

    def speak(self, text: str, block: bool = False) -> None:
        """تبدیل متن به گفتار
        
        Args:
            text: متن برای تبدیل به گفتار
            block: اگر True باشد، منتظر اتمام گفتار می‌ماند
        """
        try:
            self.speaking_queue.put(text)
            if block:
                self.speaking_queue.join()
        except Exception as e:
            logger.error(f"khata dar afzoodan matn be saf goftar: {str(e)}")

    def stop_speaking(self) -> None:
        """توقف فوری گفتار فعلی و پاک‌سازی صف"""
        with self.speaking_queue.mutex:
            self.speaking_queue.queue.clear()

    def shutdown(self) -> None:
        """خاموش کردن موتور تبدیل متن به گفتار"""
        try:
            self.speaking_queue.put(None)  # ارسال سیگنال توقف
            self.speaker_thread.join()
            if os.path.exists(self.temp_dir):
                os.rmdir(self.temp_dir)
        except Exception as e:
            logger.error(f"khata dar khamosh kardan motor: {str(e)}")

class VoiceManager:
    """مدیریت یکپارچه ورودی و خروجی صوتی"""

    def __init__(self, tts_provider: Literal["google-cloud", "gtts"] = "google-cloud") -> None:
        """مقداردهی اولیه مدیر صوتی
        
        Args:
            tts_provider: انتخاب سرویس TTS
                - "google-cloud": Google Cloud Text-to-Speech
                - "gtts": gTTS رایگان
        """
        self.voice_input = VoiceInput()
        self.voice_output = VoiceOutput(tts_provider=tts_provider)

    def listen(self, timeout: Optional[int] = None) -> str:
        """گوش دادن یک‌باره به ورودی صوتی
        
        Args:
            timeout: زمان انتظار به ثانیه
            
        Returns:
            متن تشخیص داده شده
        """
        return self.voice_input.listen_once(timeout)
    
    def speak(self, text: str, block: bool = False) -> None:
        """تبدیل متن به گفتار
        Args:
            text: متن برای تبدیل به گفتار
            block: اگر True باشد، منتظر اتمام گفتار می‌ماند
        """
        self.voice_output.speak(text, block)

    def start_conversation(self, callback: Callable[[str], Any]) -> None:
        """شروع مکالمه دوطرفه
        
        Args:
            callback: تابعی که با متن تشخیص داده شده فراخوانی می‌شود
        """
        self.voice_input.start_continuous(callback)

    def stop_conversation(self) -> None:
        """توقف مکالمه دوطرفه"""
        self.voice_input.stop_continuous()
        self.voice_output.stop_speaking()

    def shutdown(self) -> None:
        """بستن تمیز سیستم صوتی"""
        self.stop_conversation()
        self.voice_output.shutdown()