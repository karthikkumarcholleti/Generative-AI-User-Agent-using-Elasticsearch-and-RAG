# backend/app/core/llm.py
import os
import threading
import logging
import gc
import time
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
from dotenv import load_dotenv
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig

logger = logging.getLogger(__name__)

# ---- config via env ----
# Load root .env (repo root, not backend/.env) - same as database.py
# Path from: backend/app/core/llm.py -> FHIR_COMBINED/ (root)
ROOT_DIR = Path(__file__).resolve().parents[4]  # Go up 4 levels to repo root
load_dotenv(ROOT_DIR / ".env")  # Load environment variables from root .env

# Get model path from env or use default
_default_path = str(ROOT_DIR / "FHIR_LLM_UA" / "models" / "llama31-8b-bnb4")
MODEL_PATH = os.getenv("LLM_MODEL_PATH", _default_path)

# Ensure absolute path
if not os.path.isabs(MODEL_PATH):
    # If relative, make it relative to repo root (not backend directory)
    MODEL_PATH = str(ROOT_DIR / MODEL_PATH.lstrip("./"))
# Balanced token limit for complete responses while preventing OOM
MAX_NEW_TOKENS = int(os.getenv("LLM_MAX_NEW_TOKENS", "800"))  # Reduced to 800 to prevent OOM
TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.3"))
TOP_P = float(os.getenv("LLM_TOP_P", "0.9"))

# Configuration - Use device_map="auto" like the working version
# This lets HuggingFace automatically handle GPU allocation
USE_AUTO_DEVICE_MAP = os.getenv("USE_AUTO_DEVICE_MAP", "true").lower() == "true"

# singletons - Simple single model instance (like working version)
_tokenizer = None
_model = None
_init_lock = threading.Lock()
_gen_lock = threading.Lock()  # serialize generation to avoid GPU OOM
_query_waiting = threading.Condition(_gen_lock)  # Condition for query priority
_active_query_count = 0  # Track active queries (queries skip ahead of summaries)
_load_attempted = False  # Track if we've attempted to load (to prevent infinite retry loops)

# Removed dual-GPU functions - using device_map="auto" instead

def _load():
    """Lazy-load tokenizer and model once (thread-safe). Uses device_map='auto' like the working version."""
    global _tokenizer, _model, _load_attempted
    if _tokenizer is not None and _model is not None:
        return
    with _init_lock:
        if _tokenizer is not None and _model is not None:
            return

        # Set flag to track that we're attempting to load
        _load_attempted = True

        try:
            # If the model repo already stores a quantization_config, HF will ignore this safely.
            bnb_config = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_compute_dtype=torch.bfloat16 if torch.cuda.is_available() else None,
                bnb_4bit_use_double_quant=True,
                bnb_4bit_quant_type="nf4",
            )

            # Use device_map="auto" but restrict to GPU only (4-bit quantization doesn't support CPU offloading)
            # If GPU memory is insufficient, we'll get an error and can handle it gracefully
            if os.path.exists(MODEL_PATH) and os.path.isdir(MODEL_PATH):
                print(f"📦 Loading model from local path: {MODEL_PATH}")
                print(f"📦 Using device_map='auto' (GPU only - 4-bit doesn't support CPU offloading)")
                # Load tokenizer (allow HuggingFace cache for compatibility)
                _tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH, use_fast=True)
                # Try GPU-only first (4-bit quantization works best on GPU)
                try:
                    _model = AutoModelForCausalLM.from_pretrained(
                        MODEL_PATH,
                        device_map="auto",  # Let HuggingFace handle GPU allocation automatically
                        quantization_config=bnb_config,
                        trust_remote_code=True,
                    )
                except ValueError as ve:
                    # If GPU memory error, try with explicit GPU allocation
                    if "CPU" in str(ve) or "disk" in str(ve).lower():
                        print(f"⚠️ GPU memory issue detected, trying explicit GPU allocation...")
                        # Force all layers to GPU 0 (or split across GPUs if available)
                        if torch.cuda.device_count() >= 2:
                            _model = AutoModelForCausalLM.from_pretrained(
                                MODEL_PATH,
                                device_map="balanced",  # Split across available GPUs
                                quantization_config=bnb_config,
                                trust_remote_code=True,
                            )
                        else:
                            # Single GPU - try to fit everything
                            _model = AutoModelForCausalLM.from_pretrained(
                                MODEL_PATH,
                                device_map={"": 0},  # All on GPU 0
                                quantization_config=bnb_config,
                                trust_remote_code=True,
                            )
                    else:
                        raise  # Re-raise if it's a different error
            else:
                print(f"📦 Loading model from HuggingFace or path: {MODEL_PATH}")
                print(f"📦 Using device_map='auto' (GPU only - 4-bit doesn't support CPU offloading)")
                _tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH, use_fast=True)
                try:
                    _model = AutoModelForCausalLM.from_pretrained(
                        MODEL_PATH,
                        device_map="auto",  # Let HuggingFace handle GPU allocation automatically
                        quantization_config=bnb_config,
                        trust_remote_code=True,
                    )
                except ValueError as ve:
                    # If GPU memory error, try with explicit GPU allocation
                    if "CPU" in str(ve) or "disk" in str(ve).lower():
                        print(f"⚠️ GPU memory issue detected, trying explicit GPU allocation...")
                        if torch.cuda.device_count() >= 2:
                            _model = AutoModelForCausalLM.from_pretrained(
                                MODEL_PATH,
                                device_map="balanced",
                                quantization_config=bnb_config,
                                trust_remote_code=True,
                            )
                        else:
                            _model = AutoModelForCausalLM.from_pretrained(
                                MODEL_PATH,
                                device_map={"": 0},
                                quantization_config=bnb_config,
                                trust_remote_code=True,
                            )
                    else:
                        raise
            print(f"✅ Model loaded successfully with device_map='auto'")
        except Exception as e:
            error_msg = f"❌ Failed to load model: {type(e).__name__}: {str(e)[:500]}"
            print(error_msg)
            logger.error(error_msg, exc_info=True)
            
            # Log error details for debugging
            if "ModelWrapper" in str(e) or "enum" in str(e).lower() or "json" in str(e).lower():
                print("⚠️ Detected model config JSON error. This might be due to:")
                print("   1. Corrupted model files")
                print("   2. Version mismatch between transformers library and model")
                print("   3. Incomplete model download")
            
            # If all else fails, raise the original error
            raise

