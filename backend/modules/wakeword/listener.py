import numpy as np
import sounddevice as sd
from openwakeword.model import Model
import time
import requests
import threading
import sys
import queue
from pathlib import Path
import re
from datetime import datetime

PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.append(str(PROJECT_ROOT))
from backend.modules.voice.tts import speak, play_mp3, generate_cached_audio, stop_speaking
from backend.config.jarvis_config import WAKE_RESPONSE, BEAST_MODE
from backend.modules.voice.stt_whisper import listen_for_question
from backend.modules.llm.memory_manager import load_user_profile, update_user_profile
from backend.modules.memory.memory_store import get_memory_context_prompt, add_conversation_turn
from backend.router.intent_router import route_command
from backend.modules.google.gmail_intent import GmailHandler
from backend.modules.research.research_intent import ResearchHandler
from backend.modules.core.jarvis_events import get_next_event_nowait
from backend.modules.agents.calendar_reminder_agent import start_calendar_reminder_agent
from backend.modules.rag.rag_store import warm_rag
from backend.modules.core.gpu_priority import (
    mark_interactive_gpu_active,
    clear_interactive_gpu_active,
)
from backend.modules.briefing.morning_briefing_intent import (
    is_morning_briefing_request,
    handle_morning_briefing_streamed,
)

gmail_handler = GmailHandler()
research_handler = ResearchHandler()
now = datetime.now()
current_date_str = now.strftime("%Y-%m-%d")
current_year = now.year

SAMPLE_RATE = 16000
CHUNK_SIZE = 1600
TRIGGER_COOLDOWN_SECONDS = 8
WAKE_AUDIO_PATH = str(PROJECT_ROOT / "backend" / "assets" / "wake_response.mp3")
WAKE_AUDIO_PATH_GPU = str(PROJECT_ROOT / "backend" / "assets" / "wake_response.wav")
WAKE_HASH_PATH = str(PROJECT_ROOT / "backend" / "assets" / "wake_response.hash")

last_trigger = 0
is_processing = False
audio_stream = None  

# State tracking for continuous streaming
is_recording_question = False
question_queue = queue.Queue()

model = Model(inference_framework="onnx")
wake_queue = queue.Queue()
http_session = requests.Session()
UI_RENDER_SETTLE_SECONDS = 0.03
FIRST_COMMAND_LISTEN_SECONDS = 12
FOLLOW_UP_LISTEN_SECONDS = 120

print("Listening for wake word... Press Ctrl+C to stop.")
generate_cached_audio(WAKE_RESPONSE, WAKE_AUDIO_PATH, WAKE_HASH_PATH)

def notify_ui(status: str, settle: bool = False):
    """
    Sends UI state changes in order.

    Important:
    This is intentionally synchronous so the print only happens after
    the backend actually receives the state change.
    """
    start = time.perf_counter()

    try:
        response = http_session.get(
            f"http://localhost:8000/trigger-{status}",
            timeout=0.5,
        )

        elapsed_ms = (time.perf_counter() - start) * 1000
        print(f"UI status sent -> {status} ({elapsed_ms:.0f}ms)")

        if not response.ok:
            print(f"UI status failed -> {status}: {response.status_code}")

    except requests.RequestException:
        print(f"Could not notify UI: {status}")

    if settle:
        time.sleep(UI_RENDER_SETTLE_SECONDS)

def show_completed_research_ui():
    try:
        response = requests.get(
            "http://localhost:8000/research/show-completed",
            timeout=2,
        )
        return response.ok
    except requests.RequestException:
        print("Could not show completed research on UI.")
        return False    
    
def close_research_ui():
    try:
        requests.get(
            "http://localhost:8000/research/close",
            timeout=2,
        )
        return True
    except requests.RequestException:
        return False      


def active_listen_for_flow(seconds: int = 12):
    """
    Used by interactive flows that need to temporarily own the microphone.
    """
    global is_recording_question

    mark_interactive_gpu_active(
        reason="interactive_flow_listening",
        ttl_seconds=seconds + 60,
    )

    is_recording_question = True
    notify_ui("listening")

    try:
        return listen_for_question(question_queue, seconds=seconds)
    finally:
        is_recording_question = False


def active_speak_for_flow(text: str):
    mark_interactive_gpu_active(
        reason="interactive_flow_speaking",
        ttl_seconds=180,
    )
    notify_ui("speaking", settle=True)
    speak(text)
    notify_ui("listening", settle=True)