# Removed _load_dual_gpu - using device_map="auto" instead

def _is_complete_sentence(text: str) -> bool:
    """Check if text ends with a complete sentence."""
    text = text.strip()
    if not text:
        return False
    
    # Check if ends with sentence-ending punctuation
    if text[-1] not in '.!?':
        return False
    
    # Check last line - medical observations typically end with complete bullet points
    lines = text.split('\n')
    last_line = lines[-1].strip() if lines else text
    
    # Pattern 1: Ends with just a number and period (e.g., "23." or "7." or "4.")
    # This is almost always incomplete - it's a numbered list item without content
    if len(last_line) >= 2 and last_line[-2].isdigit() and last_line[-1] == '.':
        # Check if it's a numbered list item (starts with number)
        # Examples: "4." (incomplete), "4. Condition name" (complete), "2.Respiratory rate - 18." (incomplete)
        if len(last_line) <= 3:  # Just "4." or "23." - definitely incomplete
            return False
        
        # Check for incomplete patterns like "2.Respiratory rate - 18." (missing unit/date)
        # Or "1.Patient presented with G..." (truncated)
        if len(last_line) > 3 and len(last_line) < 20:
            # Check if it looks like it was cut off mid-sentence
            # Patterns: "18." (value without unit), "G..." (truncated word)
            if last_line.endswith('.') and (last_line[-3:-1].isdigit() or last_line[-2] == '.'):
                # Check if there's a value but no unit/date
                import re
                # Pattern: number followed by period at end (likely incomplete)
                if re.search(r'\d+\.$', last_line):
                    # Check if there's more context that suggests completeness
                    if not any(word in last_line.lower() for word in ['recorded', 'on', 'unit', 'mg', 'mmhg', 'bpm', 'c', 'f']):
                        return False
        
        # Look for indicators of completeness in last 50 chars (increased from 30)
        last_segment = text[-50:] if len(text) >= 50 else text
        
        # Complete patterns (must have content after the number):
        # "- normal." / "- high." / "- low." / "- abnormal."
        # "U/L." / "mmHg." / "mg/dL."
        # "from July 30, 2025."
        # "Condition name." / "Description."
        # "(recorded on 2025-07-21)." - complete observation
        complete_indicators = [
            ' - normal.', ' - high.', ' - low.', ' - abnormal.',
            ' - stable.', ' - increasing.', ' - decreasing.',
            'U/L', 'mmHg', 'mg/dL', 'g/dL', 'mmol/L', '%',
            ', 2025.', ', 2024.', ', 2023.',
            'years.', 'years old.',
            '(recorded on', 'recorded on', 'on 2025-', 'on 2024-', 'on 2023-',
            'presented with', 'admitted for', 'reason for'
        ]
    
        # If there's substantial content after the number (more than just whitespace)
        # and it contains complete indicators, it's likely complete
        if len(last_line) > 5 and any(indicator in last_segment for indicator in complete_indicators):
            return True
    
        # If it's just a number and period with minimal content, it's incomplete
        if len(last_line) <= 5:
            return False
    
    # Pattern 2: Ends with colon followed by space and number (e.g., "QN: 23.")
    if ': ' in last_line:
        parts = last_line.split(': ')
        if len(parts[-1]) <= 5:  # Short value after colon, likely incomplete
            return False
    
    return True

def _get_category_token_limit(user_prompt: str, category: str = "default") -> int:
    """Determine token limit based on prompt content/category.
    
    Uses the same limits as the working version for reliability.
    """
    # Detect category from prompt
    if "TASK:\nSummary of patient's medical records:" in user_prompt:
        return 1000  # patient_summary needs substantial space
    elif "TASK:\nBased on the documented clinical data" in user_prompt:
        return 700  # care_plans needs substantial space
    elif "clinical observations include:" in user_prompt:
        return 2500  # observations need MAXIMUM space - many values to list with ranges
    elif "conditions summary" in user_prompt:
        return 1500  # conditions need more space to complete properly
    elif "Demographics" in user_prompt and "Name:" in user_prompt:
        return 500  # demographics are short but need space for complete sentences
    elif "notes summary" in user_prompt:
        return 500  # notes need moderate space
    elif "chat query" in user_prompt.lower() or "user query:" in user_prompt.lower() or "patient query:" in user_prompt.lower():
        return 1200  # chat queries need more space to avoid incomplete responses
    elif category == "compression":
        return 2000  # compression needs space to extract relevant information
    else:
        return 600  # default

def generate_general_medical_help(user_prompt: str) -> str:
    """Generate concise medical help for general questions (2 sentences max)."""
    _load()
    
    # System prompt for general medical help
    system_prompt = """You are a medical assistant that provides concise explanations of medical terms and normal ranges. 
    Keep responses to exactly 2 sentences maximum. Focus on clear, simple explanations."""
    
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    
    messages.append({"role": "user", "content": user_prompt})
    
    with _gen_lock:
        try:
            # Use shorter max tokens for concise responses
            inputs = _tokenizer.apply_chat_template(
                messages, 
                tokenize=True, 
                add_generation_prompt=True, 
                return_tensors="pt"
            )
            
            if torch.cuda.is_available():
                inputs = inputs.to(_model.device)
            
            with torch.no_grad():
                outputs = _model.generate(
                    inputs,
                    max_new_tokens=150,  # Much shorter for 2 sentences
                    temperature=0.3,
                    top_p=0.9,
                    do_sample=True,
                    pad_token_id=_tokenizer.eos_token_id,
                    eos_token_id=_tokenizer.eos_token_id,
                )
            
            # Decode only the new tokens
            new_tokens = outputs[0][inputs.shape[1]:]
            response = _tokenizer.decode(new_tokens, skip_special_tokens=True)
            
            # Clean up response
            response = response.strip()
            
            # Ensure it's only 2 sentences max
            sentences = response.split('. ')
            if len(sentences) > 2:
                response = '. '.join(sentences[:2]) + '.'
            
            return response
            
        except Exception as e:
            # Release query priority on error
            if is_query:
                with _query_waiting:
                    _active_query_count -= 1
                    if _active_query_count == 0:
                        _query_waiting.notify_all()
            raise
            print(f"Error in general medical help generation: {e}")
            return "I'm sorry, I couldn't process that request. Please try again with a specific medical term or question."