def event_watcher():
    """
    Watches for background events from agents.

    Important:
    This does NOT speak.
    It only moves events into wake_queue so action_worker can handle them
    when it is back in standby / waiting-for-wake-word mode.
    """
    while True:
        while True:
            jarvis_event = get_next_event_nowait()

            if not jarvis_event:
                break

            wake_queue.put(("jarvis_event", jarvis_event))

        time.sleep(0.5)


def handle_jarvis_event(jarvis_event):
    """
    Handles background events only after action_worker is free again.

    This makes the event feel like a wake-word-triggered flow without requiring
    the user to say the wake word.
    """
    global is_processing, is_recording_question, last_trigger
    mark_interactive_gpu_active(
        reason="jarvis_event_voice_flow",
        ttl_seconds=180,
    )

    if jarvis_event.event_type == "calendar_reminder":
        is_processing = True

        try:
            title = jarvis_event.payload.get("title", "your meeting")
            minutes = jarvis_event.payload.get("minutes", 15)
            start_speech = jarvis_event.payload.get("start_speech", "")

            print(f"[Jarvis Event] Calendar reminder received for: {title}")

            if start_speech:
                active_speak_for_flow(
                    f"Reminder. {title} starts in {minutes} minutes, at {start_speech}."
                )
            else:
                active_speak_for_flow(
                    f"Reminder. {title} starts in {minutes} minutes."
                )

        except Exception as e:
            print(f"[Jarvis Event Error] Failed to handle calendar reminder: {e}")

        finally:
            notify_ui("listening")
            is_processing = False
            is_recording_question = False
            last_trigger = time.time()
            clear_interactive_gpu_active()

        return

    if jarvis_event.event_type != "research_complete":
        return

    is_processing = True

    try:
        topic = jarvis_event.payload.get("topic", "your research")
        report = jarvis_event.payload.get("report", "")

        print(f"[Jarvis Event] Research complete event received for: {topic}")

        # This is where Jarvis speaks the completion message.
        active_speak_for_flow(
            f"Research is complete on {topic}. You can ask me questions about it now."
        )

       
        result_note = research_handler.execute_interactive(
            listen_func=active_listen_for_flow,
            speak_func=active_speak_for_flow,
            initial_command="research is complete",
            topic=topic,
            report=report,
            announce=False,
        )

        print(result_note)

    except Exception as e:
        print(f"[Jarvis Event Error] Failed to handle event: {e}")

    finally:
        notify_ui("listening")
        is_processing = False
        is_recording_question = False
        last_trigger = time.time()    