def generate_chat(system_prompt: str, user_prompt: str, category: str = "default") -> str:
    """
    Thread-safe text generation with adaptive memory management.
    Uses device_map="auto" like the working version - simple and reliable.
    
    Priority system: Queries (category="chat") skip ahead of summaries to improve UX.
    
    Args:
        system_prompt: System prompt for the LLM
        user_prompt: User prompt/query
        category: Category of the request (for token limits). Use "chat" for user queries.
    """
    global _active_query_count
    
    _load()
    
    # Verify model is loaded before proceeding
    if _model is None or _tokenizer is None:
        error_msg = "Model or tokenizer is not loaded. Cannot generate response."
        print(f"❌ {error_msg}")
        logger.error(error_msg)
        raise RuntimeError(error_msg)
    
    # Log for large prompts to help with debugging
    prompt_length = len(user_prompt)
    if prompt_length > 5000:
        print(f"Processing large prompt ({prompt_length} chars) - this may take longer...")

    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": user_prompt})

    is_query = (category == "chat")
    
    try:
        with _query_waiting:
            # Priority system: Queries skip ahead of summaries
            if is_query:
                # Query: Wait only if there are other queries, not summaries
                _active_query_count += 1
                print(f"🔵 Query queued (priority: high). Active queries: {_active_query_count}")
            else:
                # Summary: Wait for all queries to complete
                while _active_query_count > 0:
                    print(f"⏳ Summary waiting for {_active_query_count} active query(ies) to complete...")
                    _query_waiting.wait(timeout=1.0)  # Check every second
                print(f"✅ Summary proceeding (no active queries)")
            # Aggressive memory cleanup before generation
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
                torch.cuda.synchronize()
            
            inputs = _tokenizer.apply_chat_template(
                messages,
                add_generation_prompt=True,
                return_tensors="pt",
            ).to(_model.device)

            # Get category-specific base token limit
            base_tokens = _get_category_token_limit(user_prompt, category)
            max_tokens = min(base_tokens, MAX_NEW_TOKENS)
            
            # Check memory usage and reduce further if needed
            # For research quality, we use less aggressive reduction to ensure complete responses
            if torch.cuda.is_available():
                memory_allocated = torch.cuda.memory_allocated() / 1024**3  # GB
                memory_reserved = torch.cuda.memory_reserved() / 1024**3   # GB
                total_memory = torch.cuda.get_device_properties(0).total_memory / 1024**3  # GB
                
                memory_usage = (memory_allocated + memory_reserved) / total_memory if total_memory > 0 else 0
                
                # Progressive token reduction based on memory usage with category-aware minimums
                # Same thresholds as working version for reliability
                if memory_usage > 0.90:
                    max_tokens = min(max_tokens, 150)  # Emergency: minimal tokens
                elif memory_usage > 0.80:
                    max_tokens = min(max_tokens, 300)  # High pressure: reduce significantly
                elif memory_usage > 0.70:
                    max_tokens = min(max_tokens, 500)  # Moderate pressure: reduce moderately
                elif memory_usage > 0.60:
                    max_tokens = min(max_tokens, 700)  # Light pressure: slight reduction

            outputs = _model.generate(
                inputs,
                max_new_tokens=max_tokens,
                do_sample=False,  # Disable sampling for consistency and memory efficiency
                temperature=0.1,  # Very low temperature
                pad_token_id=_tokenizer.eos_token_id,
            )

        text = _tokenizer.decode(outputs[0][inputs.shape[-1]:], skip_special_tokens=True)
        
        # Enhanced completeness checking for research quality
        original_length = len(text)
        is_complete = _is_complete_sentence(text)
        
        if not is_complete:
            # Try to find last complete sentence
            last_period = max(text.rfind('.'), text.rfind('!'), text.rfind('?'))
            last_newline = text.rfind('\n')
            
            # Check if we have substantial content (at least 50% complete, like working version)
            if last_period > len(text) * 0.5:  # If we have at least 50% complete
                text = text[:last_period + 1]
            else:
                # Response is too incomplete - add ellipsis
                text = text.strip() + "..."
        
        # Aggressive cleanup after generation (like working version)
        if torch.cuda.is_available():
            del outputs, inputs
            torch.cuda.empty_cache()
            torch.cuda.synchronize()
            # Force garbage collection
            import gc
            gc.collect()
        
        # Release query priority
        if is_query:
            with _query_waiting:
                _active_query_count -= 1
                if _active_query_count == 0:
                    _query_waiting.notify_all()  # Notify waiting summaries
                print(f"🔵 Query completed. Remaining queries: {_active_query_count}")
            
        return text
        
    except torch.cuda.OutOfMemoryError as e:
        # Emergency memory cleanup
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            torch.cuda.synchronize()
        
        # Return a simple structured summary instead of trying LLM again (like working version)
        return "Summary temporarily unavailable due to system memory constraints. Please refresh the page and try again."
    
    except Exception as e:
        # Enhanced error logging for research quality
        error_type = type(e).__name__
        error_msg = str(e)
        full_error = f"LLM generation error: {error_type}: {error_msg}"
        print(f"❌ {full_error}")
        logger.error(full_error, exc_info=True)
        
        # Check if model is loaded
        if _model is None or _tokenizer is None:
            print("❌ CRITICAL: Model or tokenizer is None - model may not be loaded!")
            return ("I encountered an error: The AI model is not loaded. Please contact the system administrator.")
        
        # Return a structured error message with more details for debugging
        if "timeout" in error_msg.lower():
            return ("I encountered a timeout error while generating the response. "
                    "The query may be too complex. Please try again with a simpler question.")
        elif "memory" in error_msg.lower() or "OOM" in error_msg.upper():
            return ("I encountered a memory error while generating the response. "
                    "Please wait a moment and try again, or refresh the page.")
        else:
            return (f"I encountered an error while generating the response ({error_type}). "
                    "Please try again, or rephrase your question. "
                    "If the problem persists, please contact the system administrator.")

def clear_gpu_memory():
    """
    Aggressively clear GPU memory across all devices.
    This function should be called after each query and on patient switches
    to prevent OOM errors and ensure clean state.
    """
    if not torch.cuda.is_available():
        return
    
    try:
        # Clear cache on all GPU devices multiple times
        for _ in range(2):  # Clear twice for thoroughness
            for i in range(torch.cuda.device_count()):
                with torch.cuda.device(i):
                    torch.cuda.empty_cache()
                    torch.cuda.synchronize()
                    torch.cuda.ipc_collect()  # Clear inter-process cache
        
        # Force Python garbage collection multiple times
        for _ in range(2):
            gc.collect()
        
        # Log memory status for monitoring
        if torch.cuda.device_count() > 0:
            memory_allocated = torch.cuda.memory_allocated(0) / 1024**3  # GB
            memory_reserved = torch.cuda.memory_reserved(0) / 1024**3   # GB
            total_memory = torch.cuda.get_device_properties(0).total_memory / 1024**3  # GB
            usage_percent = (memory_reserved / total_memory) * 100 if total_memory > 0 else 0
            
            logger.debug(f"GPU memory after cleanup - Allocated: {memory_allocated:.2f} GB, Reserved: {memory_reserved:.2f} GB, Usage: {usage_percent:.1f}%")
            
            # Warn if memory usage is still high after cleanup
            if usage_percent > 80:
                logger.warning(f"⚠️  High GPU memory usage after cleanup: {usage_percent:.1f}% (Reserved: {memory_reserved:.2f} GB)")
    except Exception as e:
        logger.warning(f"Error during GPU memory cleanup: {e}")

def clear_gpu_memory_aggressive():
    """
    Ultra-aggressive GPU memory clearing for patient switches.
    This is more thorough than regular cleanup and should be used when switching patients.
    """
    if not torch.cuda.is_available():
        return
    
    try:
        # Clear cache on all GPU devices multiple times
        for _ in range(2):  # Clear twice for thoroughness
            for i in range(torch.cuda.device_count()):
                with torch.cuda.device(i):
                    torch.cuda.empty_cache()
                    torch.cuda.synchronize()
        
        # Force multiple garbage collection passes
        for _ in range(3):
            gc.collect()
        
        # Log memory status
        if torch.cuda.device_count() > 0:
            memory_allocated = torch.cuda.memory_allocated(0) / 1024**3  # GB
            memory_reserved = torch.cuda.memory_reserved(0) / 1024**3   # GB
            total_memory = torch.cuda.get_device_properties(0).total_memory / 1024**3  # GB
            memory_usage = (memory_allocated + memory_reserved) / total_memory if total_memory > 0 else 0
            
            logger.info(f"🔧 Aggressive GPU cleanup complete - Allocated: {memory_allocated:.2f} GB, Reserved: {memory_reserved:.2f} GB, Usage: {memory_usage:.1%}")
            
            # Warn if memory usage is still high
            if memory_usage > 0.85:
                logger.warning(f"⚠️  High GPU memory usage after cleanup: {memory_usage:.1%}")
    except Exception as e:
        logger.warning(f"Error during aggressive GPU memory cleanup: {e}")

def get_gpu_memory_status() -> Dict[str, Any]:
    """
    Get current GPU memory status across all devices.
    Returns a dictionary with memory information for monitoring.
    """
    if not torch.cuda.is_available():
        return {"available": False}
    
    status = {
        "available": True,
        "device_count": torch.cuda.device_count(),
        "devices": []
    }
    
    for i in range(torch.cuda.device_count()):
        props = torch.cuda.get_device_properties(i)
        allocated = torch.cuda.memory_allocated(i) / 1024**3  # GB
        reserved = torch.cuda.memory_reserved(i) / 1024**3   # GB
        total = props.total_memory / 1024**3  # GB
        free = total - reserved
        
        device_status = {
            "device_id": i,
            "name": props.name,
            "total_gb": round(total, 2),
            "allocated_gb": round(allocated, 2),
            "reserved_gb": round(reserved, 2),
            "free_gb": round(free, 2),
            "usage_percent": round((reserved / total) * 100, 1) if total > 0 else 0
        }
        status["devices"].append(device_status)
    
    return status

def model_name() -> str:
    return os.path.basename(MODEL_PATH.rstrip("/"))