def action_worker():
    global is_processing, last_trigger, is_recording_question

    while True:
        # 1. Wait for the initial "Hey Jarvis" wake word
        event = wake_queue.get()

        # Background events are only processed when action_worker is free.
        # If Jarvis is in an active conversation, this code will not run yet.
        if isinstance(event, tuple) and event[0] == "jarvis_event":
            try:
                handle_jarvis_event(event[1])
            finally:
                wake_queue.task_done()
            continue

        try:
            if event == "trigger":
                # Immediately interrupt any ongoing speech (barge-in)
                stop_speaking()
                mark_interactive_gpu_active(
                reason="conversation_started",
                ttl_seconds=FOLLOW_UP_LISTEN_SECONDS + 200,
                )
                print("--- STARTING CONVERSATION SESSION ---")
                
                # Clear out any accidental duplicate wake word triggers
                preserved_events = []

                while not wake_queue.empty():
                    try:
                        queued_event = wake_queue.get_nowait()

                        # Only discard duplicate wake-word triggers.
                        # Preserve background events like research_complete.
                        if queued_event != "trigger":
                            preserved_events.append(queued_event)

                        wake_queue.task_done()

                    except queue.Empty:
                        break

                for preserved_event in preserved_events:
                    wake_queue.put(preserved_event)

                # Play the wake sound ONLY once at the very beginning of the chat
                notify_ui("speaking", settle=True)
                if BEAST_MODE:
                    play_mp3(WAKE_AUDIO_PATH_GPU)
                else:
                   play_mp3(WAKE_AUDIO_PATH)

                notify_ui("listening", settle=True)

                # Load previous user facts and long-term memory
                user_facts = load_user_profile()
                memory_ctx = get_memory_context_prompt()
                profile_context = ""
                if user_facts:
                    profile_context += "\nCore details you know about the user:\n" + "\n".join([f"- {fact}" for fact in user_facts])
                if memory_ctx:
                    profile_context += "\n" + memory_ctx

                # --- MEMORY INITIALIZATION ---
                # This establishes the context persona for this active session.
                conversation_history = [
                    {
                        "role": "system",
                        "content": (
                        "You are Jarvis, a highly intelligent, sharp, and articulate companion. "
                        "Your tone is polished, calm, and effortlessly capable, with a hint of dry wit. "
                        "CRITICAL: Keep all responses ultra-concise (1 to 3 sentences maximum) and optimized for voice. "
                        "Give direct answers immediately. Never use conversational filler or introductory pleasantries. "
                        "Never say a question is outside your functional parameters unless a safety rule truly prevents answering. "
                        "MEMORY RULE: Use the Core details only when the user asks about their personal schedule, reminders, notes, preferences, projects, or past conversations. "
                        "Core details are helpful context, not a limit on what you can answer. "
                        "For general knowledge, trivia, coding, explanations, or creative questions, answer normally using your own knowledge. "
                        "Do not refuse general questions just because the answer is not in Core details. "
                        "Do not redirect general questions to calendar, email, research, or other tools unless the user asked for that tool. "
                        "Background research tasks do not limit normal conversation. "
                        "You are a versatile assistant. Beyond managing tasks and schedules, "
                        "you are fully capable of general conversation, technical answers, trivia, and creative assistance. "
                        "Never mention internal labels like Core details, system prompt, profile context, or functional parameters. "
                        f"The current year is {current_year}.{profile_context}"
                                                    )
                    }
                ]

                # Flag to keep the conversation rolling without requiring the wake word
                in_conversation = True
                has_completed_turn = False
                
                while in_conversation:
                    mark_interactive_gpu_active(
                        reason="conversation_active",
                        ttl_seconds=FOLLOW_UP_LISTEN_SECONDS + 90,
                    )
                    is_recording_question = True
                    notify_ui("listening") 

                    # Capture whatever speech comes in
                    listen_seconds = (
                        FOLLOW_UP_LISTEN_SECONDS
                        if has_completed_turn
                        else FIRST_COMMAND_LISTEN_SECONDS
                    )

                    question = listen_for_question(question_queue, seconds=listen_seconds)
                    is_recording_question = False

                    # BREAK CONDITION A: If you stay silent, gracefully end the session
                    if not question or not question.strip():
                        print("Silence detected. Ending active conversation session.")
                        in_conversation = False
                        continue

                    # BREAK CONDITION B: Explicit exit phrases
                    exit_phrases = ["goodbye", "bye", "stop", "nevermind", "thank you", "that's all"]
                    if any(phrase in question.lower() for phrase in exit_phrases):
                        print("Exit phrase detected. Ending session.")
                        speak("You're welcome. Standing by.")
                        in_conversation = False
                        continue

                    print(f"Question: '{question}'")

                    def active_listen():
                        global is_recording_question
                        is_recording_question = True
                        notify_ui("listening")
                        ans = listen_for_question(question_queue, seconds=12)
                        is_recording_question = False
                        return ans


                    def active_speak(text):
                        mark_interactive_gpu_active(
                            reason="active_speak",
                            ttl_seconds=180,
                        )
                        notify_ui("speaking", settle=True)
                        speak(text)
                        notify_ui("listening", settle=True)

                    

                    # INTERACTIVE MODE: Send email
                    # This takes control of the mic/speaker and skips the normal route_command flow.
                    if "send email" in question.lower() or "send an email" in question.lower():
                          
                        result_note = gmail_handler.execute_interactive(
                            active_listen,
                            active_speak,
                            question,
                        )
                        notify_ui("listening")
                        conversation_history.append({"role": "user", "content": question})
                        conversation_history.append({"role": "assistant", "content": result_note})

                        
                        continue

                    if is_morning_briefing_request(question):
                        result_note = handle_morning_briefing_streamed(
                            speak_func=active_speak,
                            command=question,
                            history=conversation_history,
                        )

                        notify_ui("listening")
                        conversation_history.append({"role": "user", "content": question})
                        conversation_history.append({"role": "assistant", "content": result_note})
                        has_completed_turn = True

                        continue        
                    # INTERACTIVE MODE: Research Q&A
                    # This takes control of the mic/speaker and skips normal chat until the user exits research mode.
                    research_qa_phrases = [
                        "ask questions about the research",
                        "research questions",
                        "talk about the research",
                        "review the research",
                        "go over the research",
                        "what did the research find",
                        "research is complete",
                    ]

                    if any(phrase in question.lower() for phrase in research_qa_phrases):
                        result_note = research_handler.execute_interactive(
                            active_listen,
                            active_speak,
                            question,
                        )
                        notify_ui("listening")
                        conversation_history.append({"role": "user", "content": question})
                        conversation_history.append({"role": "assistant", "content": result_note})

                        
                        continue
                                
                    show_completed_research_phrases = [
                        "show me completed research",
                        "show completed research",
                        "show research",
                        "show all research",
                        "open completed research",
                        "display completed research",
                    ]

                    if any(phrase in question.lower() for phrase in show_completed_research_phrases):
                        notify_ui("thinking")

                        if show_completed_research_ui():
                            notify_ui("speaking", settle=True)
                            speak("Opening completed research.")
                        else:
                            notify_ui("speaking", settle=True)
                            speak("I could not open completed research on the interface.")

                        notify_ui("listening", settle=True)
                        continue

                    close_research_phrases = [
                        "close research",
                        "close completed research",
                        "hide research",
                        "go back",
                        "home",
                        "return home",
                    ]

                    if any(p in question.lower() for p in close_research_phrases):
                        close_research_ui()
                        speak("Closing research.")
                        continue

                    
                    
                    # Append the user's question to our memory list
                    conversation_history.append({"role": "user", "content": question})

                    notify_ui("thinking", settle=True)

                    response = route_command(question, conversation_history)

                    # Check intents
                    if response:
                        # Only call speak() here if the intent handler didn't stream-speak it already
                        if not getattr(response, "is_streamed", False):
                            notify_ui("speaking", settle=True)
                            speak(response)
                        
                        notify_ui("listening", settle=True)
                        has_completed_turn = True
                   
                    
                    # Append Jarvis's completed text response to our memory list
                    conversation_history.append({"role": "assistant", "content": response})
                    try:
                        add_conversation_turn("default_session", "user", question)
                        add_conversation_turn("default_session", "assistant", str(response))
                    except Exception as e:
                        print(f"[Memory Turn Error]: {e}")
                    
                    
                    if len(conversation_history) > 11:
                        conversation_history = [conversation_history[0]] + conversation_history[-10:]
                    
                    # Instead of closing, we loop right back to the top of 'while in_conversation'
                    print("Active turn complete. Listening for your follow-up...")

        except Exception as e:
            print(f"Error in action worker loop: {e}")

        finally:
            # This block now ONLY runs when the active session loop terminates
            print("Closing conversation session and resetting wake components...")
            clear_interactive_gpu_active()
            notify_ui("idle")
            try:
                model.reset() 
            except AttributeError:
                pass
            
            # Set the cooldown timestamp so openwakeword can safely re-initialize
            last_trigger = time.time() 
            is_processing = False
            is_recording_question = False
            wake_queue.task_done()
            if conversation_history:
                update_user_profile(conversation_history)

            print("System standby. Ready for next wake word...\n")

def callback(indata, frames, callback_time, status):
    global last_trigger, is_processing, is_recording_question

    if status:
        print(f"Audio status: {status}")

    # If Jarvis is listening for a command, route the float32 raw data seamlessly
    if is_recording_question:
        question_queue.put(indata.copy())
        return

    # If Jarvis is speaking or thinking, ignore incoming microphone data
    if is_processing:
        return

    # Otherwise, convert data to int16 for openwakeword processing
    audio = (indata[:, 0] * 32767).astype(np.int16)
    prediction = model.predict(audio)

    for wakeword, score in prediction.items():
        if wakeword == "hey_jarvis" and score > 0.5:
            current = time.time()

            if current - last_trigger > TRIGGER_COOLDOWN_SECONDS:
                mark_interactive_gpu_active(
                    reason="wake_word_detected",
                    ttl_seconds=FOLLOW_UP_LISTEN_SECONDS + 90,
                )
                is_processing = True
                last_trigger = current

                print(f"Wake word detected: {wakeword} ({score:.2f})")
                wake_queue.put("trigger")


worker_thread = threading.Thread(target=action_worker, daemon=True)
worker_thread.start()

event_thread = threading.Thread(target=event_watcher, daemon=True)
event_thread.start()

threading.Thread(target=warm_rag, daemon=True).start()

print(start_calendar_reminder_agent())

try:
    # This stream now remains active and open for the lifetime of the program
    audio_stream = sd.InputStream(
        channels=1,
        samplerate=SAMPLE_RATE,
        blocksize=CHUNK_SIZE,
        dtype="float32",
        callback=callback,
    )
    
    with audio_stream:
        while True:
            sd.sleep(1000)

except KeyboardInterrupt:
    print("Stopping wake word listener.")